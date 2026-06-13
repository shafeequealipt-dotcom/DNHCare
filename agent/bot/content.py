"""Generate a blog post: an OpenRouter model produces structured JSON content, Python
assembles the HTML deterministically so schema, disclaimer, author box, canonical and
CTA are always present and the safety gate passes."""
import re
import json
import html
import datetime
from typing import List
from pydantic import BaseModel, Field, ValidationError
from . import config, llm


class Section(BaseModel):
    heading: str
    paragraphs: List[str] = Field(default_factory=list)
    bullets: List[str] = Field(default_factory=list)


class FAQ(BaseModel):
    question: str
    answer: str


class Post(BaseModel):
    title: str
    slug: str
    meta_description: str
    category: str
    read_minutes: int
    lede: str
    sections: List[Section]
    faqs: List[FAQ]


_SCHEMA = """{
  "title": "string",
  "slug": "short-lowercase-hyphenated-no-extension",
  "meta_description": "140-158 character summary",
  "category": "one of: Skin | Allergies | Children | Migraine | Women",
  "read_minutes": 4,
  "lede": "opening paragraph",
  "sections": [{"heading": "string", "paragraphs": ["..."], "bullets": ["...optional..."]}],
  "faqs": [{"question": "string", "answer": "string"}]
}"""

SYSTEM = f"""You are the staff writer for {config.CLINIC_NAME}, a homeopathy clinic in
Varthur, Bengaluru (Dr. Nafia M, BHMS). Write a single blog post in plain, warm,
trustworthy language for local families.

HARD RULES (a medical/YMYL site — violations are rejected):
- NEVER use: cure, cures, guaranteed, "no side effects", "100% safe", miracle,
  "permanent cure", "instant relief", risk-free. No promises of outcomes. Don't
  diagnose the reader.
- Use measured language: "individualized", "may", "supports", "reviewed over time".
- Be genuinely useful and ORIGINAL. Mention Varthur / Whitefield / Bengaluru context
  where natural. 600-900 words across the sections. 3-4 sections.
- category MUST be exactly one of: {config.CATEGORIES}.
- meta_description: 140-158 characters. Include 2-3 FAQs with safe answers.

Reply with ONE JSON object and NOTHING else — no markdown fences, no commentary.
The JSON must match this shape exactly:
{_SCHEMA}"""


