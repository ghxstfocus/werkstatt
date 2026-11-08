// OP-304: Shortcut Help Overlay (?-Taste).
(function () {
  "use strict";
  var _offen = false;

  function _el(id) { return document.getElementById(id); }

  function _inInputFeld() {
    var a = document.activeElement;
    if (!a) return false;
    var tag = a.tagName;
    return tag === "INPUT" || tag === "TEXTAREA" || a.isContentEditable;
  }

  function _oeffnen() {
    var overlay = _el("shortcut-help-overlay");
    if (!overlay) return;
    overlay.classList.add("offen");
    _offen = true;
  }

  function _schliessen() {
    var overlay = _el("shortcut-help-overlay");
    if (!overlay) return;
    overlay.classList.remove("offen");
    _offen = false;
  }

  function _init() {
    var overlay = _el("shortcut-help-overlay");
    if (overlay) {
      overlay.addEventListener("click", function (e) {
        if (e.target === overlay) _schliessen();
      });
    }
    var closeBtn = _el("shortcut-help-close");
    if (closeBtn) closeBtn.addEventListener("click", _schliessen);

    document.addEventListener("keydown", function (e) {
      if (e.key === "?" && !e.ctrlKey && !e.metaKey && !e.altKey) {
        if (_inInputFeld()) return;
        e.preventDefault();
        if (_offen) _schliessen();
        else _oeffnen();
      } else if (_offen && e.key === "Escape") {
        e.preventDefault();
        _schliessen();
      }
    });
  }

  window.WerkstattShortcutHelp = {
    oeffnen: _oeffnen,
    schliessen: _schliessen,
  };

  document.addEventListener("DOMContentLoaded", _init);
})();
