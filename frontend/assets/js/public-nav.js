(function attachPublicNav(globalScope) {
  "use strict";

  function setupPublicNav(nav, ownerDocument) {
    if (!nav || !ownerDocument) {
      return null;
    }

    const groups = Array.from(nav.querySelectorAll("[data-nav-group]"));

    function setGroupOpen(group, shouldOpen, options = {}) {
      const trigger = group?.querySelector("[data-nav-trigger]");
      const menu = group?.querySelector("[data-nav-menu]");
      if (!trigger || !menu) {
        return;
      }

      group.classList.toggle("is-open", shouldOpen);
      trigger.setAttribute("aria-expanded", shouldOpen ? "true" : "false");
      menu.hidden = !shouldOpen;

      if (shouldOpen && options.focusEdge) {
        const links = Array.from(menu.querySelectorAll("a[href]"));
        const target = options.focusEdge === "last" ? links.at(-1) : links[0];
        target?.focus();
      }
    }

    function closeAll(exceptGroup = null) {
      groups.forEach((group) => {
        if (group !== exceptGroup) {
          setGroupOpen(group, false);
        }
      });
    }

    groups.forEach((group) => {
      const trigger = group.querySelector("[data-nav-trigger]");
      const menu = group.querySelector("[data-nav-menu]");
      if (!trigger || !menu) {
        return;
      }

      trigger.addEventListener("click", () => {
        const shouldOpen = trigger.getAttribute("aria-expanded") !== "true";
        closeAll(group);
        setGroupOpen(group, shouldOpen);
      });

      trigger.addEventListener("keydown", (event) => {
        if (event.key !== "ArrowDown" && event.key !== "ArrowUp") {
          return;
        }
        event.preventDefault();
        closeAll(group);
        setGroupOpen(group, true, {
          focusEdge: event.key === "ArrowUp" ? "last" : "first",
        });
      });
    });

    nav.addEventListener("keydown", (event) => {
      if (event.key !== "Escape") {
        return;
      }
      const openGroup = groups.find((group) => group.classList.contains("is-open"));
      if (!openGroup) {
        return;
      }
      event.preventDefault();
      setGroupOpen(openGroup, false);
      openGroup.querySelector("[data-nav-trigger]")?.focus();
    });

    ownerDocument.addEventListener("click", (event) => {
      if (!nav.contains(event.target)) {
        closeAll();
      }
    });

    return { closeAll, groups, setGroupOpen };
  }

  function initializePublicNav(ownerDocument) {
    if (!ownerDocument) {
      return [];
    }
    return Array.from(ownerDocument.querySelectorAll("[data-public-nav]"))
      .map((nav) => setupPublicNav(nav, ownerDocument))
      .filter(Boolean);
  }

  const api = { initializePublicNav, setupPublicNav };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }

  globalScope.PublicNav = api;

  if (typeof document !== "undefined") {
    document.addEventListener("DOMContentLoaded", () => {
      initializePublicNav(document);
    });
  }
})(typeof globalThis !== "undefined" ? globalThis : this);
