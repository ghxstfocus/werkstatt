// OP-381j Frontend: Live-Feed im Control-Modus.
// Vertikale Chronologie. Aktiv-Rolle prominent + pulsierend oben,
// Steps chronologisch darunter. Farben aus sem-Variablen.
(function () {
  "use strict";

  var POLL_MS = 2000;
  var _timer = null;
  var _aktuellesProjekt = "werkstatt";
  var _letzteSteps = [];   // Cache fuer Diff (neue Step = Flash-Animation)

  function _el(id) { return document.getElementById(id); }

  // Rolle -> sem-Variable (identisch zu waterfall.js)
  var ROLLEN_FARBE = {
    "explorer":   "var(--sem-active)",
    "scout":      "var(--sem-active-strong)",
    "architect":  "var(--sem-warn)",
    "planner":    "var(--sem-warn-strong)",
    "builder":    "var(--sem-action)",
    "verify":     "var(--sem-ok)",
    "reviewer":   "var(--sem-ok-strong)",
    "reflection": "var(--sem-action-muted)",
    "loop":       "var(--sem-history)"
  };

  function _rolleFarbe(rolle) {
    return ROLLEN_FARBE[rolle] || "var(--sem-history)";
  }

  // Zwei-Signal-Regel: Status = Symbol + Farbe
  function _statusStil(status) {
    if (status === "error") return {symbol: "\u2717", cls: "lf-err"};
    if (status === "ok")    return {symbol: "\u2713", cls: "lf-ok"};
    if (status === "running") return {symbol: "\u25cf", cls: "lf-running"};
    return {symbol: "\u25cb", cls: "lf-idle"};
  }

  function _fmtZeit(ts) {
    if (!ts) return "";
    var m = String(ts).match(/T(\d{2}:\d{2}:\d{2})/);
    return m ? m[1] : String(ts).slice(-8);
  }

  function _fmtSeit(sek) {
    if (!isFinite(sek) || sek < 0) return "";
    if (sek < 60) return Math.round(sek) + "s";
    var m = Math.floor(sek / 60);
    var s = Math.round(sek - m * 60);
    return m + "m" + (s > 0 ? s + "s" : "");
  }

  // Aktiv-Block oben (prominent, pulsierend)
  function _renderAktiv(aktiv) {
    var box = document.createElement("div");
    box.className = "lf-aktiv";
    if (!aktiv || !aktiv.rolle) {
      box.classList.add("lf-aktiv-idle");
      var lbl = document.createElement("span");
      lbl.className = "lf-aktiv-label";
      lbl.textContent = "\u25cb Kein Run aktiv";
      box.appendChild(lbl);
      return box;
    }
    box.classList.add("lf-aktiv-live");
    box.style.borderColor = _rolleFarbe(aktiv.rolle);

    var dot = document.createElement("span");
    dot.className = "lf-aktiv-dot";
    dot.style.background = _rolleFarbe(aktiv.rolle);
    box.appendChild(dot);

    var rolle = document.createElement("span");
    rolle.className = "lf-aktiv-rolle";
    rolle.style.color = _rolleFarbe(aktiv.rolle);
    rolle.textContent = aktiv.rolle;
    box.appendChild(rolle);

    var aktion = document.createElement("span");
    aktion.className = "lf-aktiv-aktion";
    aktion.textContent = aktiv.aktion || aktiv.kind || "";
    box.appendChild(aktion);

    var seit = document.createElement("span");
    seit.className = "lf-aktiv-seit";
    seit.textContent = _fmtSeit(aktiv.seit_s);
    box.appendChild(seit);

    return box;
  }

  // Eine Zeile (Step)
  function _renderStep(step, istNeu) {
    var row = document.createElement("div");
    row.className = "lf-step";
    if (istNeu) row.classList.add("lf-step-neu");
    row.style.cursor = "pointer";
    row.title = (step.kind || "") + (step.detail ? "\n" + step.detail : "");

    var ts = document.createElement("span");
    ts.className = "lf-step-ts";
    ts.textContent = _fmtZeit(step.ts);
    row.appendChild(ts);

    var rolle = document.createElement("span");
    rolle.className = "lf-step-rolle";
    rolle.style.color = _rolleFarbe(step.rolle);
    rolle.textContent = (step.rolle || "loop").slice(0, 10);
    row.appendChild(rolle);

    var detail = document.createElement("span");
    detail.className = "lf-step-detail";
    detail.textContent = step.detail || step.kind || "";
    row.appendChild(detail);

    var stil = _statusStil(step.status);
    var sym = document.createElement("span");
    sym.className = "lf-step-sym " + stil.cls;
    sym.textContent = stil.symbol;
    row.appendChild(sym);

    // Klick: Detail-Drawer
    row.addEventListener("click", function () {
      if (window.WerkstattDetail && window.WerkstattDetail.oeffneRolle) {
        window.WerkstattDetail.oeffneRolle(step.rolle || "loop");
      }
    });

    return row;
  }

  // Naechster-Schritt-Hinweis (unterste Zeile)
  function _renderNaechster(naechster) {
    if (!naechster || !naechster.rolle) return null;
    var row = document.createElement("div");
    row.className = "lf-naechster";
    var lbl = document.createElement("span");
    lbl.className = "lf-naechster-label";
    lbl.textContent = "\u2192 N\u00e4chster Schritt:";
    row.appendChild(lbl);
    var rolle = document.createElement("span");
    rolle.className = "lf-naechster-rolle";
    rolle.style.color = _rolleFarbe(naechster.rolle);
    rolle.textContent = naechster.rolle;
    row.appendChild(rolle);
    return row;
  }

  function _render(data) {
    var container = _el("control-live-feed");
    if (!container) return;

    var runLabel = _el("control-lf-run");
    if (runLabel && data.run_id) runLabel.textContent = data.run_id;

    // Cache-Vergleich: neue Step = Flash-Animation
    var neueSteps = data.steps || [];
    var letzteIds = {};
    _letzteSteps.forEach(function (s) {
      letzteIds[(s.ts || "") + "|" + (s.kind || "")] = true;
    });

    container.innerHTML = "";

    // Aktiv-Block (immer oben)
    container.appendChild(_renderAktiv(data.aktiv || {}));

    // Steps-Bereich
    var stepsBox = document.createElement("div");
    stepsBox.className = "lf-steps";
    if (neueSteps.length === 0) {
      var leer = document.createElement("div");
      leer.className = "lf-leer";
      leer.textContent = "Keine Events f\u00fcr diesen Run.";
      stepsBox.appendChild(leer);
    } else {
      neueSteps.forEach(function (s) {
        var istNeu = !letzteIds[(s.ts || "") + "|" + (s.kind || "")];
        stepsBox.appendChild(_renderStep(s, istNeu));
      });
    }
    container.appendChild(stepsBox);

    // Naechster-Schritt-Hinweis
    var nx = _renderNaechster(data.naechster || {});
    if (nx) container.appendChild(nx);

    _letzteSteps = neueSteps;
  }

  function _lade(projekt) {
    if (projekt) _aktuellesProjekt = projekt;
    if (document.body.getAttribute("data-mode") !== "control") return;
    fetch("/api/projects/" + encodeURIComponent(_aktuellesProjekt) +
          "/live-feed?limit=30",
          {credentials: "same-origin"})
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) { if (d) _render(d); })
      .catch(function (err) { console.error("[live_feed]", err); });
  }

  function start(projekt) {
    if (projekt) _aktuellesProjekt = projekt;
    if (_timer) clearInterval(_timer);
    _lade();
    _timer = setInterval(_lade, POLL_MS);
  }

  function stop() {
    if (_timer) clearInterval(_timer);
    _timer = null;
  }

  document.addEventListener("werkstatt:mode-change", function (ev) {
    var m = ev.detail && ev.detail.mode;
    if (m === "control") start();
    else stop();
  });

  document.addEventListener("DOMContentLoaded", function () {
    if (document.body.getAttribute("data-mode") === "control") start();
  });

  window.WerkstattLiveFeed = { start: start, stop: stop, lade: _lade };
})();
