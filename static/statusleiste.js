// Statusleiste (OP-233): Tasks/Verify/Drift/Phase + Token Loop/Chat
(function () {
  "use strict";
  var aktuellesProjekt = "werkstatt";
  var ladeGeneration = 0;

  function _el(id) { return document.getElementById(id); }

  function _setTokenText(rootId, text) {
    var root = _el(rootId);
    if (!root) return;
    var t = root.querySelector(".token-text");
    if (t) t.textContent = text;
    else root.textContent = text;
  }

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
      _setTokenText("status-tokens-loop", "Loop: " + _fmtTokens(L.prompt) + " \u2191 / " + _fmtTokens(L.completion) + " \u2193");
      var roleStats = d.by_role || {};
      var roleNames = Object.keys(roleStats).sort();
      var roleLines = roleNames.map(function (role) {
        var R = roleStats[role];
        return role + ": " + R.calls + " Calls, " + _fmtTokens(R.prompt)
          + " Prompt-Token, max " + _fmtTokens(R.max_prompt);
      });
      loop.title = "Loop (run " + (L.run_id || "-") + "): " + L.total
        + " Token total, " + L.calls + " Calls"
        + (roleLines.length ? "\n\nToken pro Rolle:\n" + roleLines.join("\n") : "");
      loop.classList.toggle("aktiv", L.total > 0);
    }
    var chat = _el("status-tokens-chat");
    if (chat) {
      var C = d.chat || {prompt: 0, completion: 0, total: 0};
      _setTokenText("status-tokens-chat", "Chat: " + _fmtTokens(C.prompt) + " \u2191 / " + _fmtTokens(C.completion) + " \u2193");
      chat.title = "Chat (" + C.sessions + " Sessions): " + C.total + " Token total, " + C.calls + " Calls";
      chat.classList.toggle("aktiv", C.total > 0);
    }
  }

  function _fetch(pfad, projekt) {
    return fetch("/api/projects/" + encodeURIComponent(projekt) + pfad,
                 {credentials: "same-origin"})
      .then(function (r) { return r.ok ? r.json() : {}; })
      .catch(function () { return {}; });
  }

  function lade(projekt) {
    if (projekt) aktuellesProjekt = projekt;
    if (!aktuellesProjekt) return;
    var projektGeladen = aktuellesProjekt;
    var generation = ++ladeGeneration;
    _fetch("/status", projektGeladen).then(function (d) {
      if (generation === ladeGeneration && projektGeladen === aktuellesProjekt) _status(d);
    });
    _fetch("/tokens", projektGeladen).then(function (d) {
      if (generation === ladeGeneration && projektGeladen === aktuellesProjekt) _tokens(d);
    });
    _projection(projektGeladen, generation);
  }

  function zeige_uebersicht() {
    aktuellesProjekt = null;
    ladeGeneration++;
    ["status-tasks", "status-verify", "status-drift", "status-phase", "status-run"].forEach(function (id) {
      var item = _el(id);
      if (item) { item.textContent = ""; item.dataset.state = ""; }
    });
    ["status-tokens-loop", "status-tokens-chat"].forEach(function (id) {
      var item = _el(id);
      if (!item) return;
      _setTokenText(id, (id === "status-tokens-loop" ? "Loop: —" : "Chat: —"));
      item.classList.remove("aktiv");
      item.title = "";
    });
    var projection = _el("status-projection");
    if (projection) { projection.textContent = ""; projection.dataset.state = ""; }
    var run = _el("status-run");
    if (run) run.textContent = "";
  }

  function _projection(projekt, generation) {
    var el = _el("status-projection");
    if (!el) return;
    var pfad = "/api/projects/" + encodeURIComponent(projekt) + "/projection/status";
    fetch(pfad, {credentials: "same-origin"})
      .then(function (r) { return r.ok ? r.json() : null; })
      .catch(function () { return null; })
      .then(function (d) {
        if (generation !== ladeGeneration || projekt !== aktuellesProjekt) return;
        if (!d) { el.textContent = ""; el.dataset.state = ""; return; }
        if (d.diff > 0) {
          el.textContent = "Proj: " + d.diff + " offen";
          el.dataset.state = "warn";
          el.title = "JSONL: " + d.jsonl_events + " / SQLite: " + d.sqlite_rows;
        } else {
          el.textContent = "Proj: OK";
          el.dataset.state = "ok";
          el.title = "JSONL=" + d.jsonl_events + " SQLite=" + d.sqlite_rows;
        }
      });
  }

  window.WerkstattStatus = { lade: lade, zeige_uebersicht: zeige_uebersicht };
  document.addEventListener("DOMContentLoaded", function () {
    var aktiverTab = document.querySelector(".tab.ist-aktiv");
    if (aktiverTab && aktiverTab.dataset.projekt) lade(aktiverTab.dataset.projekt);
    else zeige_uebersicht();
  });
  setInterval(function () { lade(); }, 5000);
})();
