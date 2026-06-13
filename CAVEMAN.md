# CAVEMAN.md  —  DNH CARE SITE BRAIN

READ THIS FILE ALONE = KNOW EVERYTHING. PUSH TO GITHUB. DONE.
(plain caveman notes. short words. no fluff. trust this file.)

---

## STATUS (2026-06-14) — LIVE
- SITE IS LIVE at dnhcare.co.in. main == development. full v2 site + blog + 5 posts + SEO all deployed.
- BACKUP of old main = branch `backup-main-20260614` (commit df23bf7). rollback = `git push -f origin backup-main-20260614:main`.
- LOCAL BOT is running (this machine), PUBLISH_BRANCH=main -> Approve publishes LIVE. token via `gh auth token`.
  launcher = C:\Projects\3DWebsites\run_bot.ps1 (kills old + relaunches). restart from bash:
  `export GITHUB_TOKEN=$(gh auth token); powershell.exe -File C:\Projects\3DWebsites\run_bot.ps1 > log 2>&1` (run_in_background).
- ORACLE DEPLOY = STILL PENDING (cannot do from here — no VM access). user runs agent/bot/SETUP-ORACLE.md on the VM.
  on Oracle: set DNH_Telegram_Token, DNH_Telegram_ID, OPENROUTER_API_KEY, DNH_Github_Token (a PAT, not gh) as env;
  PUBLISH_BRANCH defaults to main. RUN ONLY ONE BOT AT A TIME (same Telegram token -> 409 conflict): stop local before starting Oracle.

---

## WHAT THIS IS
3D SCROLL WEBSITE. CLINIC. HOMEOPATHY. BENGALURU.
real clinic site = dnhcare.co.in (old Framer site).
THIS = new better site. cinematic. scroll-scrub. SEO strong.
GOAL = rank #1 local "homeopathy doctor Varthur Bengaluru".

## BRAND FACTS (use these everywhere, never change without asking)
- OFFICIAL NAME = "Dr. Nafia's Homoeopathic Medical Centre"  (short = "DNH Care")
- DOCTOR = Dr. Nafia M. BHMS, Vinayaka Mission University. + PG Diploma Counseling & Family Therapy.
- ADDRESS = Opp. KK School, Gunjur Main Road, Varthur, Bengaluru, Karnataka 560087
- PHONE = +91 96637 79358   (wa.me/919663779358 for WhatsApp)
- HOURS = Mon–Sat, 10am–1pm & 4pm–8pm
- REVIEWS = 4.9 stars, 150+ Google reviews   <-- 150 NOT 50. user corrected.
- PATIENTS = 5,100+ ;  3+ years
- INSTAGRAM = @dr.nafia.m
- AREAS SERVED = Varthur, Gunjur, Whitefield, Sarjapur Road, Balagere
- GEO = lat 12.9350, lng 77.7450  (APPROX. user must verify real GBP pin.)
- COLORS = deep forest green #07120d, gold #d9a441, sage #7fb89a, cream #f5f1e6
- FONTS = Cormorant Garamond (headings), Manrope (body)

## HOW THE 3D WORKS (no three.js!)
trick = canvas image-sequence scrub.
- 2 clips -> 180 JPG frames each (1600x900, q88).
- frames live in /frames/hero/ and /frames/botanical/.
- scroll position picks which frame draws on <canvas>. scrolling = plays clip.
- Lenis = smooth scroll. engine = scroll-cinematic.js.
- FRAMES NOW = locally rendered PLACEHOLDERS (python render_frames.py).
  WHY = Higgsfield workspace had 0 credits. NOT real AI clips yet.
  TO SWAP REAL CLIPS = see README.md. slice with ffmpeg into same folders. no code change.

## BLOG / JOURNAL  (feature B — built on development)
- LIVES IN = /blog/ folder.  URL = dnhcare.co.in/blog/
- blog/index.html = journal index. card grid. lists all posts. Blog schema.
- blog/<slug>.html = one post each. seed posts:
    eczema-and-bengaluru-weather.html (Skin)
    toddler-recurring-colds.html (Children)
    dust-allergy-season.html (Allergies)
- POST TEMPLATE (copy an existing post, it has everything):
    head: title, meta desc, canonical (.html), og, BlogPosting schema + BreadcrumbList schema.
    body: nav (../ paths, Journal active), scroll-progress, article-hero (breadcrumb + .post-cat-tag + h1 + .post-meta),
          main.article (.lede para, h2 sections, .med-disclaimer, .author-box, cta-row, .related),
          footer-grid + footer + action-bar + scroll script.
    paths from /blog/ = ../styles.css, ../index.html, ../skin-treatment.html, journal = index.html.
