(() => {
  const toggle = document.querySelector(".nav-toggle");
  const nav = document.querySelector("#site-nav");
  if (!toggle || !nav) return;

  const setExpanded = (isOpen) => {
    toggle.setAttribute("aria-expanded", String(isOpen));
    nav.classList.toggle("open", isOpen);
  };

  toggle.addEventListener("click", () => {
    const isOpen = toggle.getAttribute("aria-expanded") === "true";
    setExpanded(!isOpen);
  });

  // Close menu when a link is clicked (mobile)
  nav.addEventListener("click", (e) => {
    const target = e.target;
    if (target && target.matches("a")) {
      setExpanded(false);
    }
  });

  // Close on escape
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") setExpanded(false);
  });

  // Close if switching to desktop layout
  const mq = window.matchMedia("(min-width: 860px)");
  mq.addEventListener?.("change", () => setExpanded(false));
})();