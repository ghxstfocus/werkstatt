// Timeline (OP-233): Phasen-Knoten aus /api/projects/{name}/timeline
(function () {
  "use strict";
  var aktuellesProjekt = "werkstatt";

  function _el(id) { return document.getElementById(id); }

  function _fmtDauer(start, ende) {
    if (!start || !ende) return "";
    var s = new Date(start), e = new Date(ende);
    if (isNaN(s) || isNaN(e)) return "";
    var ms = e - s;
    if (ms < 1000) return ms + "ms";
    if (ms < 60000) return (ms / 1000).toFixed(1) + "s";
    return (ms / 60000).toFixed(1) + "min";
  }

  function _rendere(knoten) {
    var box = _el("timeline");
    if (!box) return;
    box.innerHTML = "";
    knoten.forEach(function (k) {
      var det = document.createElement("details");
      det.className = "tl-knoten";
      det.dataset.status = k.status;
      var sum = document.createElement("summary");
      sum.textContent = k.label + " ";
      var dauer = _fmtDauer(k.start_ts, k.end_ts);
      if (dauer) {
        var sp = document.createElement("span");
        sp.className = "tl-kind";
        sp.textContent = dauer;
        sum.appendChild(sp);
      }
      det.appendChild(sum);
      (k.children || []).forEach(function (ch) {
        var c = document.createElement("div");
        c.className = "tl-kind";
        c.textContent = ch.ts + "  " + (ch.kind || "") + (ch.detail ? " — " + ch.detail : "");
        det.appendChild(c);
      });
      box.appendChild(det);
    });
    var r = _el("timeline-run");
    if (r) r.textContent = "";
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
