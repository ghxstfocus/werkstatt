// Workbench-Drawer (OP-233): collapsible, 5 Tabs
(function () {
  "use strict";
  var aktuellesProjekt = "werkstatt";

  function _el(id) { return document.getElementById(id); }

  function _setDrawer(offen) {
    var d = _el("workbench-drawer");
    if (!d) return;
    d.dataset.offen = offen ? "true" : "false";
    try { localStorage.setItem("werkstatt-workbench", offen ? "1" : "0"); } catch (e) {}
    if (offen && !d.dataset.initialisiert) {
      // Initial: Audit als Default, aber OHNE _aktiviereTab zu rufen
      // (das wuerde _setDrawer(true) erneut aufrufen → Rekursion).
      d.querySelectorAll(".wb-tab").forEach(function (b) {
        b.classList.toggle("aktiv", b.dataset.tab === "audit");
      });
      d.querySelectorAll(".wb-pane").forEach(function (p) {
        p.classList.toggle("aktiv", p.dataset.pane === "audit");
      });
      d.dataset.initialisiert = "1";
    }
  }

  function _ladeDiff() {
    var stat = document.getElementById("diff-stat");
    var inh = document.getElementById("diff-inhalt");
    if (!stat || !inh) return;
    fetch("/api/projects/" + encodeURIComponent(aktuellesProjekt) + "/diff",
          {credentials: "same-origin"})
      .then(function (r) { return r.ok ? r.json() : {}; })
      .then(function (d) {
        stat.textContent = d.stat || "(kein Diff)";
        inh.textContent = d.diff || "";
      }).catch(function () {});
  }

  function _ladeVerify() {
    var box = document.getElementById("verify-inhalt");
    if (!box) return;
    fetch("/api/projects/" + encodeURIComponent(aktuellesProjekt) + "/verify",
          {credentials: "same-origin"})
      .then(function (r) { return r.ok ? r.json() : {events: []}; })
      .then(function (d) {
        box.innerHTML = "";
        if (!d.events || d.events.length === 0) {
          box.textContent = "(keine verify-Events)";
          return;
        }
        d.events.slice(-50).forEach(function (ev) {
          var div = document.createElement("div");
          div.className = "wb-verify-zeile";
          div.textContent = (ev.ts || "") + "  " + (ev.kind || "") + (ev.result ? " - " + ev.result : "");
          box.appendChild(div);
        });
      }).catch(function () {});
  }

  function _ladeFiles(pfad) {
    var box = document.getElementById("files-inhalt");
    var lbl = document.getElementById("files-pfad");
    if (!box) return;
    pfad = pfad || "";
    fetch("/api/projects/" + encodeURIComponent(aktuellesProjekt) +
          "/files?pfad=" + encodeURIComponent(pfad),
          {credentials: "same-origin"})
      .then(function (r) { return r.ok ? r.json() : {}; })
      .then(function (d) {
        box.innerHTML = "";
        if (lbl) lbl.textContent = pfad || "Dateien";
        if (d.typ === "file") {
          var pre = document.createElement("pre");
          pre.className = "wb-pre";
          pre.textContent = d.inhalt || "";
          box.appendChild(pre);
          return;
        }
        if (pfad) {
          var up = document.createElement("div");
          up.className = "wb-file wb-file-up";
          up.textContent = "..";
          up.addEventListener("click", function () {
            var t = pfad.split("/").filter(Boolean); t.pop();
            _ladeFiles(t.join("/"));
          });
          box.appendChild(up);
        }
        (d.eintraege || []).forEach(function (e) {
          var div = document.createElement("div");
          div.className = "wb-file";
          div.dataset.typ = e.typ;
          div.textContent = (e.typ === "dir" ? "D " : "F ") + e.name;
          div.addEventListener("click", function () {
            _ladeFiles(pfad ? pfad + "/" + e.name : e.name);
          });
          box.appendChild(div);
        });
      }).catch(function () {});
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
    // Drawer oeffnen nur wenn noch zu — kein Rekursions-Aufruf
    if (d.dataset.offen !== "true") {
      _setDrawer(true);
    }
    if (name === "diff") _ladeDiff();
    else if (name === "verify") _ladeVerify();
    else if (name === "files") _ladeFiles("");
  }

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".wb-refresh").forEach(function (b) {
      b.addEventListener("click", function () {
        var pane = b.dataset.paneRefresh;
        if (pane === "diff") _ladeDiff();
        else if (pane === "verify") _ladeVerify();
        else if (pane === "files") _ladeFiles("");
      });
    });

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

  window.WerkstattWorkbench = {
    oeffne: _aktiviereTab,
    schliesse: function () { _setDrawer(false); },
    setProjekt: function (p) { if (p) aktuellesProjekt = p; }
  };
})();
