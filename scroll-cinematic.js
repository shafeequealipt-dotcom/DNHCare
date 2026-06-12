/* ============================================================
   v2 engine — scroll scrub with SEO-grade loading:
   - paints frame 1 immediately (poster), defers the other 179
   - full sequence loads only when the section nears the viewport
     (or shortly after window load, whichever comes first)
   - scrubbing falls back to the nearest loaded frame mid-load
   - top scroll progress bar, prefers-reduced-motion support
   ============================================================ */
function initScrub(cfg) {
  const section = document.querySelector(cfg.section);
  const canvas  = section.querySelector("canvas");
  const ctx     = canvas.getContext("2d", { alpha: false });
  const lines   = [...section.querySelectorAll(".reveal-line")];
  const bgFill  = cfg.bg || "#0a0a12";
  const images  = new Array(cfg.frameCount);
  let firstDrawn = false;
  let sequenceStarted = false;
  let current = -1;

  function ready(i) {
    const im = images[i];
    return im && im.complete && im.naturalWidth;
  }
  function loadFrame(i, priority) {
    if (images[i]) return;
    const img = new Image();
    if (priority) img.fetchPriority = "high";
    img.src = cfg.framePath(i + 1);
    img.onload = () => {
      if (!firstDrawn && i === 0) { firstDrawn = true; draw(0); }
      else if (i === current) draw(i);
    };
    images[i] = img;
  }
  loadFrame(0, true);                       // poster frame: instant LCP

  function startSequence() {
    if (sequenceStarted) return;
    sequenceStarted = true;
    let i = 1;
    (function batch() {                     // gentle 12-frame batches
      const end = Math.min(i + 12, cfg.frameCount);
      for (; i < end; i++) loadFrame(i);
      if (i < cfg.frameCount) setTimeout(batch, 80);
    })();
  }
  const io = new IntersectionObserver((entries) => {
    if (entries.some(e => e.isIntersecting)) { startSequence(); io.disconnect(); }
  }, { rootMargin: "150% 0px" });
  io.observe(section);
  window.addEventListener("load", () => setTimeout(startSequence, 2500), { once: true });

  function draw(index) {
    const img = images[index];
    if (!img || !img.complete || !img.naturalWidth) return;
    const cw = canvas.clientWidth, ch = canvas.clientHeight;
    const ir = img.naturalWidth / img.naturalHeight, cr = cw / ch;
    let dw, dh, dx, dy;
    if (ir > cr) { dh = ch; dw = ch * ir; dx = (cw - dw) / 2; dy = 0; }
    else         { dw = cw; dh = cw / ir; dx = 0; dy = (ch - dh) / 2; }
    ctx.fillStyle = bgFill; ctx.fillRect(0, 0, cw, ch);
    ctx.drawImage(img, dx, dy, dw, dh);
  }
  function resize() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width  = canvas.clientWidth  * dpr;
    canvas.height = canvas.clientHeight * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    draw(current < 0 ? 0 : current);
  }
  function update() {
    const rect = section.getBoundingClientRect();
    if (rect.bottom < -window.innerHeight || rect.top > window.innerHeight) return;
    const scrollable = rect.height - window.innerHeight;
    const p = Math.min(Math.max(-rect.top / scrollable, 0), 1);
    let idx = Math.min(cfg.frameCount - 1, Math.floor(p * (cfg.frameCount - 1)));
    while (idx > 0 && !ready(idx)) idx--;   // nearest loaded frame mid-load
    if (idx !== current) { current = idx; draw(idx); }
    for (const el of lines) {
      const a = parseFloat(el.dataset.in), b = parseFloat(el.dataset.out);
      const mid = (a + b) / 2, half = (b - a) / 2;
      let o = 1 - Math.abs(p - mid) / half;
      o = Math.max(0, Math.min(1, o));
      el.style.opacity = o.toFixed(3);
      const base = el.dataset.tf || "translate(-50%, -50%)";
      el.style.transform = `${base} translateY(${(1 - o) * 30}px)`;
    }
  }
  window.addEventListener("resize", resize);
  resize();
  return { update, resize };
}

function animateCount(el) {
  const target = parseFloat(el.dataset.count), suffix = el.dataset.suffix || "";
  const dur = 1500, t0 = performance.now();
  function step(t) {
    const k = Math.min((t - t0) / dur, 1), eased = 1 - Math.pow(1 - k, 3);
    el.textContent = (target % 1 === 0 ? Math.round(target*eased) : (target*eased).toFixed(1)) + suffix;
    if (k < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

document.addEventListener("DOMContentLoaded", () => {
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const scrubs = (window.SCRUB_SECTIONS || [])
    .filter(c => document.querySelector(c.section))
    .map(initScrub);

  const lenis = new Lenis({ lerp: reduceMotion ? 1 : 0.085, smoothWheel: !reduceMotion });
  window.__lenis = lenis;
  const progress = document.querySelector(".scroll-progress b");
  function raf(t) {
    lenis.raf(t);
    scrubs.forEach(s => s.update());
    if (progress) {
      const max = document.documentElement.scrollHeight - window.innerHeight;
      progress.style.width = (max > 0 ? (window.scrollY / max) * 100 : 0) + "%";
    }
    requestAnimationFrame(raf);
  }
  requestAnimationFrame(raf);

  const io = new IntersectionObserver((entries) => {
    entries.forEach((e) => {
      if (!e.isIntersecting) return;
      e.target.classList.add("in");
      if (e.target.classList.contains("stat-num")) animateCount(e.target);
      io.unobserve(e.target);
    });
  }, { threshold: 0.25 });
  document.querySelectorAll(".reveal, .stat-num").forEach((el) => io.observe(el));

  lenis.on("scroll", ({ scroll }) => {
    document.querySelectorAll(".scroll-hint").forEach(h => h.style.opacity = scroll > 60 ? "0" : "1");
  });
});
