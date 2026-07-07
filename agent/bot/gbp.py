"""Google Business Profile local posts — post an approved blog to the clinic's
GBP listing with a "Learn more" link back to dnhcare.co.in.

Dormant unless ALL GBP_* vars are set in .env (see gbp_auth.py for the one-time
OAuth bootstrap). Uses the v4 localPosts endpoint, which remains the live surface
for local posts; auth is a standard OAuth2 refresh-token flow (GBP has no
service-account support). Stdlib urllib only — no new dependencies.
"""
import json
import re
import urllib.request
import urllib.parse
import urllib.error
from . import config

TOKEN_URL = "https://oauth2.googleapis.com/token"
API_BASE = "https://mybusiness.googleapis.com/v4"
SUMMARY_LIMIT = 1500  # GBP hard limit for LocalPost.summary


def is_configured() -> bool:
    """True only when every GBP credential/id is present — otherwise the whole
    feature is silently skipped and the bot behaves exactly as before."""
    return all([config.GBP_CLIENT_ID, config.GBP_CLIENT_SECRET,
                config.GBP_REFRESH_TOKEN, config.GBP_ACCOUNT_ID,
                config.GBP_LOCATION_ID])


def is_enabled() -> bool:
    """Configured AND not switched off via /gbp off."""
    return is_configured() and config.gbp_enabled()


def _access_token() -> str:
    """Exchange the long-lived refresh token for a short-lived access token."""
    body = urllib.parse.urlencode({
        "client_id": config.GBP_CLIENT_ID,
        "client_secret": config.GBP_CLIENT_SECRET,
        "refresh_token": config.GBP_REFRESH_TOKEN,
        "grant_type": "refresh_token",
    }).encode()
    req = urllib.request.Request(TOKEN_URL, data=body, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["access_token"]


def _api(method: str, path: str, payload: dict | None = None) -> dict:
    """Authenticated JSON call against the Business Profile v4 API."""
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        API_BASE + path, data=data, method=method,
        headers={"Authorization": f"Bearer {_access_token()}",
                 "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:400]
        raise RuntimeError(f"GBP API {e.code} on {method} {path}: {detail}") from e


def _clean_summary(text: str) -> str:
    """Plain-text the summary (GBP posts don't render HTML/markdown) and cap it."""
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = re.sub(r"[*_#`]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > SUMMARY_LIMIT:
        text = text[:SUMMARY_LIMIT - 1].rsplit(" ", 1)[0].rstrip(".,;:") + "…"
    return text


def create_local_post(summary: str, blog_url: str) -> str:
    """Create a STANDARD local post with a Learn-more CTA to the blog post.
    Returns the created post's resource name."""
    parent = f"/accounts/{config.GBP_ACCOUNT_ID}/locations/{config.GBP_LOCATION_ID}"
    payload = {
        "languageCode": "en",
        "topicType": "STANDARD",
        "summary": _clean_summary(summary),
        "callToAction": {"actionType": "LEARN_MORE", "url": blog_url},
    }
    out = _api("POST", parent + "/localPosts", payload)
    return out.get("name", "(created)")


def delete_local_post(name: str):
    """Delete a local post by its resource name (used by the live smoke test)."""
    _api("DELETE", "/" + name.lstrip("/"))
