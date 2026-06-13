# CAVEMAN.md  —  DNH CARE SITE BRAIN

READ THIS FILE ALONE = KNOW EVERYTHING. PUSH TO GITHUB. DONE.
(plain caveman notes. short words. no fluff. trust this file.)

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
B. Blog / articles section (homeopathy topics) — biggest long-tail SEO lever. each post = new ranking page.
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
