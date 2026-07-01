"""Publish flow: stage a draft, run the safety gate, and on approval wire it into
the blog index + sitemap and commit/push to main (which auto-deploys via Pages)."""
import os
import re
import sys
import subprocess
import datetime
from . import config, topics


def _git(*args, check=True):
    return subprocess.run(["git", "-C", config.REPO_DIR, *args],
                          capture_output=True, text=True, check=check)


def sync_main():
    """Reset the local clone to a clean origin/<publish-branch> before generating."""
    br = config.PUBLISH_BRANCH
    _git("fetch", "origin")
    _git("checkout", br)
    _git("reset", "--hard", f"origin/{br}")
    _git("clean", "-fd", "blog")


def recent_posts(n=2):
    """Parse existing post cards from blog/index.html for the 'Keep reading' block."""
    idx = os.path.join(config.BLOG_DIR, "index.html")
    html = open(idx, encoding="utf-8").read()
    out = []
    for m in re.finditer(
        r'<a class="post-card" href="([^"]+)\.html">\s*'
        r'<span class="post-cat">([^<]+)</span>\s*<h2>([^<]+)</h2>', html):
        out.append({"slug": m.group(1), "category": m.group(2).strip(),
                    "title": m.group(3).strip()})
        if len(out) >= n:
            break
    return out


