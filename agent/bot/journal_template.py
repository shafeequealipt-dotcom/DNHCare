"""Black-and-gold Journal template, shared by the bot (new posts) and the demo builder
(posts converted from the old design). Pure string functions: no config import, so
the demo builder can use it without the bot's env vars.

Layout it assumes (same URLs as the live site):
  index.html            home, with the latest cards between JOURNAL_LATEST markers
  blog/index.html       the Journal, every card inside POSTS_MARKER
  blog/<slug>.html      one article, served at /blog/<slug>
  css/site.css, js/article.js
"""
import re
import html

POSTS_MARKER = '<div class="j-grid" id="posts">\n'
LATEST_START = "<!-- journal:latest -->\n"
LATEST_END = "<!-- /journal:latest -->"
HOME_LATEST = 6

WA = "https://wa.me/919663779358"
IG = "https://www.instagram.com/dr.nafia.m"
MAPS = ("https://www.google.com/maps/dir/?api=1&destination=Dr.+Nafia's+Homoeopathic"
        "+Medical+Centre+Gunjur+Main+Road+Varthur+Bengaluru")
FONTS = ("https://fonts.googleapis.com/css2?family=Mrs+Saint+Delafield&family="
         "Raleway:wght@200;300;400;500;600;700&display=swap")
FAVICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'"
           "%3E%3Crect width='32' height='32' rx='6'/%3E%3Ctext x='16' y='23' font-family="
           "'Georgia' font-size='20' font-weight='700' fill='%23d9ad7c' text-anchor='middle'"
           "%3ED%3C/text%3E%3C/svg%3E")


def esc(s: str) -> str:
    return html.escape(s, quote=True)


def head(title, description, root, *, canonical="", robots="", extra=""):
    """<head> for any page. `root` is the path back to the site root ("" or "../")."""
    lines = [
        '<!doctype html>', '<html lang="en">', '<head>',
        '  <meta charset="utf-8" />',
        '  <meta name="viewport" content="width=device-width, initial-scale=1" />',
        f'  <title>{esc(title)}</title>',
        f'  <meta name="description" content="{esc(description)}" />',
    ]
    if robots:
        lines.append(f'  <meta name="robots" content="{robots}" />')
    if canonical:
        lines.append(f'  <link rel="canonical" href="{canonical}" />')
    lines += [
        '  <meta name="theme-color" content="#000000" />',
        '  <link rel="preconnect" href="https://fonts.googleapis.com" />',
        '  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />',
        f'  <link href="{FONTS}" rel="stylesheet" />',
        f'  <link rel="icon" href="{FAVICON}" />',
        f'  <link rel="stylesheet" href="{root}css/site.css" />',
    ]
    if extra:
        lines.append(extra.rstrip())
    lines += ['</head>', '<body>', '']
    return "\n".join(lines) + "\n"


def nav(root):
    home = root or "./"
    return f"""  <header class="nav">
    <div class="nav-left">
      <button class="burger" aria-label="Open menu" aria-expanded="false" aria-controls="menu"><i></i><i></i><i></i></button>
      <a class="wordmark foil-text" href="{home}">DNH CARE</a>
    </div>
    <div class="nav-right">
      <div class="nav-sub">Dr. Nafia's Homoeopathic Medical Centre<span>Varthur, Bengaluru</span></div>
      <a class="ig-icon" href="{IG}" target="_blank" rel="noopener" aria-label="Dr. Nafia on Instagram"><svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4.2"/><circle cx="17.3" cy="6.7" r=".6"/></svg></a>
      <a class="btn-foil" href="{WA}" target="_blank" rel="noopener">Book now</a>
    </div>
  </header>

  <nav class="menu" id="menu" aria-label="Site menu">
    <a href="{home}#consultation">The consultation</a>
    <a href="{home}#skin">Treatments</a>
    <a href="{home}#physician">Dr. Nafia M</a>
    <a href="{home}#stories">Patient stories</a>
    <a href="{root}blog/">Journal</a>
    <a href="{home}#faq">Questions</a>
    <a href="{home}#visit">Visit the clinic</a>
    <a href="{IG}" target="_blank" rel="noopener">Instagram</a>
    <p>Mon–Sat, 10am–1pm &amp; 4pm–8pm · <a style="display:inline;font-size:inherit;border:0;padding:0" href="tel:+919663779358">+91 96637 79358</a></p>
  </nav>

"""


