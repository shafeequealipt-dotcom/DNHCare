const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const calm = matchMedia("(prefers-reduced-motion: reduce)").matches;

/* ---------- Hero words light up in turn ---------- */
const words = $$(".hero-words li");
if (words.length) {
  let w = 0;
  words[0].classList.add("lit");
  if (!calm) setInterval(() => {
    words[w].classList.remove("lit");
    w = (w + 1) % words.length;
    words[w].classList.add("lit");
  }, 2200);
}

/* ---------- Menu ---------- */
const burger = $(".burger");
function toggleMenu(open) {
  document.documentElement.classList.toggle("menu-open", open);
  document.body.classList.toggle("locked", open);
  burger.setAttribute("aria-expanded", String(open));
}
burger.addEventListener("click", () => toggleMenu(!document.documentElement.classList.contains("menu-open")));
$$(".menu a").forEach((a) => a.addEventListener("click", () => toggleMenu(false)));
addEventListener("keydown", (e) => { if (e.key === "Escape") { toggleMenu(false); closeFilm(); } });

/* ---------- Scroll reveals ---------- */
const seen = new IntersectionObserver((entries) => {
  entries.forEach((e) => {
    if (e.isIntersecting) { e.target.classList.add("in"); seen.unobserve(e.target); }
  });
}, { threshold: 0.14, rootMargin: "0px 0px -6% 0px" });
$$(".reveal, .care-card, .stage").forEach((el) => seen.observe(el));

/* ---------- Script line writes itself in as it scrolls past ---------- */
const script = $(".script");
const nav = $(".nav");
const tabsBar = $(".tabs");
function onScroll() {
  nav.classList.toggle("solid", scrollY > innerHeight * 0.7);
  if (script && !calm) {
    const r = script.getBoundingClientRect();
    const t = Math.min(Math.max((innerHeight * 0.95 - r.top) / (innerHeight * 0.3), 0), 1);
    script.style.setProperty("--w", `${t * 100}%`);
  }
}
addEventListener("scroll", onScroll, { passive: true });
onScroll();

/* ---------- Sticky tabs ---------- */
const tabButtons = $$(".tabs button");
const cares = $$(".care");
tabButtons.forEach((b) => b.addEventListener("click", () => $(`#${b.dataset.to}`).scrollIntoView({ behavior: calm ? "auto" : "smooth" })));
function setTab(id) {
  tabButtons.forEach((b) => {
    const on = b.dataset.to === id;
    b.classList.toggle("on", on);
    if (on && tabsBar.scrollWidth > innerWidth) b.parentElement.scrollTo({ left: b.offsetLeft - 40, behavior: "smooth" });
  });
}
const spy = new IntersectionObserver((entries) => {
  entries.forEach((e) => { if (e.isIntersecting) setTab(e.target.id); });
}, { rootMargin: "-45% 0px -50% 0px" });
cares.forEach((c) => spy.observe(c));

/* ---------- Card thumbnails swap the card's image and copy ---------- */
cares.forEach((care) => {
  const copy = $(".care-copy", care);
  const type = $(".care-type", care);
  $$(".thumb", care).forEach((t) => {
    t.addEventListener("click", () => {
      $$(".thumb", care).forEach((o) => { o.classList.remove("on"); o.setAttribute("aria-pressed", "false"); });
      t.classList.add("on");
      t.setAttribute("aria-pressed", "true");
      copy.classList.add("fade");
      type.classList.add("fade");
      setTimeout(() => {
        copy.textContent = t.dataset.copy;
        type.textContent = t.textContent;
        copy.classList.remove("fade");
        type.classList.remove("fade");
      }, 260);
    });
  });
});

/* ---------- Counters ---------- */
const counter = new IntersectionObserver((entries) => {
  entries.forEach((e) => {
    if (!e.isIntersecting) return;
    counter.unobserve(e.target);
    const el = e.target, end = +el.dataset.count, dec = el.dataset.count.includes(".") ? 1 : 0, suf = el.dataset.suffix || "";
    const fmt = (v) => v.toLocaleString("en-IN", { minimumFractionDigits: dec, maximumFractionDigits: dec }) + suf;
    if (calm) { el.textContent = fmt(end); return; }
    const t0 = performance.now();
    (function step(now) {
      const p = Math.min((now - t0) / 1600, 1);
      el.textContent = fmt(end * (1 - Math.pow(1 - p, 3)));
      if (p < 1) requestAnimationFrame(step);
    })(t0);
  });
}, { threshold: 0.6 });
$$("[data-count]").forEach((el) => counter.observe(el));

/* ---------- Metal card tilt ---------- */
const metal = $(".metal");
if (metal && !calm) {
  metal.parentElement.addEventListener("pointermove", (e) => {
    const r = metal.getBoundingClientRect();
    const x = (e.clientX - r.left) / r.width - 0.5, y = (e.clientY - r.top) / r.height - 0.5;
    metal.style.transform = `rotateY(${x * 14}deg) rotateX(${-y * 12}deg)`;
    metal.style.setProperty("--sheen", `${x * 60}%`);
  });
  metal.parentElement.addEventListener("pointerleave", () => { metal.style.transform = ""; metal.style.setProperty("--sheen", "-22%"); });
}

/* ---------- The film: the clinic's words, one line at a time ---------- */
const LINES = [
  "Medicine that listens before it prescribes.",
  "Every consultation begins with your whole story.",
  "Sleep. Stress. Appetite. History. Temperament.",
  "Then a remedy, chosen individually for you.",
  "Healing, the gentle way.",
];
const film = $(".film");
let filmTimer = 0;
const filmBar = $(".film-bar");
function playLine(i) {
  const cap = $(".film-caption", film);
  cap.textContent = LINES[i];
  cap.animate([{ opacity: 0, transform: "translateY(12px)" }, { opacity: 1, transform: "none" }], { duration: 1100, fill: "both", easing: "cubic-bezier(.2,.7,.2,1)" });
  filmBar.animate([{ transform: `scaleX(${i / LINES.length})` }, { transform: `scaleX(${(i + 1) / LINES.length})` }], { duration: 4200, fill: "forwards" });
  filmTimer = setTimeout(() => (i + 1 < LINES.length ? playLine(i + 1) : closeFilm()), 4200);
}
function openFilm() {
  film.classList.add("open");
  film.setAttribute("aria-hidden", "false");
  document.body.classList.add("locked");
  $(".film-close").focus();
  playLine(0);
}
function closeFilm() {
  clearTimeout(filmTimer);
  if (!film.classList.contains("open")) return;
  film.classList.remove("open");
  film.setAttribute("aria-hidden", "true");
  document.body.classList.remove("locked");
  $(".film-thumb").focus();
}
$(".film-thumb").addEventListener("click", openFilm);
$(".film-close").addEventListener("click", closeFilm);
