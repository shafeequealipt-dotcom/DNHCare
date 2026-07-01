"""
check_post.py  —  deterministic safety + quality gate for DNH Care blog posts.

The daily blog agent MUST run this on any new post before opening a PR.
Exit 0 = pass. Exit 1 = FAIL (do not publish; fix and re-run).

Usage:  python agent/check_post.py blog/<new-post>.html
"""
import sys, re, os

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

    # must link to at least one service page (internal linking)
    if not re.search(r'\.\./(skin-treatment|allergy-treatment|pediatric-care|migraine-treatment|womens-health)(\.html)?', html):
        fails.append("no internal link to a service page")

    # word count of the article body (sanity: real content, not thin)
    body = re.search(r'<main class="article">([\s\S]*?)</main>', html)
    words = len(visible_text(body.group(1)).split()) if body else 0
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