def _slugify(s: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s[:70] or "post"


def _extract_json(text: str) -> dict:
    """Pull the first JSON object out of a model reply (tolerates ``` fences / prose)."""
    t = text.strip()
    t = re.sub(r"^```(?:json)?", "", t).strip()
    t = re.sub(r"```$", "", t).strip()
    start, end = t.find("{"), t.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object in model reply")
    return json.loads(t[start:end + 1])


def generate_post(topic: str, feedback: str = "") -> Post:
    """Generate structured post content via the currently-selected OpenRouter model.
    `feedback` is appended on regeneration. Retries once on a parse/validation error."""
    ask = f"Write the post for this topic:\n{topic}\n"
    if feedback:
        ask += (f"\nThe previous draft was REJECTED by the editor. Apply this "
                f"feedback and rewrite accordingly:\n{feedback}\n")
    messages = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": ask}]
    last_err = None
    for attempt in range(2):
        resp = llm.chat(messages, temperature=0.6, max_tokens=4000)
        raw = resp.choices[0].message.content or ""
        try:
            post = Post(**_extract_json(raw))
            if post.category not in config.CATEGORIES:
                post.category = config.CATEGORIES[0]
            post.slug = _slugify(post.slug or post.title)
            return post
        except (ValueError, ValidationError) as e:
            last_err = e
            messages.append({"role": "assistant", "content": raw[:2000]})
            messages.append({"role": "user", "content":
                             "That was not valid JSON for the required shape. "
                             "Reply again with ONLY the JSON object, no fences."})
    raise RuntimeError(f"model did not return valid post JSON: {last_err}")


def _esc(s: str) -> str:
    return html.escape(s, quote=True)


def render_html(post: Post, recent_posts: List[dict]) -> str:
    """recent_posts: list of {slug, title, category} for the 'Keep reading' block."""
    today = datetime.date.today().isoformat()
    svc_file, svc_label = config.CATEGORY_SERVICE[post.category]
    title_t = _esc(post.title)
    meta = _esc(post.meta_description)
    crumb_title = _esc(post.title)
    # JSON-encoded values for the <script type="application/ld+json"> blocks
    title_json = json.dumps(post.title)
    meta_json = json.dumps(post.meta_description)
    cat_json = json.dumps(post.category)
    crumb_json = json.dumps(post.title)

    sections_html = []
    for s in post.sections:
        block = [f"    <h2>{_esc(s.heading)}</h2>"]
        for p in s.paragraphs:
            block.append(f"    <p>{_esc(p)}</p>")
        if s.bullets:
            block.append("    <ul>")
            block += [f"      <li>{_esc(b)}</li>" for b in s.bullets]
            block.append("    </ul>")
        sections_html.append("\n".join(block))
    sections_html = "\n\n".join(sections_html)

    faqs_html = "\n".join(
        f"      <details><summary>{_esc(f.question)}</summary>"
        f"<p>{_esc(f.answer)}</p></details>" for f in post.faqs)

    related = [f'        <a href="{svc_file}"><span>Treatment</span>{_esc(svc_label)}</a>']
    for rp in recent_posts[:2]:
        related.append(
            f'        <a href="{rp["slug"]}.html"><span>{_esc(rp["category"])}</span>'
            f'{_esc(rp["title"])}</a>')
    related_html = "\n".join(related)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{title_t} | DNH Care Journal</title>
  <meta name="description" content="{meta}" />
  <link rel="canonical" href="https://dnhcare.co.in/blog/{post.slug}.html" />
  <meta property="og:type" content="article" />
  <meta property="og:url" content="https://dnhcare.co.in/blog/{post.slug}.html" />
  <meta property="og:title" content="{title_t}" />
  <meta property="og:description" content="{meta}" />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;0,700;1,500&family=Manrope:wght@300;400;500;600;700&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="../styles.css" />
  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "BlogPosting",
    "headline": {title_json},
    "description": {meta_json},
    "datePublished": "{today}",
    "dateModified": "{today}",
    "articleSection": {cat_json},
    "url": "https://dnhcare.co.in/blog/{post.slug}.html",
    "mainEntityOfPage": "https://dnhcare.co.in/blog/{post.slug}.html",
    "author": {{ "@type": "Person", "name": "Dr. Nafia M", "jobTitle": "Homeopathic Physician", "alumniOf": "Vinayaka Mission University" }},
    "publisher": {{ "@type": "MedicalClinic", "name": "Dr. Nafia's Homoeopathic Medical Centre", "@id": "https://dnhcare.co.in/#clinic" }}
  }}
  </script>
  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    "itemListElement": [
      {{ "@type": "ListItem", "position": 1, "name": "Home", "item": "https://dnhcare.co.in/" }},
      {{ "@type": "ListItem", "position": 2, "name": "Journal", "item": "https://dnhcare.co.in/blog/" }},
      {{ "@type": "ListItem", "position": 3, "name": {crumb_json}, "item": "https://dnhcare.co.in/blog/{post.slug}.html" }}
    ]
  }}
  </script>
</head>
<body>
  <div class="scroll-progress" aria-hidden="true"><b></b></div>

  <nav class="nav">
    <a class="brand" href="../index.html">DNH<span> CARE</span><em>Dr. Nafia's Homoeopathic Medical Centre</em></a>
    <div class="nav-links">
      <a href="../index.html#about">About</a>
      <div class="nav-drop">
        <a href="../index.html#services">Treatments &#9662;</a>
        <div class="drop-menu">
          <a href="../skin-treatment.html">Skin Complaints</a>
          <a href="../allergy-treatment.html">Allergies &amp; Sinusitis</a>
          <a href="../pediatric-care.html">Pediatric Care</a>
          <a href="../migraine-treatment.html">Migraine &amp; Headaches</a>
          <a href="../womens-health.html">Women's Health &amp; Thyroid</a>
        </div>
      </div>
      <a href="index.html">Journal</a>
      <a href="../index.html#visit">Visit</a>
    </div>
    <a class="nav-cta" href="https://wa.me/919663779358" target="_blank" rel="noopener">Book on WhatsApp</a>
  </nav>

  <header class="article-hero">
    <nav class="crumbs" aria-label="Breadcrumb">
      <a href="../index.html">Home</a> &rsaquo; <a href="index.html">Journal</a> &rsaquo; {crumb_title}
    </nav>
    <span class="post-cat-tag">{post.category}</span>
    <h1>{title_t}</h1>
    <div class="post-meta">
      <span class="by">By Dr. Nafia M</span><span class="dot">&middot;</span>
      <span>{today}</span><span class="dot">&middot;</span>
      <span>{post.read_minutes} min read</span>
    </div>
  </header>

  <main class="article">
    <p class="lede">{_esc(post.lede)}</p>