def stage_draft(slug, html_str):
    """Write the post file (uncommitted) so the gate can read it. Returns path."""
    os.makedirs(config.BLOG_DIR, exist_ok=True)
    path = os.path.join(config.BLOG_DIR, f"{slug}.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html_str)
    return path


def run_gate(path):
    """Run agent/check_post.py. Returns (ok: bool, output: str)."""
    rel = os.path.relpath(path, config.REPO_DIR)
    # Use the same interpreter running the bot (the venv python) — "python" may not
    # exist on the VM (Ubuntu only ships python3).
    p = subprocess.run([sys.executable, config.CHECK_SCRIPT, rel],
                       cwd=config.REPO_DIR, capture_output=True, text=True)
    return p.returncode == 0, (p.stdout + p.stderr).strip()


def discard(slug):
    path = os.path.join(config.BLOG_DIR, f"{slug}.html")
    if os.path.exists(path):
        os.remove(path)


def slug_is_published(slug: str) -> bool:
    """True if a post with this slug is ALREADY committed to git (i.e. a real,
    live duplicate). Checks git-tracked files — not the working tree — so an
    in-flight draft or a gate-retry re-write of the same slug is NOT flagged."""
    rel = os.path.relpath(os.path.join(config.BLOG_DIR, f"{slug}.html"),
                          config.REPO_DIR)
    p = subprocess.run(["git", "ls-files", "--error-unmatch", rel],
                       cwd=config.REPO_DIR, capture_output=True, text=True)
    return p.returncode == 0


def _insert_schema_entry(post):
    """Prepend new post into Blog.blogPost + ItemList in blog/index.html, keeping
    positions sequential and numberOfItems accurate."""
    import json as _json
    idx = os.path.join(config.BLOG_DIR, "index.html")
    html = open(idx, encoding="utf-8").read()
    slug = post.slug
    title_json = _json.dumps(post.title)
    url = f"https://dnhcare.co.in/blog/{slug}"

    # 1. Prepend into Blog.blogPost array (newest first)
    bp_entry = (f'\n      {{"@type": "BlogPosting", "@id": "{url}#post", '
                f'"headline": {title_json}, "url": "{url}"}},')
    html = html.replace('"blogPost": [', '"blogPost": [' + bp_entry, 1)

    # 2. Update ItemList: increment numberOfItems, shift existing positions, prepend ListItem
    html = re.sub(r'"numberOfItems":\s*(\d+)',
                  lambda m: f'"numberOfItems": {int(m.group(1)) + 1}', html, count=1)
    # Shift existing positions upward before inserting position 1
    def _bump(m):
        return f'"position": {int(m.group(1)) + 1}'
    # Only bump positions inside the ItemList block (after the ItemList marker)
    il_start = html.find('"itemListElement": [')
    if il_start != -1:
        before = html[:il_start]
        after = html[il_start:]
        after = re.sub(r'"position":\s*(\d+)', _bump, after)
        html = before + after
    li_entry = (f'\n      {{"@type": "ListItem", "position": 1, '
                f'"url": "{url}", "name": {title_json}}},')
    html = html.replace('"itemListElement": [', '"itemListElement": [' + li_entry, 1)

    with open(idx, "w", encoding="utf-8") as f:
        f.write(html)


def _insert_index_card(post):
    idx = os.path.join(config.BLOG_DIR, "index.html")
    html = open(idx, encoding="utf-8").read()
    nice_date = datetime.date.today().strftime("%d %b %Y")
    card = (f'    <a class="post-card" href="{post.slug}">\n'
            f'      <span class="post-cat">{post.category}</span>\n'
            f'      <h2>{post.title}</h2>\n'
            f'      <p>{post.meta_description}</p>\n'
            f'      <span class="post-foot">{nice_date} &middot; {post.read_minutes} min read</span>\n'
            f'    </a>\n')
    marker = '<main class="post-grid" id="posts">\n'
    html = html.replace(marker, marker + card, 1)
    with open(idx, "w", encoding="utf-8") as f:
        f.write(html)


def _insert_sitemap(slug):
    sm = open(config.SITEMAP_FILE, encoding="utf-8").read()
    loc = (f"  <url><loc>https://dnhcare.co.in/blog/{slug}</loc>"
           f"<priority>0.6</priority></url>\n")
    if slug not in sm:
        sm = sm.replace("</urlset>", loc + "</urlset>", 1)
        with open(config.SITEMAP_FILE, "w", encoding="utf-8") as f:
            f.write(sm)


def read_prompt():
    """Return the current content prompt text (from the synced repo file)."""
    try:
        return open(config.PROMPT_FILE, encoding="utf-8").read()
    except OSError:
        return ""


def update_prompt(text):
    """Re-sync, overwrite the content prompt file, commit & push the publish branch."""
    sync_main()
    with open(config.PROMPT_FILE, "w", encoding="utf-8") as f:
        f.write(text.strip() + "\n")
    _git("add", config.PROMPT_FILE)
    _git("-c", "user.name=DNH Care Bot", "-c", "user.email=bot@dnhcare.co.in",
         "commit", "-m", "agent: update content prompt")
    remote = (f"https://x-access-token:{config.GITHUB_TOKEN}@github.com/"
              f"{config.GITHUB_REPO}.git")
    push = _git("push", remote, config.PUBLISH_BRANCH, check=False)
    if push.returncode != 0:
        raise RuntimeError("git push failed:\n" + push.stderr)


def publish(post, html_str, topic):
    """Re-sync main, re-write the held draft, wire it into index + sitemap, mark the
    topic done, then commit & push main (fast-forward guaranteed). Returns live URL."""
    sync_main()                       # ensure fast-forward + clean base
    stage_draft(post.slug, html_str)  # re-write the post (sync may have cleaned it)
    _insert_index_card(post)
    _insert_schema_entry(post)
    _insert_sitemap(post.slug)
    topics.mark_done(topic, post.slug)

    _git("add", "-A")
    _git("-c", "user.name=DNH Care Bot",
         "-c", "user.email=bot@dnhcare.co.in",
         "commit", "-m", f"blog: {post.title}")
    remote = (f"https://x-access-token:{config.GITHUB_TOKEN}@github.com/"
              f"{config.GITHUB_REPO}.git")
    push = _git("push", remote, config.PUBLISH_BRANCH, check=False)
    if push.returncode != 0:
        raise RuntimeError("git push failed:\n" + push.stderr)
    return f"https://dnhcare.co.in/blog/{post.slug}.html"
