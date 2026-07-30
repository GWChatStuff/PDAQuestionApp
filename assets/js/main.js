(() => {
  const header = document.querySelector(".site-header");
  const toggle = document.querySelector(".nav-toggle");
  const nav = document.querySelector("#site-nav");
  const pageAreas = [document.querySelector("main"), document.querySelector(".site-footer")].filter(Boolean);
  let restoreFocus = null;

  const focusables = () => nav ? [...nav.querySelectorAll('a[href],button:not([disabled]),[tabindex]:not([tabindex="-1"])')] : [];
  const setPageInert = (state) => pageAreas.forEach((area) => {
    if (state) { area.setAttribute("inert", ""); area.setAttribute("aria-hidden", "true"); }
    else { area.removeAttribute("inert"); area.removeAttribute("aria-hidden"); }
  });
  const setMenu = (open, returnFocus = true) => {
    if (!toggle || !nav) return;
    toggle.setAttribute("aria-expanded", String(open));
    toggle.setAttribute("aria-label", open ? "Close menu" : "Open menu");
    nav.classList.toggle("open", open);
    document.body.classList.toggle("menu-open", open);
    setPageInert(open);
    if (open) { restoreFocus = document.activeElement; window.requestAnimationFrame(() => focusables()[0]?.focus()); }
    else if (returnFocus) { toggle.focus(); restoreFocus = null; }
  };
  toggle?.addEventListener("click", () => setMenu(toggle.getAttribute("aria-expanded") !== "true"));
  nav?.addEventListener("click", (event) => { if (event.target.closest("a")) setMenu(false, false); });
  document.addEventListener("keydown", (event) => {
    const open = toggle?.getAttribute("aria-expanded") === "true";
    if (!open) return;
    if (event.key === "Escape") { event.preventDefault(); setMenu(false); return; }
    if (event.key !== "Tab") return;
    const items = focusables(); const first = items[0]; const last = items[items.length - 1];
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
  });
  const desktop = window.matchMedia("(min-width: 981px)");
  desktop.addEventListener?.("change", (event) => { if (event.matches) setMenu(false, false); });

  const updateHeader = () => header?.classList.toggle("scrolled", window.scrollY > 8);
  updateHeader(); window.addEventListener("scroll", updateHeader, { passive: true });

  const excluded = ["download.html", "privacy.html", "terms.html", "terms-california.html"];
  const page = location.pathname.split("/").pop() || "index.html";
  if (!excluded.includes(page) && sessionStorage.getItem("pda-sticky-dismissed") !== "1") {
    const bar = document.createElement("aside");
    bar.className = "sticky-download"; bar.setAttribute("aria-label", "Download PDA Question");
    bar.innerHTML = '<div class="container sticky-inner"><div class="sticky-copy"><strong>Support for hard moments</strong><small>PDA Question · $0.99 per month</small></div><a class="btn" href="download.html">View on App Store</a><button class="sticky-close" type="button" aria-label="Dismiss download reminder">×</button></div>';
    document.body.appendChild(bar);
    let ready = false; let shown = false;
    const updateSticky = () => {
      if (!ready || shown || window.scrollY < 480) return;
      shown = true; bar.classList.add("visible"); document.body.classList.add("sticky-visible");
    };
    window.setTimeout(() => { ready = true; updateSticky(); }, 2200);
    window.addEventListener("scroll", updateSticky, { passive: true });
    bar.querySelector(".sticky-close")?.addEventListener("click", () => {
      sessionStorage.setItem("pda-sticky-dismissed", "1"); bar.classList.remove("visible"); document.body.classList.remove("sticky-visible");
      window.setTimeout(() => bar.remove(), 320);
    });
  }
})();
