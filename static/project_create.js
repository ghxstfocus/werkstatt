// OP-305: Projekt-Anlage-Modal (ersetzt prompt() auf + Button).
(function () {
  "use strict";

  function _el(id) { return document.getElementById(id); }

  function _oeffnen() {
    var ov = _el("project-create-overlay");
    if (!ov) return;
    ov.classList.add("offen");
    var nameEl = _el("project-create-name");
    var pfadEl = _el("project-create-pfad");
    if (nameEl) nameEl.value = "";
    if (pfadEl) pfadEl.value = "";
    var fehler = _el("project-create-fehler");
    if (fehler) fehler.hidden = true;
    if (nameEl) setTimeout(function () { nameEl.focus(); }, 50);
  }

  function _schliessen() {
    var ov = _el("project-create-overlay");
    if (!ov) return;
    ov.classList.remove("offen");
  }

  function _fehler(text) {
    var el = _el("project-create-fehler");
    if (!el) return;
    el.textContent = text;
    el.hidden = false;
  }

  function _autoPfad() {
    var nameEl = _el("project-create-name");
    var pfadEl = _el("project-create-pfad");
    if (!nameEl || !pfadEl) return;
    // User hat Pfad manuell editiert -> nicht ueberschreiben
    if (pfadEl.dataset.manuell === "1") return;
    var n = nameEl.value.trim();
    pfadEl.value = n ? "/opt/" + n : "";
  }

  function _anlegen() {
    var nameEl = _el("project-create-name");
    var pfadEl = _el("project-create-pfad");
    if (!nameEl || !pfadEl) {
      console.warn("[create] name/pfad el nicht gefunden");
      return;
    }
    var name = nameEl.value.trim();
    var pfad = pfadEl.value.trim();
    console.log("[create] _anlegen fired", {name: name, pfad: pfad});
    if (!name) { _fehler("Name fehlt"); return; }
    if (!/^[a-z][a-z0-9_-]{0,50}$/.test(name)) {
      _fehler("Name ungueltig: a-z, 0-9, _, - (beginnt mit Buchstabe)");
      return;
    }
    if (!pfad) { _fehler("Pfad fehlt"); return; }
    if (!pfad.startsWith("/opt/")) { _fehler("Pfad muss unter /opt/ liegen"); return; }

    var btn = _el("project-create-submit");
    if (btn) { btn.disabled = true; btn.textContent = "Lege an…"; }

    console.log("[create] fetch POST /api/projects/create", {name: name, pfad: pfad});
    fetch("/api/projects/create", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      credentials: "same-origin",
      body: JSON.stringify({name: name, pfad: pfad}),
    })
      .then(function (r) {
        return r.json().then(function (d) { return {ok: r.ok, data: d, status: r.status}; });
      })
      .then(function (res) {
        console.log("[create] response", {ok: res.ok, status: res.status, data: res.data});
        if (btn) { btn.disabled = false; btn.textContent = "Anlegen"; }
        if (!res.ok) {
          _fehler((res.data && res.data.detail) || (res.data && res.data.fehler) || ("HTTP " + res.status));
          return;
        }
        _schliessen();
        // OP-305: Tab oeffnen via neuer_tab (UI-Methode, nicht Store-Helper)
        if (!window.WerkstattTabs) {
          console.error("[create] WerkstattTabs nicht geladen — tabs.js fehlt oder gecacht");
          _fehler("UI-Fehler: bitte Strg+Shift+R (Hard-Reload)");
          return;
        }
        if (!window.WerkstattTabs.neuer_tab) {
          console.error("[create] neuer_tab nicht exportiert — tabs.js-Version veraltet");
          _fehler("UI veraltet: bitte Strg+Shift+R (Hard-Reload)");
          return;
        }
        try {
          window.WerkstattTabs.neuer_tab(name);
          console.log("[create] neuer_tab(name) aufgerufen für:", name);
        } catch (e) {
          console.error("[create] neuer_tab threw:", e);
          _fehler("Tab-Anlage fehlgeschlagen: " + e.message);
        }
      })
      .catch(function (err) {
        console.error("[create] catch", err);
        if (btn) { btn.disabled = false; btn.textContent = "Anlegen"; }
        _fehler("Netzwerkfehler: " + err);
      });
  }

  function _init() {
    // Ersetze + Button (klont um alte Handler zu entfernen)
    var neuBtn = _el("tab-neu");
    if (neuBtn) {
      var clone = neuBtn.cloneNode(true);
      neuBtn.parentNode.replaceChild(clone, neuBtn);
      clone.addEventListener("click", _oeffnen);
    }

    var closeBtn = _el("project-create-close");
    if (closeBtn) closeBtn.addEventListener("click", _schliessen);
    var cancelBtn = _el("project-create-cancel");
    if (cancelBtn) cancelBtn.addEventListener("click", _schliessen);
    var submitBtn = _el("project-create-submit");
    if (submitBtn) {
      submitBtn.addEventListener("click", _anlegen);
      console.log("[create] submit-Handler gebunden");
    } else {
      console.warn("[create] submit-btn nicht gefunden");
    }

    var ov = _el("project-create-overlay");
    if (ov) {
      ov.addEventListener("click", function (e) {
        if (e.target === ov) _schliessen();
      });
    }

    var nameEl = _el("project-create-name");
    if (nameEl) nameEl.addEventListener("input", _autoPfad);

    var pfadElInput = _el("project-create-pfad");
    if (pfadElInput) pfadElInput.addEventListener("input", function () {
      pfadElInput.dataset.manuell = "1";
    });

    // Enter im Name-Feld -> weiter zu Pfad; Enter im Pfad -> anlegen
    var pfadEl = _el("project-create-pfad");
    if (nameEl) nameEl.addEventListener("keydown", function (e) {
      if (e.key === "Enter") { e.preventDefault(); if (pfadEl) pfadEl.focus(); }
    });
    if (pfadEl) pfadEl.addEventListener("keydown", function (e) {
      if (e.key === "Enter") { e.preventDefault(); _anlegen(); }
      if (e.key === "Escape") { e.preventDefault(); _schliessen(); }
    });
  }

  window.WerkstattProjectCreate = {
    oeffnen: _oeffnen,
    schliessen: _schliessen,
  };

  document.addEventListener("DOMContentLoaded", _init);
})();