{sections_html}

    <h2>Common questions</h2>
    <div class="faqs">
{faqs_html}
    </div>

    <div class="med-disclaimer">
      This article is general information, not medical advice, and does not replace a
      consultation. Do not start or stop any treatment based on it alone. If you use
      prescribed medication, continue it and bring it to your visit so care can be
      coordinated safely. For any severe, sudden or worsening symptoms, seek prompt
      in-person medical attention.
    </div>

    <div class="cta-row">
      <a class="big-cta" href="https://wa.me/919663779358" target="_blank" rel="noopener">Book a consultation</a>
      <a class="back-link" href="../{svc_file}">{_esc(svc_label)} &rarr;</a>
    </div>

    <div class="author-box">
      <div class="avatar" aria-hidden="true">N</div>
      <div>
        <h4>Dr. Nafia M</h4>
        <p>Homeopathic physician (BHMS, Vinayaka Mission University) with a PG Diploma in
        Counseling &amp; Family Therapy. She leads Dr. Nafia's Homoeopathic Medical Centre in
        Varthur, Bengaluru.</p>
      </div>
    </div>

    <div class="related">
      <h2>Keep reading</h2>
      <div class="related-row">
{related_html}
      </div>
    </div>
  </main>

  <div class="footer-grid">
    <div>
      <h5>Dr. Nafia's Homoeopathic Medical Centre</h5>
      <p>Opp. KK School, Gunjur Main Road, Varthur,<br/>Bengaluru, Karnataka 560087<br/>
      <a href="tel:+919663779358">+91 96637 79358</a> &middot; Mon&ndash;Sat, 10am&ndash;1pm &amp; 4pm&ndash;8pm</p>
    </div>
    <div>
      <h5>Treatments</h5>
      <ul>
        <li><a href="../skin-treatment.html">Skin complaints</a></li>
        <li><a href="../allergy-treatment.html">Allergies &amp; sinusitis</a></li>
        <li><a href="../pediatric-care.html">Pediatric care</a></li>
        <li><a href="../migraine-treatment.html">Migraine &amp; headaches</a></li>
        <li><a href="../womens-health.html">Women's health &amp; thyroid</a></li>
      </ul>
    </div>
    <div>
      <h5>Areas served</h5>
      <ul><li>Varthur</li><li>Gunjur</li><li>Whitefield</li><li>Sarjapur Road</li><li>Balagere</li></ul>
    </div>
  </div>
  <footer class="footer">
    <span>&copy; 2026 Dr. Nafia's Homoeopathic Medical Centre (DNH Care) &middot; Healing, the gentle way.</span>
  </footer>

  <div class="action-bar">
    <a href="tel:+919663779358"><strong>Call</strong></a>
    <a href="https://wa.me/919663779358" target="_blank" rel="noopener"><strong>WhatsApp</strong></a>
    <a href="https://www.google.com/maps/dir/?api=1&destination=Dr.+Nafia's+Homoeopathic+Medical+Centre+Gunjur+Main+Road+Varthur+Bengaluru" target="_blank" rel="noopener"><strong>Directions</strong></a>
  </div>

  <script>
    addEventListener("scroll", () => {{
      const b = document.querySelector(".scroll-progress b");
      const max = document.documentElement.scrollHeight - innerHeight;
      if (b) b.style.width = (max > 0 ? (scrollY / max) * 100 : 0) + "%";
    }}, {{ passive: true }});
  </script>
</body>
</html>
"""
