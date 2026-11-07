// Statusleiste (OP-233): Tasks/Verify/Drift/Phase + Token Loop/Chat
(function () {
  "use strict";
  var aktuellesProjekt = "werkstatt";

  function _el(id) { return document.getElementById(id); }

  function _fmtTokens(n) {
    if (typeof n !== "number" || n <= 0) return "0";
    if (n < 1000) return n.toString();
    if (n < 1000000) return (n / 1000).toFixed(1) + "k";
    return (n / 1000000).toFixed(2) + "M";
  }

  function _status(d) {
    var t = _el("status-tasks");
    if (t) {
      var tasks = d.tasks || {started: 0, done: 0};
      t.textContent = "Tasks: " + tasks.done + "/" + tasks.started;
    }
    var v = _el("status-verify");
    if (v) {
      if (d.verify && d.verify.ok === true) { v.textContent = "Verify: OK"; v.dataset.state = "ok"; }
      else if (d.verify && d.verify.ok === false) { v.textContent = "Verify: FEHLER"; v.dataset.state = "error"; }
      else if (d.verify && d.verify.kind) { v.textContent = "Verify: " + d.verify.kind; v.dataset.state = "warn"; }
      else { v.textContent = "Verify: -"; v.dataset.state = ""; }
    }
    var dr = _el("status-drift");
    if (dr) {
      if (d.drift && d.drift.ok === true) { dr.textContent = "Drift: OK"; dr.dataset.state = "ok"; }
      else if (d.drift && d.drift.ok === false) { dr.textContent = "Drift: FEHLER"; dr.dataset.state = "error"; }
      else if (d.drift && d.drift.status === "ungemessen") {
        dr.textContent = "Drift: -"; dr.dataset.state = "";
        dr.title = "python3 -m tools.quality_gate --hook";
      }
      else { dr.textContent = "Drift: -"; dr.dataset.state = ""; }
    }
    var ph = _el("status-phase");
    if (ph) ph.textContent = "Phase: " + (d.phase || "-");
    var run = _el("status-run");
    if (run) run.textContent = d.run_id || "";
  }

  function _tokens(d) {
    var loop = _el("status-tokens-loop");
    if (loop) {
      var L = d.loop || {prompt: 0, completion: 0, total: 0};
      loop.textContent = "Loop: " + _fmtTokens(L.prompt) + " \u2191 / " + _fmtTokens(L.completion) + " \u2193";
      loop.title = "Loop (run " + (L.run_id || "-") + "): " + L.total + " Token total, " + L.calls + " Calls";
      loop.classList.toggle("aktiv", L.total > 0);
    }
    var chat = _el("status-tokens-chat");
    if (chat) {
      var C = d.chat || {prompt: 0, completion: 0, total: 0};
      chat.textContent = "Chat: " + _fmtTokens(C.prompt) + " \u2191 / " + _fmtTokens(C.completion) + " \u2193";
      chat.title = "Chat (" + C.sessions + " Sessions): " + C.total + " Token total, " + C.calls + " Calls";
      chat.classList.toggle("aktiv", C.total > 0);
    }
  }

  function _fetch(pfad) {
    return fetch("/api/projects/" + encodeURIComponent(aktuellesProjekt) + pfad,
                 {credentials: "same-origin"})
      .then(function (r) { return r.ok ? r.json() : {}; })
      .catch(function () { return {}; });
  }

  function lade(projekt) {
    if (projekt) aktuellesProjekt = projekt;
    _fetch("/status").then(_status);
    _fetch("/tokens").then(_tokens);
  }

  window.WerkstattStatus = { lade: lade };
  document.addEventListener("DOMContentLoaded", function () { lade(); });
  setInterval(function () { lade(); }, 5000);
})();
