(function () {
  "use strict";

  const DEFAULT_DEV_BACKEND = "http://127.0.0.1:8000";

  function isLocalHost(hostname) {
    return hostname === "localhost" || hostname === "127.0.0.1" || hostname === "::1";
  }

  function hasOwn(object, property) {
    return Object.prototype.hasOwnProperty.call(object || {}, property);
  }

  function resolveConfiguredBackendBaseUrl() {
    const explicitConfig = window.HLL_FRONTEND_CONFIG || {};
    if (hasOwn(explicitConfig, "backendBaseUrl")) {
      return String(explicitConfig.backendBaseUrl || "");
    }

    const body = document.body;
    if (body && body.dataset && hasOwn(body.dataset, "backendBaseUrl")) {
      const bodyValue = body.dataset.backendBaseUrl;
      if (bodyValue === DEFAULT_DEV_BACKEND && !isLocalHost(window.location.hostname)) {
        return "";
      }
      return String(bodyValue || "");
    }

    return isLocalHost(window.location.hostname) ? DEFAULT_DEV_BACKEND : "";
  }

  function rewriteUrl(input) {
    const configuredBaseUrl = resolveConfiguredBackendBaseUrl();
    if (typeof input !== "string") {
      return input;
    }

    if (configuredBaseUrl === "") {
      if (input.startsWith(`${DEFAULT_DEV_BACKEND}/`)) {
        return input.slice(DEFAULT_DEV_BACKEND.length);
      }
      return input;
    }

    if (input.startsWith(`${DEFAULT_DEV_BACKEND}/`)) {
      return `${configuredBaseUrl}${input.slice(DEFAULT_DEV_BACKEND.length)}`;
    }

    return input;
  }

  const nativeFetch = window.fetch.bind(window);
  window.fetch = function hllConfiguredFetch(input, init) {
    if (typeof input === "string") {
      return nativeFetch(rewriteUrl(input), init);
    }
    if (input instanceof Request) {
      const rewrittenUrl = rewriteUrl(input.url);
      if (rewrittenUrl !== input.url) {
        return nativeFetch(new Request(rewrittenUrl, input), init);
      }
    }
    return nativeFetch(input, init);
  };

  window.HLL_FRONTEND_CONFIG = Object.freeze({
    ...window.HLL_FRONTEND_CONFIG,
    backendBaseUrl: resolveConfiguredBackendBaseUrl(),
  });
})();
