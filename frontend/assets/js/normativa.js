(function initializeNormativeIndex(ownerDocument) {
  "use strict";

  if (!ownerDocument) return;

  const links = Array.from(ownerDocument.querySelectorAll('.normative-index a[href^="#"]'));
  const sections = Array.from(ownerDocument.querySelectorAll("[data-normative-section]"));
  const mobileIndex = ownerDocument.querySelector("[data-normative-mobile-index]");

  function selectSection(id) {
    links.forEach((link) => {
      const current = link.getAttribute("href") === `#${id}`;
      link.classList.toggle("is-current", current);
      if (current) link.setAttribute("aria-current", "location");
      else link.removeAttribute("aria-current");
    });
  }

  links.forEach((link) => link.addEventListener("click", () => {
    if (mobileIndex) mobileIndex.open = false;
  }));

  if ("IntersectionObserver" in globalThis && sections.length) {
    const observer = new IntersectionObserver((entries) => {
      const visible = entries.filter((entry) => entry.isIntersecting)
        .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
      if (visible) selectSection(visible.target.id);
    }, { rootMargin: "-18% 0px -65%", threshold: [0, 0.1, 0.5] });
    sections.forEach((section) => observer.observe(section));
  }

  if (sections[0]) selectSection(sections[0].id);
})(typeof document === "undefined" ? null : document);
