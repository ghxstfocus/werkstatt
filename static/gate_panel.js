// OP-381c: Human-Gate als Modal.
(function () {
  "use strict";

  var POLL_MS = 2000;
  var _aktuellesProjekt = "werkstatt";
  var _timer = null;
  var _aktuelleCtx = null;
  var _bannerDismissed = false;

  function _el(id) { return document.getElementById(id); }

  function _zeigeBanner() {
    var b = _el("gate-banner");
    if (b && !_bannerDismissed) b.hidden = false;
  }
  function _versteckeBanner() {
    var b = _el("gate-banner");
    if (b) b.hidden = true;
  }

  function _oeffneModal() {
    var m = _el("gate-modal");
    var bd = _el("gate-backdrop");
    if (m) m.hidden = false;
    if (bd) { bd.hidden = false; requestAnimationFrame(function () { bd.classList.add("aktiv"); }); }
    requestAnimationFrame(function () { if (m) m.classList.add("aktiv"); });
    _bannerDismissed = true;
    _versteckeBanner();
  }
  function _schliesseModal() {
    var m = _el("gate-modal");
    var bd = _el("gate-backdrop");
    if (m) m.classList.remove("aktiv");
    if (bd) bd.classList.remove("aktiv");
    setTimeout(function () {
      if (m) m.hidden = true;
      if (bd) bd.hidden = true;
    }, 200);
    _bannerDismissed = false;
  }

  function _karte(label, wert, klasse) {
    var d = document.createElement("div");
    d.className = "gm-card " + (klasse || "");
    var l = document.createElement("div");
    l.className = "gm-card-label";
    l.textContent = label;
    var v = document.createElement("div");
    v.className = "gm-card-wert";
    v.textContent = wert || "—";
    d.appendChild(l);
    d.appendChild(v);
    return d;
  }

  function _renderPlanMarkdown(pre, text) {
    pre.innerHTML = "";
    var zeilen = (text || "").split("\n");
    for (var i = 0; i < zeilen.length; i++) {
      var z = zeilen[i];
      var sp = document.createElement("span");
      if (/^##\s/.test(z)) {
        sp.className = "gm-h2";
        sp.textContent = z.replace(/^##\s+/, "");
      } else if (/^[-*]\s/.test(z)) {
        sp.className = "gm-li";
        sp.textContent = "\u2022 " + z.replace(/^[-*]\s+/, "");
      } else {
        sp.textContent = z;
      }
      pre.appendChild(sp);
      pre.appendChild(document.createTextNode("\n"));
    }
  }

  function _renderPlan(container, planText) {
    var wrap = document.createElement("div");
    wrap.className = "gm-plan-wrap";

    var toolbar = document.createElement("div");
    toolbar.className = "gm-plan-toolbar";
    var titel = document.createElement("span");
    titel.className = "gm-plan-titel";
    titel.textContent = "Plan (" + (planText ? planText.length : 0) + " Zeichen)";
    toolbar.appendChild(titel);

    var copyBtn = document.createElement("button");
    copyBtn.type = "button";
    copyBtn.className = "gm-copy-btn";
    copyBtn.textContent = "\uD83D\uDCCB Als Markdown kopieren";
    copyBtn.addEventListener("click", function () {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(planText || "").then(function () {
          copyBtn.textContent = "\u2713 Kopiert";
          copyBtn.classList.add("kopiert");
          setTimeout(function () {
            copyBtn.textContent = "\uD83D\uDCCB Als Markdown kopieren";
            copyBtn.classList.remove("kopiert");
          }, 2000);
        });
      }
    });
    toolbar.appendChild(copyBtn);
    wrap.appendChild(toolbar);

    var pre = document.createElement("pre");
    pre.className = "gm-plan";
    _renderPlanMarkdown(pre, planText || "(kein Plan)");
    wrap.appendChild(pre);

    container.appendChild(wrap);
  }

  function _renderSection(container, titel, inhaltFn) {
    var det = document.createElement("details");
    det.className = "gm-section";
    var sum = document.createElement("summary");
    sum.textContent = titel;
    det.appendChild(sum);
    inhaltFn(det);
    container.appendChild(det);
  }

  function _renderDiff(container, ctx) {
    var stat = ctx.diff_stat || "";
    var diff = ctx.diff || "";
    if (!stat && !diff) return;
    var dateien = stat ? (stat.trim().split("\n").length - 1) : 0;
    _renderSection(container, "\u00c4nderungen (" + dateien + " Dateien)", function (det) {
      var pre = document.createElement("pre");
      pre.className = "gm-section-pre";
      pre.textContent = stat + (diff ? "\n\n" + diff : "");
      det.appendChild(pre);
    });
  }

  function _renderScout(container, scout) {
    if (!scout) return;
    var n = (scout.befehle || []).length + (scout.dateien || []).length
          + (scout.findings || []).length;
    if (n === 0) return;
    _renderSection(container, "Scout/Explorer (" + n + ")", function (det) {
      var ul = document.createElement("ul");
      ul.className = "gm-list";
      (scout.befehle || []).forEach(function (b) {
        var li = document.createElement("li");
        li.textContent = "Befehl: " + b;
        ul.appendChild(li);
      });
      (scout.dateien || []).slice(0, 10).forEach(function (f) {
        var li = document.createElement("li");
        li.textContent = "Datei: " + f;
        ul.appendChild(li);
      });
      det.appendChild(ul);
    });
  }

  function _renderHistorie(container, hist) {
    if (!hist || hist.length === 0) return;
    _renderSection(container, "Historie (" + hist.length + ")", function (det) {
      var ul = document.createElement("ul");
      ul.className = "gm-list";
      hist.forEach(function (h) {
        var li = document.createElement("li");
        var zeit = (h.ts || "").match(/T(\d{2}:\d{2}:\d{2})/);
        li.textContent = (zeit ? zeit[1] + " \u2014 " : "") + (h.kind || "");
        ul.appendChild(li);
      });
      det.appendChild(ul);
    });
  }

  function _debuggeImChat(ctx, gate) {
    var chat = window.WerkstattChat;
    if (!chat || typeof chat.uebergebeGate !== "function") {
      return Promise.resolve(false);
    }
    var diff = String(ctx.diff || "");
    var maxDiff = 25000;
    var kontext = {
      project: _aktuellesProjekt,
      run_id: ctx.run_id,
      gate_id: gate.gate_id,
      gate_prompt: gate.prompt || "",
      gate_type: gate.typ || "jna",
      plan: (ctx.plan || {}).text || "",
      verify: ctx.verify || null,
      reviewer: ctx.reviewer || null,
      diff_stat: ctx.diff_stat || "",
      diff: diff.slice(0, maxDiff),
      diff_truncated: diff.length > maxDiff,
      empfehlung: ctx.empfehlung || "",
      empfehlung_grund: ctx.empfehlung_grund || "",
    };
    if (window.WerkstattMode && window.WerkstattMode.setMode) {
      window.WerkstattMode.setMode("debug");
    }
    return chat.uebergebeGate(_aktuellesProjekt, kontext);
  }

  function _sendeAntwort(ctx, gateId, antwort) {
    return fetch("/api/runs/" + encodeURIComponent(ctx.run_id) + "/gate", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      credentials: "same-origin",
      body: JSON.stringify({gate_id: gateId, answer: antwort}),
    }).then(function (r) { return r.ok; });
  }

  function _renderActions(container, ctx) {
    (ctx.offene_gates || []).forEach(function (g) {
      var kasten = document.createElement("div");
      kasten.className = "gm-gate-kasten";

      var prompt = document.createElement("div");
      prompt.className = "gm-gate-prompt";
      prompt.textContent = g.prompt || "Antwort?";
      kasten.appendChild(prompt);

      var typ = g.typ || "jna";

      if (typ === "freitext") {
        var ta = document.createElement("textarea");
        ta.className = "gm-textarea";
        ta.placeholder = "Freitext eingeben (Enter sendet, Shift+Enter = Zeilenumbruch)";
        ta.addEventListener("keydown", function (e) {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            _abschicken();
          }
        });
        kasten.appendChild(ta);

        var hinweis = document.createElement("div");
        hinweis.className = "gm-textarea-hinweis";
        hinweis.textContent = "Enter sendet, Shift+Enter macht Zeilenumbruch.";
        kasten.appendChild(hinweis);

        var senden = document.createElement("button");
        senden.type = "button";
        senden.className = "gm-btn gm-btn-j";
        senden.textContent = "Senden";
        senden.style.marginTop = "8px";
        kasten.appendChild(senden);

        var _abschicken = function () {
          var antwort = ta.value || "";
          ta.disabled = true;
          senden.disabled = true;
          senden.textContent = "\u2026";
          _sendeAntwort(ctx, g.gate_id, antwort).then(function (ok) {
            if (ok) {
              _schliesseModal();
            } else {
              ta.disabled = false;
              senden.disabled = false;
              senden.textContent = "Fehler, nochmal";
            }
          }).catch(function () {
            ta.disabled = false;
            senden.disabled = false;
            senden.textContent = "Netz-Fehler";
          });
        };
        senden.addEventListener("click", _abschicken);
      } else {
        var btns = document.createElement("div");
        btns.className = "gm-btn-group";
        (g.optionen || "jna").split("").forEach(function (opt) {
          var b = document.createElement("button");
          b.type = "button";
          b.className = "gm-btn gm-btn-" + opt;
          b.textContent = {
            j: "j \u2014 Ja",
            n: "n \u2014 Nein",
            a: "a \u2014 Plan anpassen",
            e: "Im Chat debuggen",
          }[opt] || opt;
          b.addEventListener("click", function () {
            b.disabled = true;
            b.textContent = "\u2026";
            var operation = opt === "e"
              ? _debuggeImChat(ctx, g)
              : _sendeAntwort(ctx, g.gate_id, opt);
            operation.then(function (ok) {
              if (ok) {
                if (opt === "e") b.textContent = "Chat geöffnet · Gate bleibt offen";
                _schliesseModal();
              } else {
                b.disabled = false;
                b.textContent = opt === "e" ? "Chat nicht erreichbar" : "Fehler";
              }
            }).catch(function () {
              b.disabled = false;
              b.textContent = "Netz-Fehler";
            });
          });
          btns.appendChild(b);
        });
        kasten.appendChild(btns);
      }

      container.appendChild(kasten);
    });
  }

  function _renderModal(ctx) {
    _aktuelleCtx = ctx;
    var body = _el("gate-modal-body");
    var actions = _el("gate-modal-actions");
    if (!body || !actions) return;
    body.innerHTML = "";
    actions.innerHTML = "";

    var status = document.createElement("div");
    status.className = "gm-status";
    status.appendChild(_karte(
      "Verify",
      ctx.verify ? ctx.verify.status : "\u2014",
      ctx.verify && ctx.verify.status === "ok" ? "ok"
        : (ctx.verify && ctx.verify.status === "error" ? "error" : "")
    ));
    status.appendChild(_karte(
      "Reviewer",
      ctx.reviewer ? ctx.reviewer.verdict : "\u2014",
      ""
    ));
    status.appendChild(_karte(
      "Empfehlung",
      ctx.empfehlung,
      ctx.empfehlung === "j" ? "ok"
        : (ctx.empfehlung === "n" ? "error" : "warn")
    ));
    body.appendChild(status);

    var grund = document.createElement("div");
    grund.className = "gm-grund";
    grund.textContent = "Grund: " + (ctx.empfehlung_grund || "\u2014");
    body.appendChild(grund);

    _renderPlan(body, (ctx.plan || {}).text || "");

    _renderDiff(body, ctx);
    _renderScout(body, ctx.scout);
    _renderHistorie(body, ctx.historie);

    _renderActions(actions, ctx);
  }

  function _poll() {
    fetch("/api/projects/" + encodeURIComponent(_aktuellesProjekt) + "/gate/context",
          {credentials: "same-origin"})
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (ctx) {
        var hatGates = ctx && ctx.offene_gates && ctx.offene_gates.length > 0;
        if (!hatGates) {
          _versteckeBanner();
          _schliesseModal();
          return;
        }
        _renderModal(ctx);
        var m = _el("gate-modal");
        var modalOffen = m && !m.hidden;
        if (!modalOffen && !_bannerDismissed) _zeigeBanner();
      })
      .catch(function (err) { console.error("[gate_panel] poll:", err); });
  }

  document.addEventListener("DOMContentLoaded", function () {
    var banner = _el("gate-banner");
    if (banner) {
      banner.addEventListener("click", function (e) {
        if (e.target.id === "gate-banner-close") return;
        _oeffneModal();
      });
    }
    var bClose = _el("gate-banner-close");
    if (bClose) {
      bClose.addEventListener("click", function (e) {
        e.stopPropagation();
        _bannerDismissed = true;
        _versteckeBanner();
      });
    }
    var mClose = _el("gate-modal-close");
    if (mClose) mClose.addEventListener("click", _schliesseModal);
    var bd = _el("gate-backdrop");
    if (bd) bd.addEventListener("click", _schliesseModal);
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") {
        var m = _el("gate-modal");
        if (m && !m.hidden) _schliesseModal();
      }
    });

    _poll();
    _timer = setInterval(_poll, POLL_MS);
  });

  window.WerkstattGate = {
    lade: function (projekt) {
      if (projekt) _aktuellesProjekt = projekt;
      _poll();
    },
    oeffne: _oeffneModal,
    schliesse: _schliesseModal,
  };
})();
