// Runs-Liste (OP-233 + OP-303): OPs + Run-Status + Start/Stop.
(function () {
  "use strict";
  var aktuellesProjekt = "werkstatt";
  var _letzterStatus = {};  // Cache fuer Klick-Handler
  var _letzteOps = [];
  var _loopControl = {state: "idle"};
  var _aktionMeldung = "";
  var _aktionLaeuft = false;

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

  function _rendere(ops, runStatus, loopControl) {
    var box = _el("runs-liste");
    if (!box) return;
    box.innerHTML = "";
    var toolbarHost = document.body.getAttribute("data-mode") === "control"
      ? document.getElementById("control-run-toolbar")
      : null;
    if (toolbarHost) toolbarHost.innerHTML = "";
    var control = loopControl || {state: "idle"};
    var loopAktiv = control.state === "running" || control.state === "paused";
    var steuerung = document.createElement("div");
    steuerung.className = "runs-control";
    var zustand = document.createElement("span");
    zustand.className = "runs-control-state";
    zustand.textContent = control.state === "paused"
      ? "Loop pausiert"
      : control.state === "running"
        ? "Loop läuft" + (control.run_id ? " · " + control.run_id : "")
        : "Kein aktiver Loop";
    steuerung.appendChild(zustand);

    var aktionen = document.createElement("div");
    aktionen.className = "runs-control-actions";
    function controlButton(action, label) {
      var button = document.createElement("button");
      button.type = "button";
      button.className = "runs-action-btn";
      button.dataset.action = action;
      button.textContent = label;
      button.disabled = _aktionLaeuft;
      button.addEventListener("click", function () {
        _klickAktion("", action);
      });
      aktionen.appendChild(button);
    }
    if (control.state === "running") {
      controlButton("pause", "⏸ Pause");
      controlButton("stop", "■ Stop");
    } else if (control.state === "paused") {
      controlButton("resume", "▶ Fortsetzen");
      controlButton("stop", "■ Stop");
    }
    steuerung.appendChild(aktionen);

    var meldung = document.createElement("span");
    meldung.className = "runs-control-message";
    meldung.setAttribute("role", "status");
    meldung.setAttribute("aria-live", "polite");
    meldung.textContent = _aktionMeldung;
    steuerung.appendChild(meldung);
    (toolbarHost || box).appendChild(steuerung);

    var offen = 0, done = 0;
    ops.forEach(function (op) {
      var rs = (runStatus && runStatus[op.id]) || {};
      var state = rs.state || "idle";
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

      // OPEN-Status redundant (parse_ops filtert done raus) — nur
      // bei partial/blocked zeigen.
      var status = document.createElement("span");
      status.className = "runs-status";
      if (op.status && op.status !== "open") {
        status.textContent = op.status;
      } else {
        status.hidden = true;
      }
      div.appendChild(status);

      // Action-Button (OP-303): nur offene, freigegebene OPs starten.
      var btn = document.createElement("button");
      btn.className = "runs-action-btn";
      btn.type = "button";
      var istStartbar = op.status === "open" && !op.blockiert_von;
      if (loopAktiv) {
        btn.hidden = true;
        btn.dataset.action = "controlled";
      } else if (!istStartbar) {
        btn.textContent = "⊘";
        btn.disabled = true;
        btn.title = op.blockiert_von
          ? "OP blockiert von " + op.blockiert_von
          : "OP ist nicht als offen freigegeben";
        btn.dataset.action = "blocked";
      } else {
        btn.textContent = "▶";
        btn.title = "Loop mit " + op.id + " starten";
        btn.dataset.action = "start";
      }
      btn.addEventListener("click", function (e) {
        e.stopPropagation();
        if (!loopAktiv && istStartbar) _klickAktion(op.id, "start");
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
    if (_aktionLaeuft) return;
    var url = _baseUrl() + "/" + aktion;
    var body = aktion === "start" ? {op_id: opId} : {};
    var label = {
      start: "Start",
      pause: "Pause",
      resume: "Fortsetzen",
      stop: "Stop",
    }[aktion] || aktion;
    _aktionLaeuft = true;
    _aktionMeldung = label + " wird ausgeführt …";
    _rendere(_letzteOps, _letzterStatus, _loopControl);

    fetch(url, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      credentials: "same-origin",
      body: JSON.stringify(body),
    })
      .then(function (r) {
        return r.json().then(function (d) {
          return {ok: r.ok, data: d};
        });
      })
      .then(function (res) {
        if (!res.ok) {
          throw new Error((res.data && res.data.detail) || "HTTP-Fehler");
        }
        if (res.data && res.data.grund === "laeuft_bereits") {
          _aktionMeldung = "Für dieses Projekt läuft bereits ein Loop.";
        } else if (res.data && res.data.bereits_pausiert) {
          _aktionMeldung = "Der Loop war bereits pausiert.";
        } else if (res.data && res.data.bereits_laufend) {
          _aktionMeldung = "Der Loop lief bereits.";
        } else {
          _aktionMeldung = label + " erfolgreich.";
        }
      })
      .catch(function (err) {
        _aktionMeldung = label + " fehlgeschlagen: " + err.message;
      })
      .finally(function () {
        _aktionLaeuft = false;
        lade();
      });
  }

  function lade(projekt) {
    if (projekt && projekt !== aktuellesProjekt) _aktionMeldung = "";
    if (projekt) aktuellesProjekt = projekt;
    var base = _baseUrl();
    Promise.all([
      fetch(base + "/ops", {credentials: "same-origin"})
        .then(function (r) { return r.ok ? r.json() : {ops: []}; }),
      fetch(base + "/ops/run-status", {credentials: "same-origin"})
        .then(function (r) { return r.ok ? r.json() : {run_status: {}}; }),
      fetch(base + "/loop", {credentials: "same-origin"})
        .then(function (r) { return r.ok ? r.json() : {state: "idle"}; }),
    ])
      .then(function (res) {
        var d = res[0] || {};
        var rs = (res[1] && res[1].run_status) || {};
        _loopControl = res[2] || {state: "idle"};
        _letzterStatus = rs;
        _letzteOps = d.ops || [];
        _rendere(_letzteOps, rs, _loopControl);
      })
      .catch(function () {});
  }

  window.WerkstattRuns = { lade: lade };
  document.addEventListener("DOMContentLoaded", function () { lade(); });
  setInterval(function () { lade(); }, 5000);
})();
