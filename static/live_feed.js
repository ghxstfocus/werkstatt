// OP-381j Frontend: Live-Feed im Control-Modus + Codex-Polish.
// Vertikale Chronologie. Aktiv-Rolle prominent + pulsierend oben,
// Steps chronologisch darunter. Spinner (Braille) + animierte Dots
// + Shimmer + "alte Aktiv wird Step"-Transition. Farben sem.
(function () {
  "use strict";

  var POLL_MS = 2000;
  var STEPS_LIMIT = 8;
  var _timer = null;
  var _aktuellesProjekt = null;
  var _overviewAktiv = false;
  var _letzteSteps = [];

  // Codex-Spinner (Braille, 10 Frames)
  var SPINNER = ["\u280b", "\u2819", "\u2839", "\u2838", "\u283c",
                 "\u2834", "\u2826", "\u2827", "\u2807", "\u280f"];
  var _spinnerIdx = 0;
  var _spinnerTimer = null;
  var _letzteAktiv = null;
  var _letzteAktivTs = 0;

  function _el(id) { return document.getElementById(id); }

  function _startSpinner() {
    if (_spinnerTimer) return;
    _spinnerTimer = setInterval(function () {
      _spinnerIdx = (_spinnerIdx + 1) % SPINNER.length;
      var chars = document.querySelectorAll(".lf-spinner-char");
      for (var i = 0; i < chars.length; i++) {
        chars[i].textContent = SPINNER[_spinnerIdx];
      }
    }, 80);
  }

  function _stopSpinner() {
    if (_spinnerTimer) clearInterval(_spinnerTimer);
    _spinnerTimer = null;
  }

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
    "loop":       "var(--sem-history)",
    "chat":       "var(--sem-action)"
  };

  function _rolleFarbe(rolle) {
    return ROLLEN_FARBE[rolle] || "var(--sem-history)";
  }

  // Two-Signal-Regel: Symbol + Farbe
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

  // Aktiv-Block oben (Codex-Style: Spinner + animierte Dots + Shimmer)
  function _renderAktiv(aktiv) {
    var box = document.createElement("div");
    box.className = "lf-aktiv";

    if (!aktiv || !aktiv.rolle) {
      var jetzt = Date.now();
      if (_letzteAktiv && (jetzt - _letzteAktivTs) < 3000) {
        box.classList.add("lf-aktiv-wartend");
        box.style.borderColor = _rolleFarbe(_letzteAktiv.rolle);
        var dw = document.createElement("span");
        dw.className = "lf-aktiv-dot";
        dw.style.background = _rolleFarbe(_letzteAktiv.rolle);
        box.appendChild(dw);
        var rw = document.createElement("span");
        rw.className = "lf-aktiv-rolle";
        rw.style.color = _rolleFarbe(_letzteAktiv.rolle);
        rw.textContent = _letzteAktiv.rolle;
        box.appendChild(rw);
        var wt = document.createElement("span");
        wt.className = "lf-aktiv-aktion lf-dots";
        wt.textContent = "warte auf naechsten Schritt";
        box.appendChild(wt);
        return box;
      }
      box.classList.add("lf-aktiv-idle");
      var lbl = document.createElement("span");
      lbl.className = "lf-aktiv-label";
      lbl.textContent = "\u25cb Kein Run aktiv";
      box.appendChild(lbl);
      return box;
    }

    box.classList.add("lf-aktiv-live");
    box.style.borderColor = _rolleFarbe(aktiv.rolle);
    if (_letzteAktiv && _letzteAktiv.rolle === aktiv.rolle) {
      box.classList.add("lf-aktiv-gleich");
    } else {
      box.classList.add("lf-aktiv-neu");
    }

    // OP-394: gerade-fertig -> Haekchen statt Spinner (5s-Grace)
    if (aktiv.gerade_fertig) {
      box.classList.add("lf-aktiv-fertig");
      var sym = document.createElement("span");
      sym.className = "lf-aktiv-sym";
      sym.textContent = "\u2713";
      box.appendChild(sym);
    } else {
      var sp = document.createElement("span");
      sp.className = "lf-spinner";
      var spChar = document.createElement("span");
      spChar.className = "lf-spinner-char";
      spChar.textContent = SPINNER[_spinnerIdx];
      sp.appendChild(spChar);
      box.appendChild(sp);
    }

    var rolle = document.createElement("span");
    rolle.className = "lf-aktiv-rolle";
    rolle.style.color = _rolleFarbe(aktiv.rolle);
    rolle.textContent = aktiv.rolle;
    box.appendChild(rolle);

    var aktion = document.createElement("span");
    aktion.className = "lf-aktiv-aktion lf-dots";
    aktion.textContent = aktiv.aktion || aktiv.kind || "";
    box.appendChild(aktion);

    var seit = document.createElement("span");
    seit.className = "lf-aktiv-seit";
    seit.textContent = _fmtSeit(aktiv.seit_s);
    box.appendChild(seit);

    _letzteAktiv = aktiv;
    _letzteAktivTs = Date.now();
    return box;
  }

  var EVENT_TITEL = {
    chat_job_queued: "Chat-Auftrag angenommen",
    chat_job_started: "Chat-Pruefung gestartet",
    chat_job_chunk: "Chat-Antwort",
    chat_job_tool_call: "Chat-Tool gestartet",
    chat_job_tool_result: "Chat-Tool abgeschlossen",
    chat_job_succeeded: "Chat-Antwort fertig",
    chat_job_failed: "Chat-Auftrag fehlgeschlagen",
    chat_job_cancelled: "Chat-Auftrag abgebrochen",
    chat_job_cancel_requested: "Chat-Abbruch angefordert",
    loop_started: "Run gestartet",
    loop_ended: "Run beendet",
    loop_failed: "Run fehlgeschlagen",
    loop_human_gate_rejected: "Freigabe abgelehnt",
    gate_expired: "Freigabe abgelaufen",
    loop_rollback_skipped: "Rollback übersprungen",
    loop_plan_gate_approved: "Plan freigegeben",
    loop_verify_ok: "Prüfung erfolgreich",
    loop_verify_failed: "Prüfung fehlgeschlagen"
  };

  function _lesbarerSchritt(step) {
    var detail = String(step.detail || "");
    var gate = detail.match(/gate=([a-z0-9_-]+)/i);
    var titel = EVENT_TITEL[step.kind] || "";
    if (gate && /rejected|abgelehnt/i.test(step.kind || "")) {
      titel = "Gate abgelehnt";
      detail = gate[1].replace(/_/g, " ");
    } else if (gate && detail.indexOf("grund=?") >= 0) {
      titel = "Gate: " + gate[1].replace(/_/g, " ");
      detail = "";
    }
    if (!detail) return titel || step.kind || "";
    if (titel && detail === step.kind) return titel;
    return detail;
  }

  function _renderStep(step, istNeu) {
    var row = document.createElement("div");
    row.className = "lf-step";
    if (istNeu) row.classList.add("lf-step-neu");
    if (step._just_finished) row.classList.add("lf-step-fertig");
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
    detail.textContent = _lesbarerSchritt(step);
    row.appendChild(detail);

    var stil = _statusStil(step.status);
    var sym = document.createElement("span");
    sym.className = "lf-step-sym " + stil.cls;
    sym.textContent = stil.symbol;
    row.appendChild(sym);

    var evidence = Array.isArray(step.evidence) ? step.evidence : [];
    var hasDetails = step.phase || step.task_id || step.result_summary ||
      step.decision_summary || step.next_step || evidence.length;
    if (hasDetails) {
      var details = document.createElement("details");
      details.className = "lf-step-more";
      details.addEventListener("click", function (event) {
        event.stopPropagation();
      });
      var summary = document.createElement("summary");
      summary.textContent = "Schrittdetails";
      details.appendChild(summary);

      function addDetail(label, value) {
        if (!value) return;
        var p = document.createElement("p");
        var strong = document.createElement("strong");
        strong.textContent = label + ": ";
        p.appendChild(strong);
        p.appendChild(document.createTextNode(String(value)));
        details.appendChild(p);
      }

      var kontext = [];
      if (step.phase) kontext.push("Phase " + step.phase);
      if (step.task_id || step.task_name) kontext.push("Task " + (step.task_id ? step.task_id + ": " : "") + (step.task_name || ""));
      addDetail("Kontext", kontext.join(" · "));
      addDetail("Ergebnis", step.result_summary);
      addDetail("Entscheidung", step.decision_summary);
      if (evidence.length) {
        var belegTitel = document.createElement("strong");
        belegTitel.textContent = "Belege";
        details.appendChild(belegTitel);
        var belegListe = document.createElement("ul");
        evidence.slice(0, 5).forEach(function (beleg) {
          if (typeof beleg !== "string" || !beleg.trim()) return;
          var item = document.createElement("li");
          item.textContent = beleg;
          belegListe.appendChild(item);
        });
        if (belegListe.childNodes.length) details.appendChild(belegListe);
      }
      addDetail("Nächster Schritt", step.next_step);
      row.appendChild(details);
    }

    row.addEventListener("click", function () {
      if (window.WerkstattDetail && window.WerkstattDetail.oeffneRolle) {
        window.WerkstattDetail.oeffneRolle(step.rolle || "loop");
      }
    });

    return row;
  }

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

    // Rollen-Wechsel: alte Aktiv-Rolle wird als Step eingefuegt
    var alteAktiv = _letzteAktiv;
    var neueAktiv = data.aktiv || {};
    var rolleGeandert = (
      alteAktiv && alteAktiv.rolle &&
      (!neueAktiv.rolle || neueAktiv.rolle !== alteAktiv.rolle)
    );

    var letzteIds = {};
    _letzteSteps.forEach(function (s) {
      letzteIds[(s.ts || "") + "|" + (s.kind || "")] = true;
    });

    // OP-394: Scroll-Position merken (Auto-Scroll ans Ende, wenn User
    // schon unten war — sonst respektiere seine Scroll-Position).
    var _warUnten = (
      container.scrollHeight - container.scrollTop - container.clientHeight
    ) < 40;

    container.innerHTML = "";

    var sichtbareSteps = (data.steps || []).slice();
    if (rolleGeandert && alteAktiv) {
      sichtbareSteps.unshift({
        ts: alteAktiv.start_ts || new Date().toISOString(),
        rolle: alteAktiv.rolle,
        kind: alteAktiv.kind || "",
        detail: alteAktiv.aktion || "",
        status: "ok",
        _just_finished: true,
      });
    }
    if (sichtbareSteps.length > STEPS_LIMIT) {
      sichtbareSteps = sichtbareSteps.slice(-STEPS_LIMIT);
    }

    var stepsBox = document.createElement("div");
    stepsBox.className = "lf-steps";
    if (sichtbareSteps.length === 0) {
      var leer = document.createElement("div");
      leer.className = "lf-leer";
      leer.textContent = "Keine Events f\u00fcr diesen Run.";
      stepsBox.appendChild(leer);
    } else {
      sichtbareSteps.forEach(function (s) {
        var istNeu = s._just_finished ||
          !letzteIds[(s.ts || "") + "|" + (s.kind || "")];
        stepsBox.appendChild(_renderStep(s, istNeu));
      });
    }
    container.appendChild(stepsBox);
    // OP-394: Aktiv-Block UNTEN (direkt nach Steps, vor Naechster) —
    // eine Leserichtung: oben Verlauf, unten Jetzt. Neuestes immer unten.
    container.appendChild(_renderAktiv(neueAktiv));

    var nx = _renderNaechster(data.naechster || {});
    if (nx) container.appendChild(nx);

    // OP-394: Auto-Scroll ans Ende — Aktiv-Block bleibt sichtbar.
    if (_warUnten) {
      container.scrollTop = container.scrollHeight;
    }

    _letzteSteps = data.steps || [];
  }

  function _lade(projekt) {
    if (projekt) _aktuellesProjekt = projekt;
    if (_overviewAktiv || !_aktuellesProjekt ||
        document.body.getAttribute("data-mode") !== "control") return;
    fetch("/api/projects/" + encodeURIComponent(_aktuellesProjekt) +
          "/live-feed?limit=30",
          {credentials: "same-origin"})
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) { if (d) _render(d); })
      .catch(function (err) { console.error("[live_feed]", err); });
  }

  function start(projekt) {
    if (projekt) _aktuellesProjekt = projekt;
    if (_overviewAktiv || !_aktuellesProjekt) return;
    if (_timer) clearInterval(_timer);
    _lade();
    _timer = setInterval(_lade, POLL_MS);
  }

  function stop() {
    if (_timer) clearInterval(_timer);
    _timer = null;
  }

  function setProjekt(projekt) {
    _overviewAktiv = false;
    _aktuellesProjekt = projekt || null;
    if (document.body.getAttribute("data-mode") === "control" && _aktuellesProjekt) {
      start(_aktuellesProjekt);
    } else {
      stop();
    }
  }

  function zeige_uebersicht() {
    _overviewAktiv = true;
    _aktuellesProjekt = null;
    stop();
  }

  document.addEventListener("werkstatt:mode-change", function (ev) {
    var m = ev.detail && ev.detail.mode;
    if (m === "control" && !_overviewAktiv && _aktuellesProjekt) {
      start();
      _startSpinner();
    } else {
      stop();
      _stopSpinner();
    }
  });

  document.addEventListener("DOMContentLoaded", function () {
    var tab = document.querySelector(".tab.ist-aktiv");
    if (tab && tab.dataset.projekt) {
      _overviewAktiv = false;
      _aktuellesProjekt = tab.dataset.projekt;
      if (document.body.getAttribute("data-mode") === "control") {
        start();
        _startSpinner();
      }
    } else {
      zeige_uebersicht();
    }
  });

  window.WerkstattLiveFeed = {
    start: start, stop: stop, lade: _lade,
    setProjekt: setProjekt, zeige_uebersicht: zeige_uebersicht
  };
})();
