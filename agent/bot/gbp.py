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
# Business Information v1 — the live surface for listing fields (services,
# description, categories, website); v4 still serves posts and reviews.
BI_BASE = "https://mybusinessbusinessinformation.googleapis.com/v1"
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
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)["access_token"]
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:300]
        hint = ""
        if "invalid_grant" in detail:
            hint = (" — the refresh token is expired or revoked. If the OAuth "
                   "consent screen is still in \"Testing\" publishing status, "
                   "Google expires refresh tokens after 7 days: re-run "
                   "`python3 -m agent.bot.gbp_auth login` for a new one, or "
                   "publish the consent screen to Production to stop this "
                   "recurring.")
        raise RuntimeError(f"GBP token refresh {e.code}: {detail}{hint}") from e


def _api(method: str, path: str, payload: dict | None = None,
         base: str = API_BASE) -> dict:
    """Authenticated JSON call against the Business Profile API (v4 by default)."""
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        base + path, data=data, method=method,
        headers={"Authorization": f"Bearer {_access_token()}",
                 "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:400]
        raise RuntimeError(f"GBP API {e.code} on {method} {path}: {detail}") from e


def _clean_summary(text: str, limit: int = SUMMARY_LIMIT) -> str:
    """Plain-text the summary (GBP posts don't render HTML/markdown) and cap it.
    Markdown-strip runs on LLM prose only — call this BEFORE appending any URL
    (a URL's underscores, e.g. utm_source, would otherwise be stripped too)."""
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = re.sub(r"[*_#`]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > limit:
        text = text[:limit - 1].rsplit(" ", 1)[0].rstrip(".,;:") + "…"
    return text


def create_local_post(summary: str, blog_url: str) -> str:
    """Create a STANDARD local post. CTA comes from config.gbp_cta():
      CALL       -> "Call now" button using the clinic's listed phone number
                    (per the v4 API, `url` must be left unset for Call CTAs);
                    the blog URL is kept as plain text at the end of the summary
                    so the post still references the site.
      LEARN_MORE -> clickable "Learn more" link to the blog post.
    Returns the created post's resource name."""
    parent = f"/accounts/{config.GBP_ACCOUNT_ID}/locations/{config.GBP_LOCATION_ID}"
    # Tag the outbound link so GA4/Search Console can attribute GBP-driven visits.
    sep = "&" if "?" in blog_url else "?"
    tagged_url = f"{blog_url}{sep}utm_source=gbp&utm_medium=post"
    cta = config.gbp_cta()
    if cta == "CALL":
        # Clean the LLM prose FIRST (markdown-strip touches underscores, which
        # would corrupt utm_source/utm_medium), reserve room for the URL suffix,
        # then append the URL raw so it's never touched or truncated.
        suffix = f" Read the full guide: {tagged_url}"
        clean = _clean_summary(summary, limit=SUMMARY_LIMIT - len(suffix))
        final_summary = clean + suffix
        call_to_action = {"actionType": "CALL"}
    else:
        final_summary = _clean_summary(summary)
        call_to_action = {"actionType": "LEARN_MORE", "url": tagged_url}
    payload = {
        "languageCode": "en",
        "topicType": "STANDARD",
        "summary": final_summary,
        "callToAction": call_to_action,
    }
    if config.GBP_POST_IMAGE_URL:
        payload["media"] = [{"mediaFormat": "PHOTO",
                             "sourceUrl": config.GBP_POST_IMAGE_URL}]
    out = _api("POST", parent + "/localPosts", payload)
    return out.get("name", "(created)")


def delete_local_post(name: str):
    """Delete a local post by its resource name (used by the live smoke test)."""
    _api("DELETE", "/" + name.lstrip("/"))


# ---- listing fields (Business Information v1) ----

def get_location(read_mask: str) -> dict:
    """Read listing fields, e.g. get_location("serviceItems,profile")."""
    path = f"/locations/{config.GBP_LOCATION_ID}?readMask={read_mask}"
    return _api("GET", path, base=BI_BASE)


def patch_location(update_mask: str, body: dict, validate_only: bool = False) -> dict:
    """Write listing fields. validate_only asks Google to check the edit without
    applying it. Edits to the live listing may sit in Google review for a while."""
    path = f"/locations/{config.GBP_LOCATION_ID}?updateMask={update_mask}"
    if validate_only:
        path += "&validateOnly=true"
    return _api("PATCH", path, body, base=BI_BASE)


def service_names() -> list:
    """Display names of the listing's free-form services, in listing order."""
    items = get_location("serviceItems").get("serviceItems", [])
    return [s["freeFormServiceItem"]["label"]["displayName"]
            for s in items if "freeFormServiceItem" in s]


def add_service_item(name: str, description: str,
                     category_id: str = "gcid:homeopath") -> bool:
    """Append one free-form service. The API only replaces the whole list, so the
    current items are read and resent with the new one. Returns False if a
    service with that name already exists."""
    items = get_location("serviceItems").get("serviceItems", [])
    have = {s["freeFormServiceItem"]["label"]["displayName"].lower()
            for s in items if "freeFormServiceItem" in s}
    if name.lower() in have:
        return False
    items.append({"freeFormServiceItem": {
        "category": f"categories/{category_id}",
        "label": {"displayName": name, "description": description[:300],
                  "languageCode": "en"}}})
    patch_location("serviceItems", {"serviceItems": items})
    return True
