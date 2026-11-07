// Timeline (OP-233): Phasen-Knoten. Click-anywhere-to-toggle + persist.
(function () {
  "use strict";
  var aktuellesProjekt = "werkstatt";
  var PREFIX = "werkstatt-tl-";

  function _el(id) { return document.getElementById(id); }

  function _fmtDauer(start, ende) {
    if (!start || !ende) return "";
    var s = new Date(start), e = new Date(ende);
    if (isNaN(s) || isNaN(e)) return "";
    var ms = e - s;
    if (ms < 0) return "";
    if (ms < 1000) return ms + "ms";
    if (ms < 60000) return (ms / 1000).toFixed(1) + "s";
    return (ms / 60000).toFixed(1) + "min";
  }

  function _leseState(id) {
    try { return localStorage.getItem(PREFIX + id); } catch (e) { return null; }
  }
  function _schreibeState(id, offen) {
    try { localStorage.setItem(PREFIX + id, offen ? "1" : "0"); } catch (e) {}
  }

  function _knotenBauen(k) {
    var el = document.createElement("div");
    el.className = "tl-knoten";
    el.dataset.status = k.status;
    el.dataset.id = k.id;
    var statusLabel = {
      running: "laeuft", ok: "erfolgreich", error: "fehlgeschlagen",
      stale: "verwaist (Run beendet)"
    }[k.status] || k.status;
    el.title = k.label + " -- " + statusLabel +
               "\nKlick zum Auf-/Zuklappen";

    var head = document.createElement("div");
    head.className = "tl-head";

    var dot = document.createElement("span");
    dot.className = "tl-dot";

    var lbl = document.createElement("span");
    lbl.className = "tl-label";
    lbl.textContent = k.label || "?";

    var dur = document.createElement("span");
    dur.className = "tl-dauer";
    dur.textContent = _fmtDauer(k.start_ts, k.end_ts);

    head.appendChild(dot);
    head.appendChild(lbl);
    head.appendChild(dur);
    el.appendChild(head);

    var body = document.createElement("div");
    body.className = "tl-body";
    var kinder = k.children || [];
    if (kinder.length === 0) {
      var leer = document.createElement("div");
      leer.className = "tl-child tl-leer";
      leer.textContent = "keine Details";
      body.appendChild(leer);
    }
    kinder.forEach(function (ch) {
      var row = document.createElement("div");
      row.className = "tl-child";
      row.dataset.status = ch.status || "";
      row.title = (ch.kind || "") + (ch.ts ? "\n" + ch.ts : "");

      var dot = document.createElement("span");
      dot.className = "tl-child-dot";

      var lbl = document.createElement("span");
      lbl.className = "tl-child-label";
      lbl.textContent = ch.detail || ch.kind || "";

      var ts = document.createElement("span");
      ts.className = "tl-child-ts";
      var m = (ch.ts || "").match(/T(\d{2}:\d{2}:\d{2})/);
      ts.textContent = m ? m[1] : "";

      row.appendChild(dot);
      row.appendChild(lbl);
      row.appendChild(ts);
      body.appendChild(row);
    });
    el.appendChild(body);

    if (_leseState(k.id) === "1") el.classList.add("offen");

    el.addEventListener("click", function () {
      el.classList.toggle("offen");
      _schreibeState(k.id, el.classList.contains("offen"));
    });

    return el;
  }

  function _rendere(knoten) {
    var box = _el("timeline");
    if (!box) return;
    var alt = {};
    box.querySelectorAll(".tl-knoten").forEach(function (n) {
      alt[n.dataset.id] = n.classList.contains("offen");
    });
    box.innerHTML = "";
    knoten.forEach(function (k) {
      if (alt[k.id] !== undefined) _schreibeState(k.id, alt[k.id]);
      box.appendChild(_knotenBauen(k));
    });
  }

  function lade(projekt) {
    if (projekt) aktuellesProjekt = projekt;
    fetch("/api/projects/" + encodeURIComponent(aktuellesProjekt) + "/timeline",
          {credentials: "same-origin"})
      .then(function (r) { return r.ok ? r.json() : {knoten: [], run_id: null}; })
      .then(function (d) {
        _rendere(d.knoten || []);
        var r = _el("timeline-run");
        if (r && d.run_id) r.textContent = d.run_id;
      })
      .catch(function () {});
  }

  window.WerkstattTimeline = { lade: lade };
  document.addEventListener("DOMContentLoaded", function () { lade(); });
  setInterval(function () { lade(); }, 5000);
})();
