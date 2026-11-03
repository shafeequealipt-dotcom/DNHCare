"""GBP weekly intelligence: performance metrics, search keywords locals actually
used, a review snapshot, and our own post performance — reduced to a Telegram
digest, plus an LLM topic-suggestion step that closes the loop back into
agent/topics.md. Read-only against Google (no writes); one small Cloudflare call
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


def _keywords_for_month(year: int, month: int, n: int = 60) -> dict:
    """{keyword: impressions} for one calendar month. Phrases below Google's
    privacy threshold come back as the threshold (e.g. 15)."""
    loc = f"locations/{config.GBP_LOCATION_ID}"
    data = _perf_get(f"{loc}/searchkeywords/impressions/monthly",
                     {"monthlyRange.start_month.year": year,
                      "monthlyRange.start_month.month": month,
                      "monthlyRange.end_month.year": year,
                      "monthlyRange.end_month.month": month,
                      "pageSize": 100})
    out = {}
    for row in data.get("searchKeywordsCounts", []):
        vals = row.get("insightsValue", {})
        try:
            out[row.get("searchKeyword", "")] = int(vals.get("value") or vals.get("threshold", 0))
        except (TypeError, ValueError):
            continue
    return dict(sorted(out.items(), key=lambda x: -x[1])[:n])


# Words that say nothing about WHAT someone needs — ignored when checking whether
# a search phrase is covered by a service or the description.
_GENERIC = {"homeopathy", "homeopathic", "homoeopathic", "homeopath", "clinic", "doctor",
            "near", "best", "bangalore", "bengaluru", "hospital", "medical", "centre",
            "center", "treatment", "specialist", "medicine", "varthur", "whitefield",
            "gunjur", "road", "main", "school", "karnataka", "nafia", "top", "good",
            "homeo", "oppst"}
# Search words patients use for something a service already covers.
_SYNONYMS = {"dermatologist": "skin", "derma": "skin", "pediatrician": "child",
             "paediatrician": "child", "gynaecologist": "women", "gynecologist": "women",
             "piles": "pile", "hemorrhoid": "pile", "haemorrhoid": "pile"}


def _need_words(phrase: str) -> set:
    return {_SYNONYMS.get(w, w) for w in topics._words(phrase)} - _GENERIC


def keyword_report() -> tuple:
    """Monthly keyword-to-listing check. Compares last month's search phrases with
    the month before (rising terms), finds condition phrases no service or the
    description covers (gaps), and asks the model for up to 3 new services to
    close them. Returns (html_text, suggestions); suggestions are
    [{"name", "description"}] for /gbp apply <n> — nothing is written here."""
    def prev_month(d):
        return d.replace(day=1) - datetime.timedelta(days=1)

    m1 = prev_month(datetime.date.today())                   # last full month
    now = _keywords_for_month(m1.year, m1.month)
    if not now:
        # Google publishes a month's keywords some days after it ends — fall
        # back to the latest month that has data.
        m1 = prev_month(m1)
        now = _keywords_for_month(m1.year, m1.month)
    m2 = prev_month(m1)
    before = _keywords_for_month(m2.year, m2.month)
    services = gbp.service_names()
    desc = gbp.get_location("profile").get("profile", {}).get("description", "")
    covered = topics._words(" ".join(services) + " " + desc) - _GENERIC

    # People searching the clinic's own name or address aren't a content signal.
    now = {k: c for k, c in now.items() if "nafia" not in k.lower()}
    rising = [(k, c) for k, c in now.items() if c > before.get(k, 0)][:8]
    gaps = []
    for k, c in now.items():
        need = _need_words(k)
        if need and not need & covered:
            gaps.append((k, c))

    lines = [f"🔎 <b>Keyword check — {m1.strftime('%B %Y')}</b>", ""]
    lines.append("📈 Rising: " + (", ".join(f"{k} ({before.get(k, 0)}→{c})"
                                          for k, c in rising) or "—"))
    lines.append("🕳 Not covered by any service or the description: "
                 + (", ".join(f"{k} ({c})" for k, c in gaps[:10]) or "none 👍"))

    suggestions = []
    if gaps:
        try:
            suggestions = _suggest_services(gaps[:10], services)
        except Exception:  # noqa
            suggestions = []
    if suggestions:
        lines.append("")
        lines.append("💡 <b>Suggested new services</b> — /gbp apply &lt;n&gt; to add one:")
        for i, s in enumerate(suggestions, 1):
            lines.append(f"  {i}. <b>{s['name']}</b> — {s['description']}")
    return "\n".join(lines), suggestions


def _suggest_services(gaps: list, services: list) -> list:
    """Ask the model for up to 3 service entries that honestly cover the gap
    phrases. Returns [{"name", "description"}]."""
    resp = llm.chat(messages=[{
        "role": "user",
        "content": (
            "A homeopathy clinic in Varthur, Bengaluru lists these services on its "
            f"Google Business Profile: {', '.join(services)}.\n"
            "People found the clinic with these search phrases, which no service "
            "covers yet (phrase — impressions):\n"
            + "\n".join(f"- {k} ({c})" for k, c in gaps)
            + "\n\nPropose up to 3 NEW services, only for phrases about a health "
            "condition or symptom a homeopath treats (skip directions, places, "
            "pharmacies, other medical specialities and anything not a health "
            "need). Name = the condition in plain words, max 40 characters, no place "
            "names, no 'best/top/near me', no specialist titles. Description = one "
            "or two sentences, max 250 characters, starting 'Homeopathic care for', "
            "no cure or result claims.\n"
            "Reply with one line per service and nothing else, in this format:\n"
            "Name | Description\n"
            "If none qualify, reply NONE."
        ),
    }], temperature=0.3, max_tokens=400)
    text = (resp.choices[0].message.content or "").strip()
    have = [topics._words(s) for s in services]
    out = []
    for line in text.splitlines():
        name, sep, d = line.strip().lstrip("-0123456789. ").partition("|")
        name, d = name.strip(), d.strip()
        words = topics._words(name)
        # Skip near-duplicates, e.g. "Excess Sweating" vs "Excess Sweating (Hyperhidrosis)".
        if any(words <= h or h <= words for h in have if h):
            continue
        if sep and name and d and len(name) <= 40:
            out.append({"name": name, "description": d[:300]})
    return out[:3]


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
