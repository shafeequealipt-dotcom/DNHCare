"""Shared Groq (OpenAI-compatible) client with a rate-limit retry — models can be
rate-limited upstream on the free tier, so retry a few times before giving up."""
import time
import json
import urllib.request
import openai
from openai import OpenAI
from . import config

# Groq also serves non-chat models (speech-to-text, TTS, moderation classifiers)
# under the same /models endpoint. These can't take a chat-completions blog-writing
# prompt, so list_models() excludes them by id substring.
_NON_CHAT_MARKERS = ("whisper", "orpheus", "prompt-guard")


def list_models() -> list:
    """Fetch the CURRENT chat-capable model roster live from Groq, sorted
    alphabetically. Stdlib-only GET so it can't be tripped up by SDK quirks.
    Raises on network/HTTP error — caller falls back to config.PRESET_MODELS."""
    url = config.GROQ_BASE_URL.rstrip("/") + "/models"
    # Groq's edge (Cloudflare) 403s the default "Python-urllib/x.y" User-Agent —
    # any normal-looking UA passes.
    req = urllib.request.Request(
        url, headers={"Authorization": f"Bearer {config.GROQ_API_KEY}",
                     "User-Agent": "dnhcare-bot/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r).get("data", [])
    ids = (str(m.get("id", "")) for m in data)
    return sorted(i for i in ids if i and not any(x in i for x in _NON_CHAT_MARKERS))

# max_retries=0 so the SDK does NOT add its own (long, Retry-After-honoring) backoff on
# top of ours — otherwise a throttled model hangs for minutes. We handle 429 here.
_client = OpenAI(
    base_url=config.GROQ_BASE_URL,
    api_key=config.GROQ_API_KEY,
    max_retries=0,
    timeout=300,   # 5 min per call — large models can be slow under load
)


def chat(messages, model=None, retries=2, wait_cap=12, **kw):
    """Chat completion against the current (or given) model. On 429 we retry a couple
    of times with a short, capped wait, then fail fast so the user can switch models."""
    model = model or config.get_model()
    last = None
    for attempt in range(retries + 1):
        try:
            return _client.chat.completions.create(model=model, messages=messages, **kw)
        except openai.RateLimitError as e:
            last = e
            if attempt == retries:
                break
            wait = 4
            try:
                wait = int(e.response.headers.get("retry-after", "4"))
            except Exception:  # noqa
                pass
            time.sleep(min(wait, wait_cap))
    raise last
