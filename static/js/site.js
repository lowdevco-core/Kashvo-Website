// Kashvo site: mobile menu, copy-link, and restrained GSAP motion.
(() => {
  const burger = document.querySelector(".burger");
  const nav = document.getElementById("nav");
  burger?.addEventListener("click", () => burger.setAttribute("aria-expanded", nav.classList.toggle("open")));

  document.querySelectorAll("[data-copy]").forEach((b) => b.addEventListener("click", () => navigator.clipboard?.writeText(b.dataset.copy)));

  const pwaDialog = document.getElementById("pwa-dialog");
  const isMobileOrTablet = () => {
    if (navigator.userAgentData?.mobile) return true;
    const ua = navigator.userAgent || "";
    return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(ua)
      || (ua.includes("Macintosh") && navigator.maxTouchPoints > 1);
  };
  const isAppleTouch = () => {
    const ua = navigator.userAgent || "";
    return /iPhone|iPad|iPod/i.test(ua) || (ua.includes("Macintosh") && navigator.maxTouchPoints > 1);
  };
  if (pwaDialog?.showModal) {
    document.querySelectorAll("[data-download-app]").forEach((link) => {
      link.addEventListener("click", (e) => {
        if (!isMobileOrTablet()) return;
        e.preventDefault();
        nav?.classList.remove("open");
        burger?.setAttribute("aria-expanded", "false");
        const apple = isAppleTouch();
        pwaDialog.querySelector('[data-pwa-steps="ios"]')?.toggleAttribute("hidden", !apple);
        pwaDialog.querySelector('[data-pwa-steps="android"]')?.toggleAttribute("hidden", apple);
        pwaDialog.showModal();
      });
    });
  }
  pwaDialog?.querySelector("[data-pwa-close]")?.addEventListener("click", () => pwaDialog.close());
  if (pwaDialog) pwaDialog.addEventListener("click", (e) => { if (e.target === pwaDialog) pwaDialog.close(); });

  // Home page: interactive POS counter preview
  const pos = document.querySelector("[data-pos-demo]");
  if (pos) {
    const itemsEl = pos.querySelector("[data-pos-items]");
    const totalEl = pos.querySelector("[data-pos-total]");
    const statusEl = pos.querySelector("[data-pos-status]");
    const barcodeEl = pos.querySelector("[data-pos-barcode]");
    const catalog = [
      { name: "Basmati rice 5 kg", price: 590, code: "8901491101837" },
      { name: "Filter coffee 200 g", price: 215, code: "8901058851229" },
      { name: "Whole wheat atta 5 kg", price: 285, code: "8901725121105" },
    ];
    let idx = 0;
    let total = 619;
    const payLabels = {
      cash: "Cash drawer ready · tender ₹1,000 -> change ₹",
      upi: "UPI QR ready · waiting for confirmation",
      bank: "Card / Bank transfer · instant settlement",
    };
    let mode = "upi";
    const renderStatus = () => {
      if (mode === "cash") {
        const change = Math.max(0, 1000 - total);
        statusEl.textContent = `Cash drawer · Tender ₹1,000 -> Change ₹${change.toFixed(2)}`;
      } else {
        statusEl.textContent = payLabels[mode];
      }
    };
    pos.querySelectorAll("[data-pos-pay]").forEach((b) => b.addEventListener("click", () => {
      mode = b.dataset.posPay;
      pos.querySelectorAll("[data-pos-pay]").forEach((x) => x.classList.toggle("on", x === b));
      renderStatus();
    }));
    pos.querySelector("[data-pos-add]")?.addEventListener("click", () => {
      const item = catalog[idx % catalog.length];
      idx += 1;
      const row = document.createElement("div");
      row.className = "panel__row panel__row--new";
      row.innerHTML = `<span>${item.name}</span><span>₹${item.price.toFixed(2)}</span>`;
      itemsEl.appendChild(row);
      if (itemsEl.children.length > 4) itemsEl.firstElementChild.remove();
      total += item.price;
      totalEl.textContent = `₹${total.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
      barcodeEl.textContent = item.code;
      renderStatus();
    });
  }

  const gsap = window.gsap;
  if (!gsap || matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  gsap.registerPlugin(window.ScrollTrigger);
  gsap.config({ nullTargetWarn: false }); // one script serves every page; missing targets are expected
  document.documentElement.classList.add("js");

  const ease = "power3.out";
  gsap.timeline({ defaults: { ease } })
    .from(".hero .eyebrow, .phero .eyebrow", { y: 12, opacity: 0, duration: .5 })
    .from(".hero h1 .line > span", { yPercent: 105, duration: .8, stagger: .08 }, "-=.25")
    .from(".phero h1, .article-head h1", { y: 24, opacity: 0, duration: .6 }, "<")
    .from(".hero .lead, .phero .lead, .hero__actions, .hero .ticks", { y: 16, opacity: 0, duration: .6, stagger: .07 }, "-=.45")
    .from(".receipt", { y: 40, opacity: 0, rotate: 4, duration: .9 }, "-=.7");

  gsap.to(".receipt", { yPercent: -6, ease: "none", scrollTrigger: { trigger: ".hero", start: "top top", end: "bottom top", scrub: true } });

  gsap.utils.toArray(".reveal").forEach((el) =>
    gsap.to(el, { opacity: 1, y: 0, duration: .7, ease, scrollTrigger: { trigger: el, start: "top 88%", once: true } }));
  gsap.utils.toArray(".stagger").forEach((group) =>
    gsap.to(group.children, { opacity: 1, y: 0, duration: .6, stagger: .07, ease, scrollTrigger: { trigger: group, start: "top 88%", once: true } }));

  gsap.utils.toArray("[data-count]").forEach((el) => {
    const n = { v: 0 };
    gsap.to(n, { v: +el.dataset.count, duration: 1.2, ease: "power2.out", scrollTrigger: { trigger: el, start: "top 90%", once: true },
      onUpdate: () => { el.textContent = Math.round(n.v) + (el.dataset.suffix || ""); } });
  });
})();
