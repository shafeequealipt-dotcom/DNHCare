const PAGE = 12;
const cards = [...document.querySelectorAll(".j-card")];
const chips = [...document.querySelectorAll(".j-filter button")];
const more = document.getElementById("more");
let cat = "all", shown = PAGE;

function render() {
  const match = cards.filter((c) => cat === "all" || c.dataset.cat === cat);
  cards.forEach((c) => { c.hidden = true; });
  match.slice(0, shown).forEach((c) => { c.hidden = false; });
  more.hidden = shown >= match.length;
}
chips.forEach((b) => b.addEventListener("click", () => {
  chips.forEach((o) => o.classList.toggle("on", o === b));
  cat = b.dataset.cat;
  shown = PAGE;
  render();
}));
more.addEventListener("click", () => { shown += PAGE; render(); });
render();

const burger = document.querySelector(".burger");
function toggleMenu(open) {
  document.documentElement.classList.toggle("menu-open", open);
  document.body.classList.toggle("locked", open);
  burger.setAttribute("aria-expanded", String(open));
}
burger.addEventListener("click", () => toggleMenu(!document.documentElement.classList.contains("menu-open")));
addEventListener("keydown", (e) => { if (e.key === "Escape") toggleMenu(false); });
addEventListener("scroll", () => document.querySelector(".nav").classList.toggle("solid", scrollY > 40), { passive: true });