def footer(root):
    return f"""  <footer class="foot">
    <div class="wrap">
      <div class="foot-grid">
        <div><h5>Dr. Nafia's Homoeopathic Medical Centre</h5><p>Opp. KK School, Gunjur Main Road, Varthur,<br />Bengaluru, Karnataka 560087<br /><a href="tel:+919663779358">+91 96637 79358</a><br /><a href="{IG}" target="_blank" rel="noopener">Instagram: @dr.nafia.m</a></p></div>
        <div><h5>Treatments</h5><ul>
          <li><a href="{root}skin-treatment">Skin complaints</a></li>
          <li><a href="{root}allergy-treatment">Allergies &amp; sinusitis</a></li>
          <li><a href="{root}pediatric-care">Pediatric care</a></li>
          <li><a href="{root}migraine-treatment">Migraine &amp; headaches</a></li>
          <li><a href="{root}womens-health">Women's health &amp; thyroid</a></li>
          <li><a href="{root}blog/">Journal</a></li>
        </ul></div>
        <div><h5>Areas served</h5><ul><li>Varthur</li><li>Gunjur</li><li>Whitefield</li><li>Sarjapur Road</li><li>Balagere</li></ul></div>
      </div>
      <div class="foot-base">
        <span>© 2026 Dr. Nafia's Homoeopathic Medical Centre (DNH Care)</span>
        <span><a href="{root}terms-and-conditions">Terms</a> · <a href="{root}privacy-policy">Privacy</a> · <a href="{root}cancellation-and-refund-policy">Cancellation &amp; Refunds</a> · <a href="{root}contact-us">Contact</a></span>
      </div>
    </div>
  </footer>

  <div class="action-bar">
    <a href="tel:+919663779358">Call</a>
    <a href="{WA}" target="_blank" rel="noopener">WhatsApp</a>
    <a href="{MAPS}" target="_blank" rel="noopener">Directions</a>
  </div>

"""


def card(slug, category, title, description, foot, prefix=""):
    """One Journal card. `prefix` is "" inside blog/ and "blog/" on the home page."""
    return (f'        <a class="j-card" data-cat="{esc(category)}" href="{prefix}{slug}">\n'
            f'          <span class="eyebrow">{esc(category)}</span>\n'
            f'          <h3>{esc(title)}</h3>\n'
            f'          <p>{esc(description)}</p>\n'
            f'          <small>{esc(foot)}</small>\n'
            f'        </a>\n')


def article_page(*, title, description, canonical, category, meta_line, body,
                 more_cards="", head_extra="", robots=""):
    """A full article page at blog/<slug>. `body` is the inner HTML of
    <main class="article"> (lede, sections, FAQs, disclaimer, CTA, author box, related);
    `more_cards` are card() strings for the "Continue reading" row."""
    more = ""
    if more_cards:
        more = f"""  <section class="journal art-more"><div class="wrap">
    <div class="j-head"><div><p class="eyebrow">More on {esc(category)}</p><h2>Continue reading</h2></div><a class="btn-line" href="./">All articles</a></div>
    <div class="j-grid">
{more_cards.rstrip()}
    </div></div></section>
"""
    return (head(f"{title} | DNH Care Journal", description, "../", canonical=canonical,
                 robots=robots, extra=head_extra)
            + nav("../")
            + f"""  <div class="scroll-progress" aria-hidden="true"><b></b></div>
  <header class="art-hero" id="top">
    <div class="ambient" aria-hidden="true"></div>
    <div class="art-col">
      <nav class="crumbs" aria-label="Breadcrumb"><a href="../">Home</a> › <a href="./">Journal</a></nav>
      <p class="eyebrow">{esc(category)}</p>
      <h1>{esc(title)}</h1>
      <p class="art-meta">{esc(meta_line)}</p>
    </div>
  </header>

  <main class="article">
{body.strip(chr(10))}
  </main>

{more}
"""
            + footer("../")
            + '  <script src="../js/article.js"></script>\n</body>\n</html>\n')


