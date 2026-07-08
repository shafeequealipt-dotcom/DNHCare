"""GBP weekly intelligence: performance metrics, search keywords locals actually
used, a review snapshot, and our own post performance — reduced to a Telegram
digest, plus an LLM topic-suggestion step that closes the loop back into
agent/topics.md. Read-only against Google (no writes); one small OpenRouter call
for suggest_topics(). Dormant unless gbp.is_configured().
"""
import datetime
import json
import urllib.parse
import urllib.request
import urllib.error
from . import config, gbp, llm, topics

PERF_BASE = "https://businessprofileperformance.googleapis.com/v1"
DAILY_METRICS = [
    "CALL_CLICKS", "WEBSITE_CLICKS", "BUSINESS_DIRECTION_REQUESTS",
    "BUSINESS_IMPRESSIONS_DESKTOP_SEARCH", "BUSINESS_IMPRESSIONS_MOBILE_SEARCH",
    "BUSINESS_IMPRESSIONS_DESKTOP_MAPS", "BUSINESS_IMPRESSIONS_MOBILE_MAPS",
]
_LABELS = {"CALL_CLICKS": "Calls", "WEBSITE_CLICKS": "Site clicks",
          "BUSINESS_DIRECTION_REQUESTS": "Directions"}


def _perf_get(path: str, params: dict) -> dict:
    """Authenticated GET against the Performance API. Raises RuntimeError with a
    short, actionable message on HTTP error (e.g. API not yet enabled)."""
    url = f"{PERF_BASE}/{path}?{urllib.parse.urlencode(params, doseq=True)}"
    req = urllib.request.Request(
        url, headers={"Authorization": f"Bearer {gbp._access_token()}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:300]
        raise RuntimeError(f"Performance API {e.code}: {detail}") from e


def _date_range(days_ago_start: int, days_ago_end: int):
    today = datetime.date.today()
    start = today - datetime.timedelta(days=days_ago_start)
    end = today - datetime.timedelta(days=days_ago_end)
    def d(dt):
        return {"year": dt.year, "month": dt.month, "day": dt.day}
    return d(start), d(end)


def weekly_metrics() -> dict:
    """Sum each daily metric over the last 7 full days vs the prior 7, for %
    change. Returns {metric: {"this": int, "prev": int, "pct": float|None}}."""
    loc = f"locations/{config.GBP_LOCATION_ID}"
    this_s, this_e = _date_range(7, 1)
    prev_s, prev_e = _date_range(14, 8)
    out = {}
    for metric in DAILY_METRICS:
        params = {
            "dailyMetric": metric,
            "dailyRange.start_date.year": prev_s["year"],
            "dailyRange.start_date.month": prev_s["month"],
            "dailyRange.start_date.day": prev_s["day"],
            "dailyRange.end_date.year": this_e["year"],
            "dailyRange.end_date.month": this_e["month"],
            "dailyRange.end_date.day": this_e["day"],
        }
        try:
            data = _perf_get(f"{loc}:getDailyMetricsTimeSeries", params)
        except RuntimeError:
            out[metric] = {"this": 0, "prev": 0, "pct": None, "error": True}
            continue
        series = data.get("timeSeries", {}).get("datedValues", [])
        this_total = prev_total = 0
        for pt in series:
            dt = pt.get("date", {})
            val = int(pt.get("value", 0))
            day = datetime.date(dt.get("year", 1), dt.get("month", 1), dt.get("day", 1))
            if day >= today_minus(7):
                this_total += val
            else:
                prev_total += val
        pct = round((this_total - prev_total) / prev_total * 100) if prev_total else None
        out[metric] = {"this": this_total, "prev": prev_total, "pct": pct}
    return out


def today_minus(n: int) -> datetime.date:
    return datetime.date.today() - datetime.timedelta(days=n)


def top_search_keywords(n: int = 10) -> list:
    """Latest available month of search-keyword impressions. Returns
    [(keyword, impressions), ...] sorted descending, or [] on error/no data."""
    loc = f"locations/{config.GBP_LOCATION_ID}"
    try:
        data = _perf_get(
            f"{loc}/searchkeywords/impressions/monthly",
            {"monthlyRange.start_month.year": today_minus(60).year,
             "monthlyRange.start_month.month": today_minus(60).month,
             "monthlyRange.end_month.year": datetime.date.today().year,
             "monthlyRange.end_month.month": datetime.date.today().month})
    except RuntimeError:
        return []
    rows = data.get("searchKeywordsCounts", [])
    parsed = []
    for row in rows:
        kw = row.get("searchKeyword", "")
        vals = row.get("insightsValue", {})
        impressions = vals.get("value") or vals.get("threshold", 0)
        try:
            parsed.append((kw, int(impressions)))
        except (TypeError, ValueError):
            continue
    parsed.sort(key=lambda x: x[1], reverse=True)
    return parsed[:n]


def review_snapshot() -> dict:
    """Read-only review mining via the v4 API (list only — never replies).
    Returns total count, average rating, and how many arrived in the last 7 days."""
    parent = f"/accounts/{config.GBP_ACCOUNT_ID}/locations/{config.GBP_LOCATION_ID}"
    try:
        data = gbp._api("GET", parent + "/reviews?pageSize=50")
    except RuntimeError:
        return {"error": True}
    reviews = data.get("reviews", [])
    total = data.get("totalReviewCount", len(reviews))
    avg = data.get("averageRating", 0)
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=7)
    recent = 0
    for r in reviews:
        ts = r.get("createTime", "")
        try:
            created = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if created >= cutoff:
                recent += 1
        except ValueError:
            continue
    return {"total": total, "avg": avg, "recent": recent}


def post_insights(slugs_and_names: list) -> dict | None:
    """Per-post view counts. NOT AVAILABLE: Google removed
    accounts.locations.localPosts.reportInsights (confirmed live — returns 404 as
    of 2026-07) and its Performance-API replacement only covers location-level
    metrics, not individual post views. config.record_gbp_post still tracks each
    post's title+resource name (harmless, and ready if Google reinstates a
    per-post metric), but there is currently no API call that can answer this.
    Always returns None; kept as a function so build_digest doesn't need to
    change if/when Google restores this capability."""
    return None


def suggest_topics(keywords: list, review_avg: float, n: int = 3) -> list:
    """Cross-reference top search keywords against already-published topics
    (topics.list_done_titles — same source the daily auto-picker avoids
    duplicating) and ask the model for fresh, keyword-matched blog ideas."""
    if not keywords:
        return []
    kw_text = ", ".join(f"{k} ({c})" for k, c in keywords[:10])
    done = topics.list_done_titles()
    avoid = "\n".join(f"- {t}" for t in done) if done else "(none yet)"
    cats = " / ".join(config.CATEGORIES)
    resp = llm.chat(messages=[{
        "role": "user",
        "content": (
            "You plan content for a homeopathy clinic in Varthur, Bengaluru "
            f"(Dr. Nafia's Homoeopathic Medical Centre). Categories: {cats}.\n"
            f"These are the ACTUAL search phrases locals used on Google to find "
            f"the clinic this month (keyword — impressions):\n{kw_text}\n\n"
            f"Already-published topics — do NOT repeat these or anything close:\n{avoid}\n\n"
            f"Propose exactly {n} NEW blog topics that closely match what locals "
            "are actually searching for. Each MUST map to one of the categories "
            "and stay within safe, non-overclaiming homeopathy content.\n"
            f"Reply with EXACTLY {n} lines, nothing else, each in this format:\n"
            "[Category] Title of the post"
        ),
    }], temperature=0.7, max_tokens=300)
    text = (resp.choices[0].message.content or "").strip()
    import re
    lines = [l.strip() for l in text.splitlines()
            if re.match(r"^\[[A-Za-z]+\]\s+.+", l.strip())]
    return lines[:n]


def build_digest() -> tuple:
    """Assemble the weekly Telegram digest. Returns (html_text, suggested_topics).
    Every section degrades gracefully — a failed API call shows '—' rather than
    raising, so one broken surface never blocks the whole report."""
    metrics = weekly_metrics()
    keywords = top_search_keywords()
    reviews = review_snapshot()
    recent = [(p["title"], p["name"]) for p in config.get_gbp_posts(5)]
    best = post_insights(recent) if recent else None

    def fmt_metric(key):
        m = metrics.get(key, {})
        if m.get("error"):
            return "—"
        pct = m.get("pct")
        arrow = f" ({'▲' if pct >= 0 else '▼'} {abs(pct)}%)" if pct is not None else ""
        return f"{m.get('this', 0)}{arrow}"

    impressions = sum(metrics.get(k, {}).get("this", 0) for k in DAILY_METRICS
                      if "IMPRESSIONS" in k)

    lines = ["📊 <b>GBP Weekly — Dr. Nafia's Clinic</b>", ""]
    lines.append(f"📞 Calls: {fmt_metric('CALL_CLICKS')}   "
                 f"🌐 Site clicks: {fmt_metric('WEBSITE_CLICKS')}")
    lines.append(f"🧭 Directions: {fmt_metric('BUSINESS_DIRECTION_REQUESTS')}   "
                 f"👀 Impressions: {impressions}")

    if keywords:
        kw_line = ", ".join(f"{k} ({c})" for k, c in keywords[:6])
        lines.append(f"🔍 Top searches: {kw_line}")
    else:
        lines.append("🔍 Top searches: — (no data yet, or API not enabled)")

    if reviews.get("error"):
        lines.append("⭐ Reviews: —")
    else:
        lines.append(f"⭐ Reviews: {reviews['total']} total · {reviews['avg']:.1f} avg"
                     f" · +{reviews['recent']} this week")

    if best:
        lines.append(f"📝 Best post: \"{best['title']}\" — {best['views']} views")

    suggestions = []
    if keywords:
        try:
            suggestions = suggest_topics(keywords, reviews.get("avg", 0))
        except Exception:  # noqa
            suggestions = []
    if suggestions:
        lines.append("")
        lines.append("💡 <b>Suggested topics</b> (tap to add to the queue):")
        for i, s in enumerate(suggestions, 1):
            lines.append(f"  {i}. {s}")

    return "\n".join(lines), suggestions
