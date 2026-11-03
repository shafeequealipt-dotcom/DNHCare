const bar = document.querySelector(".scroll-progress b");
const article = document.querySelector(".article");
const nav = document.querySelector(".nav");
function onScroll() {
  nav.classList.toggle("solid", scrollY > 40);
  const r = article.getBoundingClientRect();
  const p = Math.min(Math.max(-r.top / Math.max(r.height - innerHeight, 1), 0), 1);
  bar.style.transform = `scaleX(${p})`;
}
addEventListener("scroll", onScroll, { passive: true });
onScroll();

const burger = document.querySelector(".burger");
function toggleMenu(open) {
  document.documentElement.classList.toggle("menu-open", open);
  document.body.classList.toggle("locked", open);
  burger.setAttribute("aria-expanded", String(open));
}
burger.addEventListener("click", () => toggleMenu(!document.documentElement.classList.contains("menu-open")));
addEventListener("keydown", (e) => { if (e.key === "Escape") toggleMenu(false); });
