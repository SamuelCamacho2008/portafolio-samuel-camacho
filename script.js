const menuToggle = document.querySelector(".menu-toggle");
const menu = document.querySelector("#menu");

if (menuToggle && menu) {
  menuToggle.addEventListener("click", () => {
    const isExpanded = menuToggle.getAttribute("aria-expanded") === "true";
    menuToggle.setAttribute("aria-expanded", String(!isExpanded));
    menuToggle.setAttribute("aria-label", isExpanded ? "Abrir menú" : "Cerrar menú");
    menu.classList.toggle("is-open", !isExpanded);
  });

  menu.querySelectorAll("a").forEach((link) => {
    link.addEventListener("click", () => {
      menuToggle.setAttribute("aria-expanded", "false");
      menuToggle.setAttribute("aria-label", "Abrir menú");
      menu.classList.remove("is-open");
    });
  });
}

const year = document.querySelector("#current-year");
if (year) year.textContent = new Date().getFullYear();
