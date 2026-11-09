// OP-306a: UI-Modi (cockpit / control / debug).
// ADR-0022. Persistiert in localStorage + URL-Parameter.
(function () {
  "use strict";

  var MODI = ["cockpit", "control", "debug"];
  var KEY = "werkstatt-mode";
  var DEFAULT = "cockpit";

  function _istModus(m) {
    return MODI.indexOf(m) !== -1;
  }

  function _ausUrl() {
    try {
      var p = new URLSearchParams(window.location.search);
      var m = (p.get("mode") || "").toLowerCase();
      return _istModus(m) ? m : null;
    } catch (e) { return null; }
  }

  function _ausStorage() {
    try {
      var m = (localStorage.getItem(KEY) || "").toLowerCase();
      return _istModus(m) ? m : null;
    } catch (e) { return null; }
  }

  function _setzeUrl(m) {
    try {
      var url = new URL(window.location.href);
      if (m === DEFAULT) {
        url.searchParams.delete("mode");
      } else {
        url.searchParams.set("mode", m);
      }
      // replaceState: kein History-Eintrag pro Mode-Wechsel
      window.history.replaceState({}, "", url.toString());
    } catch (e) {}
  }

  function getMode() {
    var m = _ausUrl();
    if (m) return m;
    m = _ausStorage();
    if (m) return m;
    return DEFAULT;
  }

  function _apply(m) {
    if (!_istModus(m)) m = DEFAULT;
    var body = document.body;
    if (body) body.setAttribute("data-mode", m);
    try { localStorage.setItem(KEY, m); } catch (e) {}
    _setzeUrl(m);
    // Dropdown-Buttons markieren
    var btns = document.querySelectorAll("[data-mode-btn]");
    for (var i = 0; i < btns.length; i++) {
      var b = btns[i];
      if (b.getAttribute("data-mode-btn") === m) {
        b.classList.add("aktiv");
        b.setAttribute("aria-pressed", "true");
      } else {
        b.classList.remove("aktiv");
        b.setAttribute("aria-pressed", "false");
      }
    }
    // Event fuer andere Module (spaeter: waterfall.js, palette.js)
    try {
      document.dispatchEvent(new CustomEvent("werkstatt:mode-change", {
        detail: {mode: m}
      }));
    } catch (e) {}
  }

  function setMode(m) {
    if (!_istModus(m)) return;
    _apply(m);
  }

  function cycle() {
    var jetzt = getMode();
    var idx = MODI.indexOf(jetzt);
    if (idx === -1) idx = 0;
    var naechster = MODI[(idx + 1) % MODI.length];
    _apply(naechster);
  }

  // Initial-Apply
  _apply(getMode());

  // Tastatur: Shift+Space zyklisch, 1/2/3 direkt
  document.addEventListener("keydown", function (e) {
    // Nur wenn kein Input/Textarea fokussiert
    var tag = (document.activeElement && document.activeElement.tagName) || "";
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;

    if (e.shiftKey && e.code === "Space") {
      e.preventDefault();
      cycle();
      return;
    }
    if (!e.shiftKey && !e.ctrlKey && !e.metaKey && !e.altKey) {
      if (e.key === "1") { e.preventDefault(); _apply("cockpit"); return; }
      if (e.key === "2") { e.preventDefault(); _apply("control"); return; }
      if (e.key === "3") { e.preventDefault(); _apply("debug"); return; }
    }
  });

  // Dropdown-Buttons (werden im HTML gerendert)
  document.addEventListener("DOMContentLoaded", function () {
    var btns = document.querySelectorAll("[data-mode-btn]");
    for (var i = 0; i < btns.length; i++) {
      (function (b) {
        b.addEventListener("click", function () {
          _apply(b.getAttribute("data-mode-btn"));
        });
      })(btns[i]);
    }
    // Nochmal apply, damit Dropdown-Markierung passt
    _apply(getMode());
  });

  // Public API fuer Command Palette / andere Module
  window.WerkstattMode = {
    getMode: getMode,
    setMode: setMode,
    cycle: cycle,
    MODI: MODI.slice()
  };
})();
