// OP-302: Command Palette (Ctrl+K / Cmd+K).
(function () {
  "use strict";
  var aktuellesProjekt = "werkstatt";
  var _offen = false;
  var _treffer = [];
  var _aktiv = 0;
  var _letzterQuery = "";

  function _el(id) { return document.getElementById(id); }

  function _baseUrl() {
    return "/api/projects/" + encodeURIComponent(aktuellesProjekt) + "/palette";
  }

  function _icons() {
    return {
      action: "▸",
      nav: "→",
      op: "⚙",
      session: "◆",
      run: "↻",
    };
  }

  function _kategorieLabel(typ) {
    return {
      action: "Aktion",
      nav: "Navigation",
      op: "OP",
      session: "Session",
      run: "Run",
    }[typ] || typ;
  }

  function _flach(kategorien) {
    var out = [];
    ["actions", "ops", "sessions", "runs"].forEach(function (k) {
      (kategorien[k] || []).forEach(function (t) { out.push(t); });
    });
    return out;
  }

  function _rendere(liste) {
    var box = _el("palette-treffer");
    if (!box) return;
    box.innerHTML = "";
    if (!liste.length) {
      var lehre = document.createElement("div");
      lehre.className = "palette-leer";
      lehre.textContent = "Was willst du tun? (Tippe einen Suchbegriff)";
      box.appendChild(lehre);
      return;
    }
    var lastTyp = null;
    liste.forEach(function (t, i) {
      if (t.typ !== lastTyp) {
        var sep = document.createElement("div");
        sep.className = "palette-kategorie";
        sep.textContent = _kategorieLabel(t.typ);
        box.appendChild(sep);
        lastTyp = t.typ;
      }
      var row = document.createElement("div");
      row.className = "palette-treffer-zeile";
      if (i === _aktiv) row.classList.add("aktiv");
      row.dataset.idx = i;
      row.addEventListener("click", function () { _ausfuehren(t); });

      var icon = document.createElement("span");
      icon.className = "palette-icon";
      icon.textContent = _icons()[t.typ] || "·";
      row.appendChild(icon);

      var titel = document.createElement("span");
      titel.className = "palette-titel";
      titel.textContent = t.titel || "";
      row.appendChild(titel);

      if (t.untertitel) {
        var sub = document.createElement("span");
        sub.className = "palette-untertitel";
        sub.textContent = t.untertitel;
        row.appendChild(sub);
      }

      if (t.shortcut) {
        var sc = document.createElement("span");
        sc.className = "palette-shortcut";
        sc.textContent = t.shortcut;
        row.appendChild(sc);
      }

      box.appendChild(row);
    });
    _scrollAktiv();
  }

  function _scrollAktiv() {
    var aktiv = document.querySelector(".palette-treffer-zeile.aktiv");
    if (aktiv && aktiv.scrollIntoView) {
      aktiv.scrollIntoView({block: "nearest"});
    }
  }

  function _suche(q) {
    _letzterQuery = q;
    fetch(_baseUrl() + "?q=" + encodeURIComponent(q), {credentials: "same-origin"})
      .then(function (r) { return r.ok ? r.json() : {}; })
      .catch(function () { return {}; })
      .then(function (kategorien) {
        if (_letzterQuery !== q) return;  // Race-Schutz
        _treffer = _flach(kategorien || {});
        _aktiv = 0;
        _rendere(_treffer);
      });
  }

  function _ausfuehren(t) {
    if (!t) return;
    var base = "/api/projects/" + encodeURIComponent(aktuellesProjekt);
    if (t.action === "start_op" || t.action === "start_loop") {
      var body = t.action === "start_op" ? {op_id: (t.params || {}).op_id} : {};
      fetch(base + "/start", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        credentials: "same-origin",
        body: JSON.stringify(body),
      }).catch(function () {});
    } else if (t.action === "stop_loop") {
      fetch(base + "/stop", {method: "POST", credentials: "same-origin"})
        .catch(function () {});
    } else if (t.action === "open_tab") {
      var tab = (t.params || {}).tab || "audit";
      var btn = document.querySelector('.wb-tab[data-tab="' + tab + '"]');
      if (btn) btn.click();
    } else if (t.action === "open_session") {
      if (window.WerkstattChat && window.WerkstattChat.setze_chat) {
        window.WerkstattChat.setze_chat(aktuellesProjekt, (t.params || {}).session_id);
      }
    } else if (t.action === "open_run") {
      var btnTl = document.querySelector('.wb-tab[data-tab="terminal"]');
      if (btnTl) btnTl.click();
    } else if (t.action === "new_project") {
      var neuBtn = document.getElementById("tab-neu");
      if (neuBtn) neuBtn.click();
    }
    _schliessen();
  }

  function _oeffnen() {
    if (_offen) return;
    var overlay = _el("palette-overlay");
    if (!overlay) return;
    overlay.classList.add("offen");
    _offen = true;
    var input = _el("palette-input");
    if (input) {
      input.value = "";
      input.focus();
    }
    _suche("");
  }

  function _schliessen() {
    var overlay = _el("palette-overlay");
    if (!overlay) return;
    overlay.classList.remove("offen");
    _offen = false;
    _treffer = [];
    _aktiv = 0;
  }

  function _navRichtung(delta) {
    if (!_treffer.length) return;
    _aktiv = (_aktiv + delta + _treffer.length) % _treffer.length;
    _rendere(_treffer);
  }

  function _init() {
    var input = _el("palette-input");
    if (input) {
      input.addEventListener("input", function () { _suche(input.value); });
    }
    var overlay = _el("palette-overlay");
    if (overlay) {
      overlay.addEventListener("click", function (e) {
        if (e.target === overlay) _schliessen();
      });
    }
    document.addEventListener("keydown", function (e) {
      if ((e.ctrlKey || e.metaKey) && e.key === "k") {
        e.preventDefault();
        if (_offen) _schliessen();
        else _oeffnen();
      } else if (_offen && e.key === "Escape") {
        e.preventDefault();
        _schliessen();
      } else if (_offen && e.key === "ArrowDown") {
        e.preventDefault();
        _navRichtung(1);
      } else if (_offen && e.key === "ArrowUp") {
        e.preventDefault();
        _navRichtung(-1);
      } else if (_offen && e.key === "Enter") {
        e.preventDefault();
        if (_treffer[_aktiv]) _ausfuehren(_treffer[_aktiv]);
      }
    });
  }

  window.WerkstattPalette = {
    oeffnen: _oeffnen,
    schliessen: _schliessen,
    setze_projekt: function (p) { aktuellesProjekt = p; },
  };

  document.addEventListener("DOMContentLoaded", _init);
})();
