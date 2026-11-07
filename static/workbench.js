// Workbench-Drawer (OP-233): collapsible, 5 Tabs
(function () {
  "use strict";

  function _el(id) { return document.getElementById(id); }

  function _setDrawer(offen) {
    var d = _el("workbench-drawer");
    if (!d) return;
    d.dataset.offen = offen ? "true" : "false";
    try { localStorage.setItem("werkstatt-workbench", offen ? "1" : "0"); } catch (e) {}
    if (offen && !d.dataset.initialisiert) {
      _aktiviereTab("audit");
      d.dataset.initialisiert = "1";
    }
  }

  function _aktiviereTab(name) {
    var d = _el("workbench-drawer");
    if (!d) return;
    d.querySelectorAll(".wb-tab").forEach(function (b) {
      b.classList.toggle("aktiv", b.dataset.tab === name);
    });
    d.querySelectorAll(".wb-pane").forEach(function (p) {
      p.classList.toggle("aktiv", p.dataset.pane === name);
    });
    _setDrawer(true);
  }

  document.addEventListener("DOMContentLoaded", function () {
    var d = _el("workbench-drawer");
    if (!d) return;
    var gespeichert = "0";
    try { gespeichert = localStorage.getItem("werkstatt-workbench") || "0"; } catch (e) {}
    _setDrawer(gespeichert === "1");

    d.querySelectorAll(".wb-tab").forEach(function (b) {
      if (b.disabled) return;
      b.addEventListener("click", function () {
        _aktiviereTab(b.dataset.tab);
      });
    });

    var tog = _el("wb-toggle");
    if (tog) {
      tog.addEventListener("click", function () {
        _setDrawer(d.dataset.offen !== "true");
      });
    }
  });

  window.WerkstattWorkbench = { oeffne: _aktiviereTab, schliesse: function () { _setDrawer(false); } };
})();
