// OP-305: Utility-Bar (⌘K-Button, ?-Button) + Shift+N.
(function () {
  "use strict";

  function _el(id) { return document.getElementById(id); }

  function _oeffnePalette() {
    if (window.WerkstattPalette && window.WerkstattPalette.oeffnen) {
      window.WerkstattPalette.oeffnen();
    }
  }

  function _oeffneHelp() {
    if (window.WerkstattShortcutHelp && window.WerkstattShortcutHelp.oeffnen) {
      window.WerkstattShortcutHelp.oeffnen();
    }
  }

  function _neuesProjekt() {
    var btn = _el("tab-neu");
    if (btn) btn.click();
  }

  function _init() {
    var paletteBtn = _el("utility-palette");
    var helpBtn = _el("utility-help");
    if (paletteBtn) paletteBtn.addEventListener("click", _oeffnePalette);
    if (helpBtn) helpBtn.addEventListener("click", _oeffneHelp);

    // Shift+N: Neues Projekt (ausser in Inputs)
    document.addEventListener("keydown", function (e) {
      if (!e.shiftKey || e.ctrlKey || e.metaKey || e.altKey) return;
      if (e.key !== "N" && e.key !== "n") return;
      var a = document.activeElement;
      if (a && (a.tagName === "INPUT" || a.tagName === "TEXTAREA" || a.isContentEditable)) return;
      e.preventDefault();
      _neuesProjekt();
    });
  }

  window.WerkstattUtility = {
    palette: _oeffnePalette,
    help: _oeffneHelp,
  };

  document.addEventListener("DOMContentLoaded", _init);
})();
