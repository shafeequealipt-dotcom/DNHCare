"""Shared OpenRouter (OpenAI-compatible) client with a rate-limit retry — free
models are frequently rate-limited upstream, so retry a few times before giving up."""
import time
import openai
from openai import OpenAI
from . import config

_client = OpenAI(
    base_url=config.OPENROUTER_BASE_URL,
    api_key=config.OPENROUTER_API_KEY,
    default_headers={"HTTP-Referer": "https://dnhcare.co.in",
                     "X-Title": "DNH Care Blog Agent"},
)


def chat(messages, model=None, retries=4, **kw):
    """Chat completion against the current (or given) model, retrying on 429."""
    model = model or config.get_model()
    last = None
    for _ in range(retries):
        try:
            return _client.chat.completions.create(model=model, messages=messages, **kw)
        except openai.RateLimitError as e:
            last = e
            wait = 5
            try:
                wait = int(e.response.headers.get("retry-after", "5"))
            except Exception:  # noqa
                pass
            time.sleep(min(wait, 30))
    raise last
