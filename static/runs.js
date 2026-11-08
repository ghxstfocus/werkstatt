// Runs-Liste (OP-233 + OP-303): OPs + Run-Status + Start/Stop.
(function () {
  "use strict";
  var aktuellesProjekt = "werkstatt";
  var _letzterStatus = {};  // Cache fuer Klick-Handler
  var _letzteOps = [];

  function _el(id) { return document.getElementById(id); }

  function _baseUrl() {
    return "/api/projects/" + encodeURIComponent(aktuellesProjekt);
  }

  function _runBadge(state) {
    var map = {
      idle:    ["○", "idle"],
      running: ["●", "läuft"],
      done:    ["✓", "fertig"],
      failed:  ["✗", "fehler"],
    };
    return map[state] || map.idle;
  }

  function _rendere(ops, runStatus) {
    var box = _el("runs-liste");
    if (!box) return;
    box.innerHTML = "";
    var offen = 0, done = 0;
    ops.forEach(function (op) {
      var rs = (runStatus && runStatus[op.id]) || {};
      var state = rs.state || "idle";
      var isRunning = state === "running";

      var div = document.createElement("div");
      div.className = "runs-eintrag";
      div.dataset.status = op.status;
      div.dataset.runState = state;
      div.dataset.opId = op.id;
      div.title = op.titel;

      var dot = document.createElement("span");
      dot.className = "runs-dot";
      div.appendChild(dot);

      var id = document.createElement("span");
      id.className = "runs-id";
      id.textContent = op.id;
      div.appendChild(id);

      var titel = document.createElement("span");
      titel.className = "runs-titel";
      titel.textContent = op.titel;
      div.appendChild(titel);

      // Run-Status-Badge (OP-303)
      var badge = document.createElement("span");
      badge.className = "runs-run-badge";
      var b = _runBadge(state);
      badge.textContent = b[0] + " " + b[1];
      if (isRunning) badge.title = "Loop läuft (run " + (rs.run_id || "?") + ")";
      else if (state === "done") badge.title = "Letzter Run fertig";
      else if (state === "failed") badge.title = "Letzter Run fehlgeschlagen";
      else badge.title = "Noch kein Run";
      div.appendChild(badge);

      var status = document.createElement("span");
      status.className = "runs-status";
      status.textContent = op.status;
      div.appendChild(status);

      // Action-Button (OP-303)
      var btn = document.createElement("button");
      btn.className = "runs-action-btn";
      btn.type = "button";
      if (isRunning) {
        btn.textContent = "■";
        btn.title = "Loop stoppen";
        btn.dataset.action = "stop";
      } else {
        btn.textContent = "▶";
        var blockInfo = op.blockiert_von ? " (blockiert von " + op.blockiert_von + ")" : "";
        btn.title = "Loop mit " + op.id + " starten" + blockInfo;
        btn.dataset.action = "start";
      }
      btn.addEventListener("click", function (e) {
        e.stopPropagation();
        _klickAktion(op.id, isRunning ? "stop" : "start");
      });
      div.appendChild(btn);

      box.appendChild(div);
      if (op.status === "open") offen++;
      else if (op.status === "done") done++;
    });
    var c = _el("runs-counter");
    if (c) c.textContent = offen + " offen · " + done + " done";
  }

  function _klickAktion(opId, aktion) {
    var url = _baseUrl() + "/" + aktion;
    var body = aktion === "start" ? {op_id: opId} : {};
    fetch(url, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      credentials: "same-origin",
      body: JSON.stringify(body),
    })
      .then(function (r) { return r.json().then(function (d) { return {ok: r.ok, data: d}; }); })
      .then(function (res) {
        if (!res.ok) {
          if (res.data && res.data.grund === "laeuft_bereits") {
            // Loop laeuft schon - sanft ignorieren
            return;
          }
          console.warn("Loop-Aktion fehlgeschlagen:", res.data);
        }
        setTimeout(function () { lade(); }, 600);
      })
      .catch(function (err) { console.warn("Loop-Aktion Netzwerkfehler:", err); });
  }

  function lade(projekt) {
    if (projekt) aktuellesProjekt = projekt;
    var base = _baseUrl();
    Promise.all([
      fetch(base + "/ops", {credentials: "same-origin"})
        .then(function (r) { return r.ok ? r.json() : {ops: []}; }),
      fetch(base + "/ops/run-status", {credentials: "same-origin"})
        .then(function (r) { return r.ok ? r.json() : {run_status: {}}; }),
    ])
      .then(function (res) {
        var d = res[0] || {};
        var rs = (res[1] && res[1].run_status) || {};
        _letzterStatus = rs;
        _letzteOps = d.ops || [];
        _rendere(_letzteOps, rs);
      })
      .catch(function () {});
  }

  window.WerkstattRuns = { lade: lade };
  document.addEventListener("DOMContentLoaded", function () { lade(); });
  setInterval(function () { lade(); }, 5000);
})();
