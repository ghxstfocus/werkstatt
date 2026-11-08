// OP-301: Ambient Status Bar (oben). Polling /ambient alle 3s.
(function () {
  "use strict";
  var aktuellesProjekt = "werkstatt";
  var INTERVALL_MS = 3000;

  function _el(id) { return document.getElementById(id); }


  function _fmtRel(iso) {
    if (!iso) return "—";
    try {
      var d = new Date(iso);
      if (isNaN(d.getTime())) return "—";
      var sek = Math.floor((Date.now() - d.getTime()) / 1000);
      if (sek < 60) return "gerade";
      if (sek < 3600) return Math.floor(sek / 60) + "m";
      if (sek < 86400) return Math.floor(sek / 3600) + "h";
      return Math.floor(sek / 86400) + "d";
    } catch (e) { return "—"; }
  }

  function _setLoop(status) {
    var el = _el("ambient-loop");
    if (!el) return;
    var icon = el.querySelector(".ambient-icon");
    var label = el.querySelector(".ambient-label");
    var map = {
      idle:    ["○", "Idle"],
      running: ["◉", "Läuft"],
      done:    ["●", "Fertig"],
      failed:  ["✗", "Fehler"]
    };
    var v = map[status] || map.idle;
    el.dataset.state = status || "idle";
    if (icon) icon.textContent = v[0];
    if (label) label.textContent = v[1];
  }

  function _setLastRun(lr) {
    var el = _el("ambient-last-run");
    if (!el) return;
    if (!lr) {
      el.textContent = "Letzter Run: —";
      el.dataset.ok = "none";
      return;
    }
    var ok = lr.erfolg === true ? "true" : (lr.erfolg === false ? "false" : "none");
    var sym = ok === "true" ? "✓" : (ok === "false" ? "✗" : "·");
    el.textContent = "Letzter Run: " + _fmtRel(lr.ts) + " " + sym;
    el.dataset.ok = ok;
    if (lr.run_id) el.dataset.runId = lr.run_id;
  }


  function _setGates(n) {
    var el = _el("ambient-gates");
    if (!el) return;
    if (!n || n <= 0) {
      el.hidden = true;
    } else {
      el.hidden = false;
      el.textContent = n + (n === 1 ? " Gate offen" : " Gates offen");
    }
  }

  function _clickZiel(ziel) {
    if (ziel === "timeline") {
      var tl = document.querySelector(".bereich.timeline");
      if (tl) tl.scrollIntoView({ behavior: "smooth", block: "nearest" });
    } else if (ziel === "gate-panel") {
      var gp = document.getElementById("gate-panel");
      if (gp) gp.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }

  function _daten(d) {
    if (!d) return;
    _setLoop(d.loop_status);
    _setLastRun(d.last_run);
    _setGates(d.gates_open);
  }

  function lade(projekt) {
    if (projekt) aktuellesProjekt = projekt;
    var url = "/api/projects/" + encodeURIComponent(aktuellesProjekt) + "/ambient";
    fetch(url, { credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .catch(function () { return null; })
      .then(_daten);
  }

  document.addEventListener("DOMContentLoaded", function () {
    // Klick-Handler
    document.querySelectorAll(".ambient-item[data-ziel]").forEach(function (el) {
      el.addEventListener("click", function () { _clickZiel(el.dataset.ziel); });
    });
    lade();
    setInterval(function () { lade(); }, INTERVALL_MS);
  });

  window.WerkstattAmbient = { lade: lade };
})();
