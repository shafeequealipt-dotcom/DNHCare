"""
check_post.py  —  deterministic safety + quality gate for DNH Care blog posts.

The daily blog agent MUST run this on any new post before opening a PR.
Exit 0 = pass. Exit 1 = FAIL (do not publish; fix and re-run).

Usage:  python agent/check_post.py blog/<new-post>.html
"""
import sys, re, os

try:                      # imported as agent.check_post (by the bot)
    from . import locations
except ImportError:       # run as a script: python agent/check_post.py <file>
    import locations

# Medical-overclaim words banned on a YMYL health site (case-insensitive, word-ish match).
BANNED = [
    "cure", "cures", "cured", "guaranteed", "guarantee",
    "no side effects", "100% safe", "completely safe", "miracle",
    "permanent cure", "instant relief", "risk-free", "proven to cure",
]

# Specific homeopathic remedy/medicine names must never appear in patient-facing posts.
# Naming remedies looks like prescribing — a YMYL/regulatory risk and not the clinic's style.
BANNED_REMEDY_NAMES = [
    "belladonna", "hepar sulphur", "hepar sulph", "phytolacca", "kali bichromicum",
    "kali bich", "arsenicum", "pulsatilla", "nux vomica", "bryonia", "rhus tox",
    "sulphur", "calcarea", "lycopodium", "natrum mur", "sepia", "ignatia",
    "apis mellifica", "apis mel", "silicea", "phosphorus", "thuja", "lachesis",
    "mercurius", "gelsemium", "aconite", "aconitum", "graphites", "conium",
    "hypericum", "arnica", "ledum", "ruta", "staphysagria", "china officinalis",
]

REQUIRED_SUBSTRINGS = {
    "medical disclaimer block": 'class="med-disclaimer"',
    "author E-E-A-T box": 'class="author-box"',
    "BlogPosting schema": '"@type": "BlogPosting"',
    "BreadcrumbList schema": '"@type": "BreadcrumbList"',
    "canonical tag": 'rel="canonical"',
    "scroll progress bar": 'class="scroll-progress"',
    "footer NAP": "Gunjur Main Road",
    "book CTA": "wa.me/919663779358",
}

def visible_text(html: str) -> str:
    # strip scripts/styles then tags, lowercase — for overclaim scan on prose only
    html = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
    html = re.sub(r"<style[\s\S]*?</style>", " ", html, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", text).lower()

def main(path):
    if not os.path.isfile(path):
        print(f"FAIL: file not found: {path}"); return 1
    html = open(path, encoding="utf-8").read()
    text = visible_text(html)
    fails = []

    for word in BANNED:
        if re.search(r"\b" + re.escape(word) + r"\b", text):
            fails.append(f"banned overclaim word present: '{word}'")

    for remedy in BANNED_REMEDY_NAMES:
        if re.search(r"\b" + re.escape(remedy) + r"\b", text):
            fails.append(f"specific remedy name must not appear in patient-facing content: '{remedy}'")

    for label, needle in REQUIRED_SUBSTRINGS.items():
        if needle not in html:
            fails.append(f"missing required element: {label} ({needle})")

    # local SEO: every post must name Varthur and enough of the ~10 km service area
    # (agent/locations.py) IN THE ARTICLE ITSELF. Checked against the <main> body only —
    # the shared nav/footer already says "Varthur" and lists 4 areas on every page, which
    # would make this check meaningless. The template always renders all areas, so a
    # healthy post passes trivially; this catches a template regression or hand edit.
    _main = re.search(r'<main class="article">([\s\S]*?)</main>', html)
    article_text = visible_text(_main.group(1)) if _main else text
    if not re.search(r"\b" + re.escape(locations.PRIMARY.lower()) + r"\b", article_text):
        fails.append(f"local SEO: '{locations.PRIMARY}' is not mentioned in the article body")
    found = [a for a in locations.NEARBY_AREAS
             if re.search(r"\b" + re.escape(a.lower()) + r"\b", article_text)]
    if len(found) < locations.MIN_AREAS_IN_POST:
        fails.append(f"local SEO: only {len(found)} nearby area(s) mentioned "
                     f"(need >= {locations.MIN_AREAS_IN_POST} of the ~{locations.RADIUS_KM} km "
                     f"service area: {', '.join(locations.NEARBY_AREAS)})")

    # must link to at least one service page (internal linking)
    if not re.search(r'\.\./(skin-treatment|allergy-treatment|pediatric-care|migraine-treatment|womens-health)(\.html)?', html):
        fails.append("no internal link to a service page")

    # word count of the article body (sanity: real content, not thin)
    body = re.search(r'<main class="article">([\s\S]*?)</main>', html)
    # the auto-added areas-served block is boilerplate, not content — don't let it
    # help a thin article clear the floor
    body_html = re.sub(r'<div class="areas-served">[\s\S]*?</div>', " ",
                       body.group(1), flags=re.I) if body else ""
    words = len(visible_text(body_html).split()) if body else 0
    # hard floor blocks spam-thin content; PLAYBOOK target is 600-900 words.
    if words < 380:
        fails.append(f"article too thin: {words} words (need >= 380; aim 600-900)")

    # title + meta description present and non-trivial
    if not re.search(r"<title>.{15,}</title>", html):
        fails.append("missing or too-short <title>")
    if not re.search(r'name="description" content=".{60,}"', html):
        fails.append("missing or too-short meta description")

    if fails:
        print(f"FAIL ({len(fails)}) — {path}")
        for f in fails:
            print("  - " + f)
        return 1
    print(f"PASS ({words} words) — {path}")
    return 0

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python agent/check_post.py blog/<post>.html"); sys.exit(2)
    sys.exit(main(sys.argv[1]))