- WHEN ADDING A POST also: add a <a class="post-card"> to blog/index.html #posts (newest first),
  and add <loc> to sitemap.xml.
- "Journal" nav link is on ALL pages (root pages -> blog/index.html ; blog pages -> index.html).
- RULES: every post MUST have .med-disclaimer + author-box (E-E-A-T). NO overclaims (cure/guaranteed/no side effects/miracle).
  link to the matching service page. keep ~600-900 words, real local value, original.

## DAILY AGENT  (Python + Telegram bot on Oracle — BUILT on development)
- GOAL = 1 new post/day INTO /blog/, DRAFT only -> sent to Telegram with Approve/Reject ->
  on Approve the bot commits to main -> GitHub Pages auto-deploys. Approval happens IN TELEGRAM.
- ARCHITECTURE = standing Python service on the user's Oracle Cloud VM (systemd), long-polling Telegram.
- LLM PROVIDER = **OpenRouter** (OpenAI-compatible), NOT Anthropic. Free models by default.
  Model is RUNTIME-SWITCHABLE from Telegram (/model /models /setmodel), persisted in agent/bot/state.json (gitignored).
  Default = qwen/qwen3-next-80b-a3b-instruct:free; presets incl. llama-3.3-70b, gpt-oss-120b, gemma-4, nemotron (all :free).
  NOTE: OpenRouter's free roster changes — if a model 404s "unavailable for free", pick another via /models or /setmodel.
  Free models get rate-limited (429) upstream; llm.chat retries 4x; user can switch model if one is flaky.
- CODE = /agent/bot/  (a Python package):
    config.py    = Telegram creds from SYSTEM env (DNH_Telegram_Token / DNH_Telegram_ID); OpenRouter key + base url;
                   PRESET_MODELS; get_model()/set_model() persist to state.json; brand constants; category->service map.
    llm.py       = shared OpenRouter client + chat() with 429 retry.
    topics.py    = read/add/consume agent/topics.md; autoselect_viral_topic() = date-aware OpenRouter call (no web tool).
    content.py   = OpenRouter (current model) returns JSON -> robust parse -> Pydantic Post; Python assembles the post
                   HTML deterministically (schema/disclaimer/author/canonical/CTA always present).
    publisher.py = sync main, stage draft, run gate, on approve: insert blog index card + sitemap loc + mark topic done + git commit/push main.
    bot.py       = telegram bot: JobQueue daily at POST_TIME (IST); /generate /topics /addtopic /model /models /setmodel;
                   Approve/Reject buttons; Reject->reply feedback->regenerate.
    check_post.py (in /agent/) = the deterministic gate, run on every draft before it's shown.
    deploy/dnhcare-bot.service + SETUP-ORACLE.md = systemd unit + full Oracle deploy guide.
