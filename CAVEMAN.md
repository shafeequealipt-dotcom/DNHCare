# CAVEMAN.md  —  DNH CARE SITE BRAIN

READ THIS FILE ALONE = KNOW EVERYTHING. PUSH TO GITHUB. DONE.
(plain caveman notes. short words. no fluff. trust this file.)

---

## STATUS (2026-07-02) — LIVE ON ORACLE, BOT PUBLISHING TO MAIN
- SITE IS LIVE at dnhcare.co.in (served from Oracle Nginx, main branch, clean URLs).
- 2026-07-02 FIXES (all live on main + Oracle):
    * check_post.py: clean-URL service-link regex (was requiring .html — rejected every post).
    * check_post.py: NEW remedy-name gate (BANNED_REMEDY_NAMES) — blocks Belladonna, Hepar sulph,
      Pulsatilla, etc. from patient-facing prose. content_prompt.txt also forbids naming remedies.
      Cleaned 10 old posts that had listed remedy names.
    * daily agent: duplicate-post prevention (topic memory + slug guard) — see DAILY AGENT below.
- ORACLE bot GITHUB TOKEN ROTATED 2026-07-02: old DNH_Github_Token had expired (push 401).
  New fine-grained PAT is in /home/ubuntu/DNHCare/agent/bot/.env (Contents:R/W). Bot restarted.
  DEPLOY RULE: test token auth + dry-run push BEFORE deploying bot changes (see DEPLOYMENT RULES).
- BACKUP of old main = branch `backup-main-20260614` (commit df23bf7). rollback = `git push -f origin backup-main-20260614:main`.
- ORACLE DEPLOY = DONE (2026-06-14). bot runs 24/7 on the Oracle VM as a systemd service.
    host = ubuntu@140.245.230.251 (Ubuntu 22.04). ssh key (local) = ~/.ssh/oracle.key.
    venv = /home/ubuntu/dnhvenv ; secrets = /home/ubuntu/DNHCare/agent/bot/.env (chmod 600).
    service = dnhcare-bot (systemd, enabled=survives reboot). manage: `sudo systemctl {status|restart|stop} dnhcare-bot` ; logs `journalctl -u dnhcare-bot -f`.
    config: PUBLISH_BRANCH=main, POST_TIME=06:00 IST, model=openai/gpt-oss-120b:free, token=DNH_Github_Token (fine-grained PAT, Contents:R/W).
- LOCAL bot = STOPPED (Oracle is the only instance). RUN ONLY ONE BOT (same Telegram token -> 409).
- GOTCHA hit during deploy: fine-grained PAT needs **Contents: Read AND write** + the repo selected under "Only select repositories".

## HOSTING ARCHITECTURE (2026-06-19)
TWO ENVIRONMENTS ON ORACLE VM (140.245.230.251):
  production  = ~/DNHCare          (main branch)      -> dnhcare.co.in
  staging     = ~/DNHCare-staging  (development branch)-> staging.dnhcare.co.in

AUTO-DEPLOY via GitHub Actions (secrets: ORACLE_SSH_KEY, ORACLE_HOST):
  push to development -> .github/workflows/deploy-staging.yml    -> ssh pulls ~/DNHCare-staging
  push/merge to main  -> .github/workflows/deploy-production.yml -> ssh pulls ~/DNHCare

BOT FLOW (2026-06-19):
  bot generates post -> Approve in Telegram -> pushes to main -> deploy-production.yml -> dnhcare.co.in live in ~15s
  staging.dnhcare.co.in = used for manual dev/design changes (push to development branch)

NGINX on Oracle (already installed + active):
  /etc/nginx/sites-enabled/dnhcare.co.in         -> serves ~/DNHCare (clean URLs: /blog/my-post)
  /etc/nginx/sites-enabled/staging.dnhcare.co.in -> serves ~/DNHCare-staging

SSL = certbot already installed. run AFTER DNS propagates:
  sudo certbot --nginx -d dnhcare.co.in -d www.dnhcare.co.in --non-interactive --agree-tos -m shafeequealipt@gmail.com
  sudo certbot --nginx -d staging.dnhcare.co.in --non-interactive --agree-tos -m shafeequealipt@gmail.com

DNS CHANGES NEEDED (user does in registrar — PENDING):
  dnhcare.co.in     A record -> 140.245.230.251  (remove GitHub Pages CNAME first)
  www.dnhcare.co.in A record -> 140.245.230.251
  staging.dnhcare.co.in A record -> 140.245.230.251

CLEAN URLs: Nginx rewrites /blog/my-post -> serves blog/my-post.html (no extension in URL).
  Old .html URLs 301-redirect to clean URLs automatically.

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
- CHECK_POST GATE (agent/check_post.py) blocks a draft if ANY of:
    banned overclaim word (cure/guaranteed/miracle/no side effects/...); specific homeopathic
    REMEDY NAME (Belladonna, Hepar sulph, Pulsatilla + 30 more — never name remedies in prose);
    missing required element (med-disclaimer, author-box, BlogPosting/BreadcrumbList schema,
    canonical, scroll-progress, footer NAP, WhatsApp CTA); no internal service-page link
    (clean URL, no .html); body < 380 words; missing/too-short title or meta description.
