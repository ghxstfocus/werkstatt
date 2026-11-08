// Informed Gate Panel (OP-298). Zeigt offene Gates mit vollem Kontext,
// Empfehlung und Antwort-Buttons. Pollt /gate/context alle 2s.
(function () {
  "use strict";
  var aktuellesProjekt = "werkstatt";
  var POLL_MS = 2000;
  var _timer = null;

  function _el(id) { return document.getElementById(id); }
  function _clear(box) { if (box) box.innerHTML = ""; }

  function _karte(label, wert, klass) {
    var d = document.createElement("div");
    d.className = "gate-card " + (klass || "");
    var l = document.createElement("div");
    l.className = "gate-card-label";
    l.textContent = label;
    var v = document.createElement("div");
    v.className = "gate-card-wert";
    v.textContent = wert || "—";
    d.appendChild(l);
    d.appendChild(v);
    return d;
  }

  function _renderPlan(box, plan) {
    var details = document.createElement("details");
    details.className = "gate-block";
    // Persistenter Offen-State (Poll-Rebuild zerstoert sonst den State)
    var key = "werkstatt-gate-plan-offen";
    try {
      if (localStorage.getItem(key) === "1") details.open = true;
    } catch (e) {}
    details.addEventListener("toggle", function () {
      try { localStorage.setItem(key, details.open ? "1" : "0"); } catch (e) {}
    });
    var sum = document.createElement("summary");
    sum.textContent = "Plan (" + (plan.text ? plan.text.length : 0) + " Zeichen)";
    details.appendChild(sum);
    var pre = document.createElement("pre");
    pre.className = "gate-plan";
    pre.textContent = (plan && plan.text) || "(kein Plan)";
    details.appendChild(pre);
    box.appendChild(details);
  }

  function _renderScout(box, scout) {
    if (!scout) return;
    var details = document.createElement("details");
    details.className = "gate-block";
    var key = "werkstatt-gate-scout-offen";
    try { if (localStorage.getItem(key) === "1") details.open = true; } catch (e) {}
    details.addEventListener("toggle", function () {
      try { localStorage.setItem(key, details.open ? "1" : "0"); } catch (e) {}
    });
    var key = "werkstatt-gate-scout-offen";
    try { if (localStorage.getItem(key) === "1") details.open = true; } catch (e) {}
    details.addEventListener("toggle", function () {
      try { localStorage.setItem(key, details.open ? "1" : "0"); } catch (e) {}
    });
    var sum = document.createElement("summary");
    var n = (scout.befehle || []).length + (scout.dateien || []).length + (scout.findings || []).length;
    sum.textContent = "Scout/Explorer (" + n + ")";
    details.appendChild(sum);
    var list = document.createElement("ul");
    list.className = "gate-list";
    (scout.befehle || []).forEach(function (b) {
      var li = document.createElement("li");
      li.textContent = "Befehl: " + b;
      list.appendChild(li);
    });
    (scout.dateien || []).slice(0, 10).forEach(function (f) {
      var li = document.createElement("li");
      li.textContent = "Datei: " + f;
      list.appendChild(li);
    });
    details.appendChild(list);
    box.appendChild(details);
  }

  function _renderHistorie(box, hist) {
    if (!hist || hist.length === 0) return;
    var details = document.createElement("details");
    details.className = "gate-block";
    var sum = document.createElement("summary");
    sum.textContent = "Historie (" + hist.length + ")";
    details.appendChild(sum);
    var list = document.createElement("ul");
    list.className = "gate-list";
    hist.forEach(function (h) {
      var li = document.createElement("li");
      var zeit = (h.ts || "").match(/T(\d{2}:\d{2}:\d{2})/);
      li.textContent = (zeit ? zeit[1] + " — " : "") + (h.kind || "");
      list.appendChild(li);
    });
    details.appendChild(list);
    box.appendChild(details);
  }

  function _renderDiff(box, ctx) {
    var stat = ctx.diff_stat || "";
    var diff = ctx.diff || "";
    if (!stat && !diff) return;
    var det = document.createElement("details");
    det.className = "gate-block";
    var key = "werkstatt-gate-diff-offen";
    try { if (localStorage.getItem(key) === "1") det.open = true; } catch (e) {}
    det.addEventListener("toggle", function () {
      try { localStorage.setItem(key, det.open ? "1" : "0"); } catch (e) {}
    });
    var sum = document.createElement("summary");
    var dateien = stat ? stat.trim().split("\n").length - 1 : 0;
    sum.textContent = "Aenderungen (" + dateien + " Dateien)";
    det.appendChild(sum);
    if (stat) {
      var preStat = document.createElement("pre");
      preStat.className = "gate-plan gate-diff-stat";
      preStat.textContent = stat;
      det.appendChild(preStat);
    }
    if (diff) {
      var preDiff = document.createElement("pre");
      preDiff.className = "gate-plan gate-diff-body";
      diff.split("\n").forEach(function (linie) {
        var zeile = document.createElement("span");
        zeile.className = "diff-line";
        if (linie.startsWith("+++") || linie.startsWith("---")) {
          zeile.className += " diff-meta";
        } else if (linie.startsWith("+")) {
          zeile.className += " diff-plus";
        } else if (linie.startsWith("-")) {
          zeile.className += " diff-minus";
        } else if (linie.startsWith("@@")) {
          zeile.className += " diff-hunk";
        }
        zeile.textContent = linie + "\n";
        preDiff.appendChild(zeile);
      });
      det.appendChild(preDiff);
    }
    box.appendChild(det);
  }

  function _renderGate(box, ctx) {
    _clear(box);

    var header = document.createElement("div");
    header.className = "gate-header";
    header.textContent = "Human-Gate offen";
    header.title = "Ziehen zum Verschieben";
    box.appendChild(header);
    _machDraggable(box, header);

    var status = document.createElement("div");
    status.className = "gate-status";
    status.appendChild(_karte("Verify",
      ctx.verify ? ctx.verify.status : "—",
      ctx.verify && ctx.verify.status === "ok" ? "ok" :
        (ctx.verify && ctx.verify.status === "error" ? "error" : "")));
    status.appendChild(_karte("Reviewer",
      ctx.reviewer ? ctx.reviewer.verdict : "—", ""));
    status.appendChild(_karte("Empfehlung", ctx.empfehlung,
      ctx.empfehlung === "j" ? "ok" :
        (ctx.empfehlung === "n" ? "error" : "warn")));
    box.appendChild(status);

    var grund = document.createElement("div");
    grund.className = "gate-grund";
    grund.textContent = "Grund: " + (ctx.empfehlung_grund || "—");
    box.appendChild(grund);

    _renderPlan(box, ctx.plan || { text: "" });
    _renderDiff(box, ctx);
    _renderScout(box, ctx.scout);
    _renderHistorie(box, ctx.historie);

    ctx.offene_gates.forEach(function (g) {
      var kasten = document.createElement("div");
      kasten.className = "gate-kasten";
      var prompt = document.createElement("div");
      prompt.className = "gate-prompt";
      prompt.textContent = g.prompt || "Antwort?";
      kasten.appendChild(prompt);
      var btns = document.createElement("div");
      btns.className = "gate-buttons";
      (g.optionen || "jna").split("").forEach(function (opt) {
        var b = document.createElement("button");
        b.className = "gate-btn gate-btn-" + opt;
        b.textContent = {j: "j — Ja", n: "n — Nein", a: "a — Auto"}[opt] || opt;
        b.addEventListener("click", function () {
          b.disabled = true;
          b.textContent = "…";
          fetch("/api/runs/" + encodeURIComponent(ctx.run_id) + "/gate",
                {method: "POST",
                 headers: {"Content-Type": "application/json"},
                 credentials: "same-origin",
                 body: JSON.stringify({gate_id: g.gate_id, answer: opt})})
            .then(function (r) { return r.ok; })
            .then(function (ok) {
              if (!ok) {
                b.disabled = false;
                b.textContent = "Fehler";
                setTimeout(_poll, 500);
              }
            })
            .catch(function () {
              b.disabled = false;
              b.textContent = "Netz-Fehler";
            });
        });
        btns.appendChild(b);
      });
      kasten.appendChild(btns);
      box.appendChild(kasten);
    });
  }

  function _poll() {
    fetch("/api/projects/" + encodeURIComponent(aktuellesProjekt) + "/gate/context",
          {credentials: "same-origin"})
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (ctx) {
        var box = _el("gate-panel");
        if (!box) return;
        if (!ctx || !ctx.offene_gates || ctx.offene_gates.length === 0) {
          _clear(box);
          box.classList.remove("aktiv");
          return;
        }
        box.classList.add("aktiv");
        _renderGate(box, ctx);
      })
      .catch(function () {});
  }

  function lade(projekt) {
    if (projekt) aktuellesProjekt = projekt;
    if (_timer) clearInterval(_timer);
    _poll();
    _timer = setInterval(_poll, POLL_MS);
  }

  window.WerkstattGate = { lade: lade };
  document.addEventListener("DOMContentLoaded", function () { lade(); });
})();