- SECRETS:
    Telegram = SYSTEM env vars DNH_Telegram_Token + DNH_Telegram_ID (already set on user's Windows machine; export on the VM).
    OPENROUTER_API_KEY = system env (already set) or .env.
    in agent/bot/.env: GITHUB_TOKEN (fine-grained PAT, Contents:RW on DNHCare), REPO_DIR, POST_TIME, optional DEFAULT_MODEL.
- IMPORTANT = the bot's working clone (REPO_DIR) must be on **main** and must contain blog/ + agent/ + agent/bot/.
  So MERGE development->main before deploying (blog + agent + bot all land on main together).
- TESTED locally: modules compile; live OpenRouter free-model generation produced a valid post that PASSED the gate
  (627 words); model set/get persistence works; JSON-LD valid. NOT yet run live on the VM (needs GitHub PAT + VM).

## FILES (the whole site)
- index.html ............ homepage. 2 scrub sections (#hero, #philosophy) + about/services/stories/faq/visit.
- skin-treatment.html ... service page (full template).
- allergy-treatment.html  service page.
- pediatric-care.html ... service page.
- migraine-treatment.html service page.
- womens-health.html .... service page.
- styles.css ............ ALL css (v2 redesign already merged in, bottom of file).
- scroll-cinematic.js ... scroll engine (v2: poster-frame instant load + lazy batches + progress bar + reduced-motion).
- sitemap.xml / robots.txt  SEO crawl files.
- render_frames.py ...... regenerates placeholder frames. `python render_frames.py [hero|botanical|all]`.
- Launch Demo.bat ....... double-click = run localhost + open browser.
- frames/ ............... 360 JPGs (~31 MB). the actual visuals. COMMITTED to git.
- README.md ............. how to swap in real Higgsfield clips.
- CAVEMAN.md ............ THIS FILE. context + runbook.

## RUN ON LOCALHOST
double-click `Launch Demo.bat`   ->  http://localhost:8347
OR:  cd to folder, `python -m http.server 8347`, open http://localhost:8347

## GITHUB  (REPO ALREADY EXISTS — DO NOT MAKE NEW ONE)
- REPO = https://github.com/shafeequealipt-dotcom/DNHCare
- account = shafeequealipt-dotcom (gh already logged in)
- branch = main
- DEPLOY = GitHub Pages. CNAME file = dnhcare.co.in  (Pages serves at the REAL domain).
  -> KEEP the CNAME file. never delete. if rebase needed, preserve it.
  -> Pages serves files at real path: /skin-treatment.html (NOT /skin-treatment).
  -> so all canonical/og/sitemap URLs use .html to match (no 404 canonicals). home = "/".
  -> NOTE: was the old Framer site live at dnhcare.co.in. DNS may or may not point to Pages yet.
- BRANCHES:
    main        = LIVE. deploys to dnhcare.co.in. only touch via approved merge.
    development = WORK HERE. push freely, does NOT deploy. (current default branch for changes.)
- MERGE FLOW (user chose: PR + review each time):
    do work on development -> commit -> push origin development
    when user says "ship"/"approve": open PR development->main with `gh pr create --base main --head development`
    user reviews + merges on GitHub -> main rebuilds -> domain live in ~1-2 min.
    NEVER push straight to main without user approval.
PUSH PENDING CHANGES (on development) =
    git add -A
    git commit -m "your message"
    git push                       # pushes to origin/development (upstream set)
(if remote rejects: `git fetch origin` then `git rebase origin/<branch>` (keeps CNAME), then push.)
(if push asks auth, gh handles it. https protocol.)

## SEO STATE  (DONE = on the site already)
DONE:
- title/meta/OG/canonical on every page. geo-keyworded ("Varthur, Bengaluru").
- 1 clean H1 per page.
- JSON-LD: MedicalClinic (+aggregateRating 4.9/150, hasMap, areaServed, openingHours, physician),
  FAQPage (home), BreadcrumbList (every service page).
- visible FAQ matches FAQPage schema EXACTLY (YMYL-safe wording, no "cure"/"no side effects").
- 5 service pages, internal-linked: nav "Treatments" dropdown + homepage cards + footer + related-treatment blocks.
- crawlable NAP in 3-col footer + areas served.
- embedded Google Map + "Get directions" in #visit.
- sticky mobile action bar (Call/WhatsApp/Directions).
- trust chips in hero (★4.9 150+ reviews, landmark).
- scroll progress bar. prefers-reduced-motion honored.
- perf: hero poster frame preloads instantly, other 179 lazy-load (page weight ~30MB -> ~0.3MB first paint).

## PENDING / TODO  (load these next time if not done)
1. REAL HIGGSFIELD CLIPS — frames are placeholders. needs Higgsfield credits. see README.md. (blocked on $)
2. VERIFY GEO COORDS — user must give exact Google Maps pin; update geo + map links if different.
3. CONFIRM HOURS — site uses 10–1 / 4–8 (website). Practo says 9:30 start. user to confirm.
4. OFF-SITE (user only, cannot do in code): Google Business Profile services+desc+UTM+Q&A,
   Search Console add property + submit sitemap, fix Practo name/hours to match.
5. FEATURE BACKLOG — see below. user picks. DO NOT build without user pick.

## FEATURE BACKLOG  (proposed, NOT built. user chooses.)
A. Booking/enquiry form section (name+phone+concern -> WhatsApp prefilled or Formspree). conversion + dwell time.
B. Blog / articles section — DONE (built on development). daily agent = stage 2, pending.
C. Real doctor photo + clinic photos (replace abstract frames in spots) — E-E-A-T trust + GBP sync.
D. Google reviews live widget (pull real reviews) instead of static quotes.
E. Hindi/Kannada language toggle — local audience reach.
F. "Book appointment" calendar (Calendly-style) embed.
G. Symptom -> treatment finder (small interactive quiz) — engagement + internal linking.
H. Deploy live (Netlify/Vercel/Cloudflare Pages) w/ clean URLs + real domain swap from Framer.
I. Web vitals / analytics (GA4 or Plausible) + Search Console wiring.
J. Service schema per treatment page (MedicalProcedure / Service) for richer results.

## RULES / GOTCHAS
- SEO = FIRST objective. every change must not hurt crawlability or page speed.
- NO medical overclaims. no "cure", "guaranteed", "no side effects". YMYL health rules.
- keep frames ~180, 1600px, q88. more/bigger = slow = bad SEO.
- continuous-motion clips only (no hard cuts — ugly scrubbed backward).
- v2 redesign = APPROVED and merged. it IS the live version now. no v2 files anymore.
- headless screenshot tool sometimes blanks sticky-canvas — verify via DOM/pixel sample + real browser.