- GOOGLE BUSINESS PROFILE AUTO-POST (LIVE since 2026-07-07; all 5 env vars set on Oracle):
    on ✅ Approve, after the blog publishes, bot ALSO creates a GBP local post.
    GBP failure never blocks the blog.
    STYLE (2026-07-08): gbp_summary = informative MINI-ARTICLE (4-6 sentences,
          600-1200 chars, keyword+locality in FIRST sentence — only ~100 chars show
          before truncation; practical takeaways; call-the-clinic close). NOT a teaser.
    CTA (2026-07-08): default = CALL ("Call now" button -> clinic's listed number;
          v4 API requires url UNSET for CALL; blog URL appended as plain text
          "Read the full guide: <url>"). Toggle: /gbp cta call | /gbp cta learn
          (LEARN_MORE = clickable link to post). Persisted in state.json (gbp_cta).
    OPTIONAL IMAGE: set GBP_POST_IMAGE_URL in .env (public https) to attach a photo
          to every post. Unset = no image (dormant).
    CODE: agent/bot/gbp.py (token refresh + create/delete local post, stdlib urllib);
          agent/bot/gbp_auth.py (one-time OAuth: `login` mints refresh token,
          `discover` lists account/location ids); content.py Post.gbp_summary +
          gbp_blurb() fallback chain (summary -> title+lede+invite -> title+meta+invite)
          with the same banned-words + remedy-names scan as the gate;
          /gbp on|off|cta|status in Telegram.
    ENV: GBP_CLIENT_ID, GBP_CLIENT_SECRET, GBP_REFRESH_TOKEN, GBP_ACCOUNT_ID,
          GBP_LOCATION_ID (+ optional GBP_POST_IMAGE_URL). GBP = OAuth refresh-token
          only, NO service accounts. LocalPost.summary limit = 1500 chars.
          ROLLBACK: branch backup-pre-gbp-20260707; /gbp off kills posting instantly.
- DUPLICATE-POST PREVENTION (added 2026-07-02):
    1. topics.autoselect_viral_topic() feeds the whole "Done" list into the LLM prompt
       ("do NOT propose any of these again") — no repeat topics when the queue is empty.
    2. publisher.slug_is_published() + guard in bot._generate_blocking(): a draft whose slug
       is already committed to git is REJECTED (Telegram message), never overwrites a live post.
       Checks git-tracked files, so gate-retries of the in-flight draft are not false-flagged.
- SECRETS:
    Telegram = SYSTEM env vars DNH_Telegram_Token + DNH_Telegram_ID (already set on user's Windows machine; export on the VM).
    OPENROUTER_API_KEY = system env (already set) or .env.
    in agent/bot/.env: GITHUB_TOKEN (fine-grained PAT, Contents:RW on DNHCare), REPO_DIR, POST_TIME, optional DEFAULT_MODEL.
- IMPORTANT = bot REPO_DIR = /home/ubuntu/DNHCare-staging (development branch). Bot pushes to development.
  GitHub Actions deploy-staging.yml auto-pulls staging. User merges dev->main -> deploy-production.yml auto-pulls production.
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
- DEPLOY = Oracle VM via Nginx (replacing GitHub Pages). See HOSTING ARCHITECTURE above.
  -> CNAME file preserved (needed until DNS cutover fully completes, then can be left or removed).
  -> Oracle Nginx serves clean URLs: /blog/my-post (not .html). Old .html URLs 301 to clean.
  -> canonical/og/schema URLs: update to clean URLs once DNS is live on Oracle.
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
- JSON-LD: MedicalClinic (+aggregateRating 4.9/150, hasMap, areaServed, openingHours, physician,
    priceRange, currenciesAccepted, paymentAccepted, logo, availableService list),
  FAQPage (home + ALL 5 service pages), BreadcrumbList (every service page + blog posts).
- ADDED 2026-06-19: Physician entity @id=/#doctor (full credentials, BHMS + PG Diploma, E-E-A-T).
- ADDED 2026-06-19: WebSite entity @id=/#website (domain graph node, linked to clinic).
- ADDED 2026-06-19: MedicalTherapy entity on each service page (medicineSystem=Homeopathic,
    relevantSpecialty per page, indication list, provider→#clinic).
- ADDED 2026-06-19: MedicalWebPage on each service page (reviewedBy→#doctor, medicalAudience=Patients,
    about→therapy entity, isPartOf→#website, lastReviewed=2026-06-14).
- ADDED 2026-06-19: BlogPosting enhanced: author @id→#doctor, reviewedBy→#doctor, isPartOf→#website.
- ADDED 2026-06-19: FAQPage auto-generated per blog post (from post.faqs) in content.py template.
- ADDED 2026-06-19: favicon.svg (branded green+gold "D") on all pages.
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
J. Service schema per treatment page — DONE (MedicalTherapy + MedicalWebPage + FAQPage on all 5 service pages, 2026-06-19).

## DEPLOYMENT RULES (MANDATORY — NO EXCEPTIONS)
- BEFORE pushing to main or Oracle: test the full affected flow end-to-end. For bot changes: verify token auth (curl 200), dry-run git push, restart service and confirm `active (running)`. For site changes: run check_post.py on representative posts. Never deploy untested code.
- Oracle SSH key = /Users/naash/Documents/Projects/Personal-2/Orcale/ssh-key-2026-05-25 (1).key  host = ubuntu@140.245.230.251
- ALWAYS confirm with user before any push to main or any Oracle operation. Ask explicitly and wait for "yes".

## RULES / GOTCHAS
- SEO = FIRST objective. every change must not hurt crawlability or page speed.
- NO medical overclaims. no "cure", "guaranteed", "no side effects". YMYL health rules.
- NEVER name specific homeopathic remedies (Belladonna, Pulsatilla, etc.) in blog prose —
  looks like prescribing = YMYL/regulatory risk. check_post.py enforces this. Say
  "an individually selected remedy" instead.
- keep frames ~180, 1600px, q88. more/bigger = slow = bad SEO.
- continuous-motion clips only (no hard cuts — ugly scrubbed backward).
- v2 redesign = APPROVED and merged. it IS the live version now. no v2 files anymore.
- headless screenshot tool sometimes blanks sticky-canvas — verify via DOM/pixel sample + real browser.
