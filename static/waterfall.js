// OP-381i Frontend: Horizontaler Swimlane-Wasserfall (Control-Modus).
// Rendert /swimlane-Daten als SVG: Zeit-Achse horizontal, Lanes vertikal.
// Farben aus sem-Variablen (layout.css :root), kein Hex-Code im JS.
(function () {
  "use strict";

  var POLL_MS = 2000;
  var LANE_H = 26;      // px pro Lane
  var AXIS_H = 28;      // px Zeit-Achse
  var ROW_PAD = 4;
  var LABEL_W = 100;    // linke Spalte fuer Rollen-Namen
  var _timer = null;
  var _aktuellesProjekt = "werkstatt";

  function _el(id) { return document.getElementById(id); }

  // Rolle -> sem-Variable. Monoscope-Prinzip: color = signal.
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

  // Balken-Status -> Fuellfarbe + Symbol (two-signal-Regel)
  function _balkenStil(status) {
    if (status === "error") {
      return {fill: "var(--sem-error)", symbol: "\u2717", class: "wf-err"};
    }
    if (status === "ok") {
      return {fill: "var(--sem-ok)", symbol: "\u2713", class: "wf-ok"};
    }
    if (status === "running") {
      return {fill: "var(--sem-active)", symbol: "\u25cf", class: "wf-running"};
    }
    return {fill: "var(--sem-history)", symbol: "\u25cb", class: "wf-idle"};
  }

  function _fmtDauer(sek) {
    if (!isFinite(sek) || sek < 0) return "";
    if (sek < 1) return Math.round(sek * 1000) + "ms";
    if (sek < 60) return sek.toFixed(1) + "s";
    var m = Math.floor(sek / 60);
    var s = Math.round(sek - m * 60);
    return m + "m" + (s > 0 ? s + "s" : "");
  }

  function _tsSekunden(ts) {
    if (!ts) return NaN;
    var d = new Date(ts);
    return isNaN(d) ? NaN : d.getTime() / 1000;
  }

  // Kompakter Tick-Format: 0ms / 5s / 1m / 2m30 (ohne .5)
  function _fmtTick(sek) {
    if (!isFinite(sek) || sek < 0) return "0";
    if (sek < 1) return Math.round(sek * 1000) + "ms";
    if (sek < 60) return Math.round(sek) + "s";
    var m = Math.floor(sek / 60);
    var s = Math.round(sek - m * 60);
    if (s === 0) return m + "m";
    if (s === 60) return (m + 1) + "m";
    return m + "m" + s + "s";
  }

  // Zeit-Achse: 3-5 Ticks abhaengig von Breite
  function _zeitTicks(t0, t1, breite) {
    var dauer = Math.max(t1 - t0, 0.001);
    var ziel = Math.max(3, Math.min(6, Math.floor(breite / 150)));
    var ticks = [];
    for (var i = 0; i <= ziel; i++) {
      var frac = i / ziel;
      ticks.push({
        x_fraction: frac,
        sekunden: frac * dauer,
        label: _fmtTick(frac * dauer)
      });
    }
    return ticks;
  }

  // Ein einzelner Balken als SVG-Rect + Symbol + Tooltip
  function _balkenZuSvg(balken, t0, t1, x0, breite, y) {
    var start = _tsSekunden(balken.start_ts) - t0;
    var dauer = Math.max(balken.dauer_s || 0.5, 0.2);
    var x_px = x0 + (breite * start / (t1 - t0));
    var w_px = Math.max(8, breite * dauer / (t1 - t0));
    var stil = _balkenStil(balken.status);

    var g = document.createElementNS("http://www.w3.org/2000/svg", "g");
    g.setAttribute("class", "wf-balken " + stil.class);
    g.style.cursor = "pointer";

    var rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    rect.setAttribute("x", x_px);
    rect.setAttribute("y", y);
    rect.setAttribute("width", w_px);
    rect.setAttribute("height", LANE_H - ROW_PAD * 2);
    rect.setAttribute("rx", 3);
    rect.setAttribute("fill", stil.fill);
    rect.setAttribute("opacity", "0.85");
    g.appendChild(rect);

    // Symbol im Balken (Two-Signal-Regel: Form + Farbe, nicht nur Farbe)
    if (w_px > 14) {
      var txt = document.createElementNS("http://www.w3.org/2000/svg", "text");
      txt.setAttribute("x", x_px + w_px / 2);
      txt.setAttribute("y", y + LANE_H / 2 - ROW_PAD + 3);
      txt.setAttribute("text-anchor", "middle");
      txt.setAttribute("font-size", "10");
      txt.setAttribute("fill", "white");
      txt.setAttribute("pointer-events", "none");
      txt.textContent = stil.symbol;
      g.appendChild(txt);
    }

    // Tooltip via <title> (SVG-nativ, kein extra Div)
    var title = document.createElementNS("http://www.w3.org/2000/svg", "title");
    title.textContent = balken.kind + "  \u00b7  " + _fmtDauer(dauer) +
                        (balken.detail ? "\n" + balken.detail : "");
    g.appendChild(title);

    // Klick: bestehender Detail-Drawer (falls vorhanden)
    g.addEventListener("click", function () {
      if (window.WerkstattDetail && window.WerkstattDetail.oeffneRolle) {
        window.WerkstattDetail.oeffneRolle(balken.rolle || "loop");
      }
    });

    return g;
  }

  function _render(data) {
    var container = _el("control-waterfall");
    if (!container) return;
    var zeitspanne = data.zeitspanne || {};
    var lanes = data.lanes || [];
    if (!lanes.length) {
      container.innerHTML = '<div class="wf-leer">Keine Daten f\u00fcr diesen Run.</div>';
      return;
    }

    // Zeit-Range
    var t0 = _tsSekunden(zeitspanne.start_ts);
    var t1 = _tsSekunden(zeitspanne.end_ts);
    if (isNaN(t0) || isNaN(t1) || t1 <= t0) {
      // Fallback: aus balken min/max
      var mins = [], maxs = [];
      lanes.forEach(function (l) {
        (l.balken || []).forEach(function (b) {
          var s = _tsSekunden(b.start_ts);
          var e = _tsSekunden(b.end_ts) || s;
          if (!isNaN(s)) mins.push(s);
          if (!isNaN(e)) maxs.push(e);
        });
      });
      t0 = Math.min.apply(null, mins);
      t1 = Math.max.apply(null, maxs);
      if (!isFinite(t0) || !isFinite(t1) || t1 <= t0) t1 = t0 + 1;
    }

    var breite = container.clientWidth || 800;
    var x0 = LABEL_W;
    var plotW = Math.max(50, breite - LABEL_W - 12);
    var height = AXIS_H + lanes.length * LANE_H + 8;

    // SVG aufbauen
    var svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("width", breite);
    svg.setAttribute("height", height);
    svg.setAttribute("class", "wf-svg");

    // Zeit-Achse
    var ticks = _zeitTicks(t0, t1, plotW);
    ticks.forEach(function (t) {
      var x = x0 + plotW * t.x_fraction;
      var line = document.createElementNS("http://www.w3.org/2000/svg", "line");
      line.setAttribute("x1", x);
      line.setAttribute("y1", AXIS_H - 6);
      line.setAttribute("x2", x);
      line.setAttribute("y2", height - 4);
      line.setAttribute("stroke", "rgba(255,255,255,0.06)");
      line.setAttribute("stroke-width", "1");
      svg.appendChild(line);

      var lbl = document.createElementNS("http://www.w3.org/2000/svg", "text");
      lbl.setAttribute("x", x);
      lbl.setAttribute("y", AXIS_H - 10);
      lbl.setAttribute("text-anchor", "middle");
      lbl.setAttribute("font-size", "10");
      lbl.setAttribute("fill", "var(--text-dim)");
      lbl.textContent = t.label;
      svg.appendChild(lbl);
    });

    // Lanes
    lanes.forEach(function (lane, idx) {
      var y = AXIS_H + idx * LANE_H;

      // Lane-Label (links, ausserhalb Plot-Bereich)
      var lbl = document.createElementNS("http://www.w3.org/2000/svg", "text");
      lbl.setAttribute("x", 8);
      lbl.setAttribute("y", y + LANE_H / 2 - ROW_PAD + 3);
      lbl.setAttribute("font-size", "11");
      lbl.setAttribute("fill", _rolleFarbe(lane.rolle));
      lbl.setAttribute("font-weight", "600");
      lbl.textContent = lane.rolle;
      svg.appendChild(lbl);

      // Trennlinie
      var sep = document.createElementNS("http://www.w3.org/2000/svg", "line");
      sep.setAttribute("x1", 0);
      sep.setAttribute("y1", y);
      sep.setAttribute("x2", breite);
      sep.setAttribute("y2", y);
      sep.setAttribute("stroke", "rgba(255,255,255,0.03)");
      sep.setAttribute("stroke-width", "1");
      svg.appendChild(sep);

      // Balken dieser Lane
      (lane.balken || []).forEach(function (b) {
        svg.appendChild(_balkenZuSvg(b, t0, t1, x0, plotW, y + ROW_PAD));
      });
    });

    // Aktiv-Marker: pulsierender Punkt in der aktiven Lane
    var aktiv = data.aktiv || {};
    if (aktiv.rolle) {
      var idx = -1;
      lanes.forEach(function (l, i) { if (l.rolle === aktiv.rolle) idx = i; });
      if (idx >= 0) {
        var ay = AXIS_H + idx * LANE_H + LANE_H / 2 - ROW_PAD;
        var circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
        circle.setAttribute("cx", breite - 8);
        circle.setAttribute("cy", ay);
        circle.setAttribute("r", 5);
        circle.setAttribute("fill", "var(--sem-active)");
        circle.setAttribute("class", "wf-pulse");
        svg.appendChild(circle);
      }
    }

    container.innerHTML = "";
    container.appendChild(svg);
  }

  function _lade(projekt) {
    if (projekt) _aktuellesProjekt = projekt;
    // Nur rendern, wenn Control-Modus aktiv
    if (document.body.getAttribute("data-mode") !== "control") return;
    fetch("/api/projects/" + encodeURIComponent(_aktuellesProjekt) + "/swimlane",
          {credentials: "same-origin"})
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) {
        if (!d) return;
        _render(d);
      })
      .catch(function (err) {
        console.error("[waterfall] fetch:", err);
      });
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

  // Bei Modus-Wechsel: start/stop automatisch
  document.addEventListener("werkstatt:mode-change", function (ev) {
    var m = ev.detail && ev.detail.mode;
    if (m === "control") start();
    else stop();
  });

  document.addEventListener("DOMContentLoaded", function () {
    if (document.body.getAttribute("data-mode") === "control") start();
  });

  window.WerkstattWaterfall = { start: start, stop: stop, lade: _lade };
})();