def journal_page(cards_html, count, categories, *, head_extra="", robots=""):
    """The Journal (blog/index.html) with every card, newest first."""
    chips = '<button class="on" data-cat="all">All</button>' + "".join(
        f'<button data-cat="{esc(c)}">{esc(c)}</button>' for c in categories)
    og = """  <meta property="og:type" content="website" />
  <meta property="og:url" content="https://dnhcare.co.in/blog/" />
  <meta property="og:title" content="Journal — Homeopathy Notes from DNH Care, Varthur" />
  <meta property="og:description" content="Plain-language homeopathy notes from Dr. Nafia's Homoeopathic Medical Centre, Varthur." />
"""
    return (head("Journal — Homeopathy Notes from DNH Care, Varthur | DNH Care",
                 "Plain-language homeopathy notes from Dr. Nafia's Homoeopathic Medical Centre, "
                 "Varthur — skin, allergies, children's health, migraine and women's health, "
                 "explained simply.",
                 "../", canonical="https://dnhcare.co.in/blog/", robots=robots,
                 extra=og + head_extra)
            + nav("../")
            + f"""  <main id="top">
    <section class="j-hero">
      <div class="ambient" aria-hidden="true"></div>
      <div class="wrap">
        <p class="eyebrow rise d1">Journal</p>
        <h1 class="rise d2">Notes on <span class="foil-text">gentle healing.</span></h1>
        <p class="rise d3"><span class="j-count">{count}</span> articles from DNH Care, Varthur.</p>
      </div>
    </section>
    <div class="j-filter" role="group" aria-label="Filter by topic"><div class="tabs-inner">{chips}</div></div>
    <section class="journal">
      <div class="wrap">
        {POSTS_MARKER}{cards_html}        </div>
        <div class="care-more"><button class="btn-line" id="more">Show more</button></div>
      </div>
    </section>
  </main>

"""
            + footer("../")
            + '  <script src="../js/journal.js"></script>\n</body>\n</html>\n')


def add_to_journal(index_html, card_html):
    """Put a new card first in blog/index.html and bump the article count."""
    if POSTS_MARKER not in index_html:
        raise RuntimeError("blog/index.html is not the new Journal page (no posts grid)")
    index_html = index_html.replace(POSTS_MARKER, POSTS_MARKER + card_html, 1)
    return re.sub(r'<span class="j-count">(\d+)</span>',
                  lambda m: f'<span class="j-count">{int(m[1]) + 1}</span>', index_html, count=1)


def add_to_home(home_html, card_html):
    """Put a new card first in the home page's latest row, keep HOME_LATEST, bump
    the "See all N articles" count."""
    if LATEST_START not in home_html or LATEST_END not in home_html:
        raise RuntimeError("index.html has no journal:latest markers")
    a = home_html.index(LATEST_START) + len(LATEST_START)
    b = home_html.index(LATEST_END)
    cards = re.findall(r'[ \t]*<a class="j-card".*?</a>\n', home_html[a:b], re.S)
    row = "".join(([card_html] + cards)[:HOME_LATEST])
    home_html = home_html[:a] + row + "        " + home_html[b:]
    return re.sub(r'See all (\d+) articles',
                  lambda m: f'See all {int(m[1]) + 1} articles', home_html, count=1)


def parse_cards(index_html):
    """Cards in blog/index.html as {slug, category, title}, newest first."""
    out = []
    for m in re.finditer(r'<a class="j-card" data-cat="[^"]*" href="([^"]+)">\s*'
                         r'<span class="eyebrow">(.*?)</span>\s*<h3>(.*?)</h3>', index_html, re.S):
        out.append({"slug": m[1], "category": html.unescape(m[2]).strip(),
                    "title": html.unescape(m[3]).strip()})
    return out
