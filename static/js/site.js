// Kashvo site: mobile menu, copy-link, and restrained GSAP motion.
(() => {
  const burger = document.querySelector(".burger");
  const nav = document.getElementById("nav");
  burger?.addEventListener("click", () => burger.setAttribute("aria-expanded", nav.classList.toggle("open")));

  document.querySelectorAll("[data-copy]").forEach((b) => b.addEventListener("click", () => navigator.clipboard?.writeText(b.dataset.copy)));

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
