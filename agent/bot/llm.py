"""Shared OpenRouter (OpenAI-compatible) client with a rate-limit retry — free
models are frequently rate-limited upstream, so retry a few times before giving up."""
import time
import json
import urllib.request
import openai
from openai import OpenAI
from . import config


def list_free_models() -> list:
    """Fetch the CURRENT free-model roster live from OpenRouter and return the model
    ids (those ending ':free') sorted alphabetically. Stdlib-only GET so it can't be
    tripped up by SDK quirks. Raises on network/HTTP error — caller falls back."""
    url = config.OPENROUTER_BASE_URL.rstrip("/") + "/models"
    req = urllib.request.Request(
        url, headers={"Authorization": f"Bearer {config.OPENROUTER_API_KEY}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r).get("data", [])
    return sorted(m["id"] for m in data if str(m.get("id", "")).endswith(":free"))

# max_retries=0 so the SDK does NOT add its own (long, Retry-After-honoring) backoff on
# top of ours — otherwise a throttled free model hangs for minutes. We handle 429 here.
_client = OpenAI(
    base_url=config.OPENROUTER_BASE_URL,
    api_key=config.OPENROUTER_API_KEY,
    max_retries=0,
    timeout=300,   # 5 min per call — slow large free models (nemotron etc.) need it
    default_headers={"HTTP-Referer": "https://dnhcare.co.in",
                     "X-Title": "DNH Care Blog Agent"},
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
