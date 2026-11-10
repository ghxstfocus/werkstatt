(function () {
  "use strict";

  var vorlage = document.getElementById("tab-vorlage");
  var leiste = document.getElementById("tab-leiste");
  var neuBtn = document.getElementById("tab-neu");
  var zaehler = 0;
  var aktiverTabId = null;
  var tabDaten = {};  // tabId -> { projekt, terminal: [], chat: [], audit: [] }
  // Neue Store-API parallel zu den alten Handlern.
  // Wird von wechsle/schliesse/neuerTab aufgerufen.
  var _zustand = null;  // spaet initialisiert

  // OP-306a: Tab-Persistenz in localStorage (versioniert, validiert, debounced)
  var PERSIST_KEY = "werkstatt-tabs:v1";
  var _rehydriere_laeuft = false;
  var _persist_timer = null;


  // OP-306a: Persistenz-Helfer
  function _persistiere_tabs() {
    if (_rehydriere_laeuft) { return; }
    if (_persist_timer !== null) { return; }
    _persist_timer = setTimeout(function () {
      _persist_timer = null;
      try {
        var eintraege = [];
        var knoten = document.querySelectorAll(".tab");
        for (var i = 0; i < knoten.length; i++) {
          var tid = knoten[i].dataset.tabId;
          var d = tabDaten[tid];
          if (!d) { continue; }
          if (typeof d.projekt !== "string" || d.projekt.length === 0) { continue; }
          eintraege.push({projekt: d.projekt, aktiv: tid === aktiverTabId});
        }
        if (eintraege.length === 0) {
          localStorage.removeItem(PERSIST_KEY);
        } else {
          localStorage.setItem(PERSIST_KEY, JSON.stringify(eintraege));
        }
      } catch (e) { /* localStorage nicht verfuegbar */ }
    }, 50);
  }

  function _lade_gespeicherte_tabs() {
    try {
      var raw = localStorage.getItem(PERSIST_KEY);
      if (!raw) { return []; }
      var arr = JSON.parse(raw);
      if (!Array.isArray(arr)) { return []; }
      var sauber = [];
      for (var i = 0; i < arr.length; i++) {
        var e = arr[i];
        if (!e) { continue; }
        if (typeof e.projekt !== "string" || e.projekt.length === 0) { continue; }
        sauber.push({projekt: e.projekt, aktiv: e.aktiv === true});
      }
      return sauber;
    } catch (err) {
      return [];
    }
  }

  function neuerTab(projekt) {
    var klon = vorlage.content.cloneNode(true);
    var btn = klon.querySelector(".tab");
    var titel = klon.querySelector(".tab-titel");
    var schliessen = klon.querySelector(".tab-schliessen");
    var id = "tab-" + (++zaehler);

    btn.dataset.tabId = id;
    btn.dataset.projekt = projekt;
    titel.textContent = projekt;

    btn.addEventListener("click", function () {
      wechsle(id);
    });
    schliessen.addEventListener("click", function (ev) {
      ev.stopPropagation();
      schliesse(id);
    });

    var _neuBtnLive = document.getElementById("tab-neu");
    if (_neuBtnLive && _neuBtnLive.parentNode === leiste) {
      leiste.insertBefore(klon, _neuBtnLive);
    } else {
      leiste.appendChild(klon);
    }

    tabDaten[id] = {
      projekt: projekt,
      terminal: [],
      chat: [],
      audit: [],
    };
    // Store-API: Tab oeffnen (Kanal reservieren)
    if (_zustand) {
      try {
        window.WerkstattTabs.oeffne_tab(_zustand, projekt, projekt);
      } catch (e) { /* Store-API optional */ }
    }
    _persistiere_tabs();
    return id;
  }

  var _uebersichtAktiv = false;

  function _zeigeUebersicht() {
    _uebersichtAktiv = true;
    var screen = document.getElementById("overview-screen");
    var workspace = document.getElementById("projekt-workspace");
    var home = document.getElementById("tab-home");
    if (screen) screen.hidden = false;
    if (workspace) workspace.hidden = true;
    if (home) home.setAttribute("aria-pressed", "true");
    if (window.WerkstattAmbient && window.WerkstattAmbient.zeige_uebersicht) {
      window.WerkstattAmbient.zeige_uebersicht();
    }
    ["WerkstattRuns", "WerkstattTimeline", "WerkstattWaterfall", "WerkstattLiveFeed"].forEach(function (name) {
      var panel = window[name];
      if (panel && panel.zeige_uebersicht) panel.zeige_uebersicht();
    });
    if (window.WerkstattStatus && window.WerkstattStatus.zeige_uebersicht) {
      window.WerkstattStatus.zeige_uebersicht();
    }
    if (window.WerkstattOverview && window.WerkstattOverview.lade) {
      window.WerkstattOverview.lade();
    }
  }

  function _zeigeProjektbereich() {
    _uebersichtAktiv = false;
    var screen = document.getElementById("overview-screen");
    var workspace = document.getElementById("projekt-workspace");
    var home = document.getElementById("tab-home");
    if (screen) screen.hidden = true;
    if (workspace) workspace.hidden = false;
    if (home) home.setAttribute("aria-pressed", "false");
  }

  var homeBtn = document.getElementById("tab-home");
  if (homeBtn) {
    homeBtn.addEventListener("click", _zeigeUebersicht);
  }

  function wechsle(tabId) {
    if (!tabDaten[tabId]) {
      return;
    }
    _zeigeProjektbereich();
    aktiverTabId = tabId;
    _persistiere_tabs();
    document.querySelectorAll(".tab").forEach(function (t) {
      t.classList.toggle("ist-aktiv", t.dataset.tabId === tabId);
    });
    var daten = tabDaten[tabId];

    // Loop-Log hat keinen Titel mehr (Terminal->Loop-Log Umbau), skip
    var ambProj = document.getElementById("ambient-project-name");
    if (ambProj) ambProj.textContent = daten.projekt;
    var chatTitel = document.getElementById("chat-titel");
    if (chatTitel) chatTitel.textContent = "Chat — " + daten.projekt;

    rendereListe("terminal", daten.terminal);
    rendereListe("chat-nachrichten", daten.chat);
    rendereListe("audit-live", daten.audit);

    // Panel-Verbindungen oeffnen (OP-083 Wiring 2026-11-03)
    try {
      if (window.WerkstattTerminal && window.WerkstattTerminal.oeffne) {
        window.WerkstattTerminal.oeffne(daten.projekt);
      }
      if (window.WerkstattAudit && window.WerkstattAudit.oeffne) {
        window.WerkstattAudit.oeffne(daten.projekt);
      }
      if (window.WerkstattChat && window.WerkstattChat.setze_chat) {
        window.WerkstattChat.setze_chat(daten.projekt);
      }
      if (window.WerkstattRuns && window.WerkstattRuns.lade) {
        window.WerkstattRuns.lade(daten.projekt);
      }
      if (window.WerkstattTimeline && window.WerkstattTimeline.lade) {
        window.WerkstattTimeline.lade(daten.projekt);
      }
      if (window.WerkstattWaterfall && window.WerkstattWaterfall.setProjekt) {
        window.WerkstattWaterfall.setProjekt(daten.projekt);
      }
      if (window.WerkstattLiveFeed && window.WerkstattLiveFeed.setProjekt) {
        window.WerkstattLiveFeed.setProjekt(daten.projekt);
      }
      if (window.WerkstattStatus && window.WerkstattStatus.lade) {
        window.WerkstattStatus.lade(daten.projekt);
      }
      if (window.WerkstattWorkbench && window.WerkstattWorkbench.setProjekt) {
        window.WerkstattWorkbench.setProjekt(daten.projekt);
      }
      if (window.WerkstattGate && window.WerkstattGate.lade) {
        window.WerkstattGate.lade(daten.projekt);
      }
      if (window.WerkstattDetail && window.WerkstattDetail.setProjekt) {
        window.WerkstattDetail.setProjekt(daten.projekt);
      }
    } catch (e) { /* Panels optional */ }
  }

  function schliesse(tabId) {
    // Panel-Verbindungen schliessen bevor Tab weg
    try {
      if (window.WerkstattTerminal && window.WerkstattTerminal.schliesse) {
        window.WerkstattTerminal.schliesse();
      }
      if (window.WerkstattAudit && window.WerkstattAudit.schliesse) {
        window.WerkstattAudit.schliesse();
      }
    } catch (e) { /* Panels optional */ }
    var btn = document.querySelector('.tab[data-tab-id="' + tabId + '"]');
    if (btn) {
      btn.remove();
    }
    delete tabDaten[tabId];
    if (aktiverTabId === tabId) {
      var erste = document.querySelector(".tab");
      if (erste) {
        wechsle(erste.dataset.tabId);
      } else {
        aktiverTabId = null;
        _zeigeUebersicht();
      }
    }
    _persistiere_tabs();
  }

  function rendereListe(zielId, eintraege) {
    var ziel = document.getElementById(zielId);
    if (!ziel) {
      return;
    }
    ziel.textContent = "";
    eintraege.forEach(function (text) {
      var div = document.createElement("div");
      div.textContent = text;
      ziel.appendChild(div);
    });
    ziel.scrollTop = ziel.scrollHeight;
  }

  // OP-305: Der + Button wird in project_create.js geklont und bekommt
  // dort einen Modal-Handler. Alter prompt() entfernt — kein Doppel-Handler.

  // Chat-Form: Text anhaengen
  var chatForm = document.getElementById("chat-form");

  // History-Sidebar
  var sidebar = document.getElementById("history-sidebar");
  var toggle = document.getElementById("history-toggle");
  var close = document.getElementById("history-close");
  if (toggle && sidebar) {
    toggle.addEventListener("click", function () {
      sidebar.classList.toggle("ist-offen");
    });
  }
  if (close && sidebar) {
    close.addEventListener("click", function () {
      sidebar.classList.remove("ist-offen");
    });
  }

  // Store-API initialisieren
  if (window.WerkstattTabs && window.WerkstattTabs.neuer_zustand) {
    try {
      _zustand = window.WerkstattTabs.neuer_zustand({
        hole_kanal: function() { return null; },
        neuer_kanal: function(p) { return p; },
        schliesse_kanal: function() {},
      });
    } catch (e) { _zustand = null; }
  }

  // OP-306a: Rehydration aus localStorage mit Default-Fallback
  var _gespeicherte = _lade_gespeicherte_tabs();
  if (_gespeicherte.length === 0) {
    _zeigeUebersicht();
  } else {
    _rehydriere_laeuft = true;
    var _aktiverId = null;
    for (var _i = 0; _i < _gespeicherte.length; _i++) {
      var _tid = neuerTab(_gespeicherte[_i].projekt);
      if (_gespeicherte[_i].aktiv) { _aktiverId = _tid; }
    }
    _rehydriere_laeuft = false;
    if (_aktiverId !== null) {
      wechsle(_aktiverId);
    } else {
      var _erste = document.querySelector(".tab");
      if (_erste) { wechsle(_erste.dataset.tabId); }
    }
    _persistiere_tabs();
  }

  // ============================================================
  // Store-API (Drift-Guard gegen tests/test_ui_layout.py::Spiegel)
  // Reine Zustandsfunktionen, kein DOM-Zugriff.
  // ============================================================

  function neuer_zustand(fabrik) {
    return {
      fabrik: fabrik,
      tabs: {},
      reihenfolge: [],
      aktiv: null,
      kanaele: {},  // projekt -> refcount
    };
  }

  function kanal_holen(zustand, projekt) {
    var vorhanden = zustand.fabrik.hole_kanal(projekt);
    if (vorhanden) {
      zustand.kanaele[projekt] = (zustand.kanaele[projekt] || 0) + 1;
      return vorhanden;
    }
    var kanal = zustand.fabrik.neuer_kanal(projekt);
    zustand.kanaele[projekt] = 1;
    return kanal;
  }

  function kanal_freigeben(zustand, projekt) {
    var anzahl = zustand.kanaele[projekt] || 0;
    if (anzahl <= 1) {
      delete zustand.kanaele[projekt];
      if (zustand.fabrik && typeof zustand.fabrik.schliesse_kanal === "function") {
        zustand.fabrik.schliesse_kanal(projekt);
      }
      return false;
    }
    zustand.kanaele[projekt] = anzahl - 1;
    return true;
  }

  function oeffne_tab(zustand, projekt, titel) {
    var id = "tab-" + (Object.keys(zustand.tabs).length + 1);
    zustand.tabs[id] = {
      id: id,
      projekt: projekt,
      titel: titel || projekt,
    };
    zustand.reihenfolge.push(id);
    kanal_holen(zustand, projekt);
    return zustand.tabs[id];
  }

  function _tab_ressourcen_schliessen(tab) {
    if (!tab) {
      return;
    }
    if (tab.typ === "terminal") {
      window.WerkstattTerminal?.schliesse?.();
    } else if (tab.typ === "audit") {
      window.WerkstattAudit?.schliesse?.();
    } else if (tab.typ === "chat") {
      window.WerkstattChat?.schliesse?.();
    }
  }

  function _tab_ressourcen_oeffnen(tab) {
    if (!tab) {
      return;
    }
    if (tab.typ === "terminal") {
      window.WerkstattTerminal?.oeffne?.(tab.projekt);
    } else if (tab.typ === "audit") {
      window.WerkstattAudit?.oeffne?.(tab.projekt);
    } else if (tab.typ === "chat") {
      window.WerkstattChat?.setze_chat?.(tab.chat_id);
    }
  }

  function wechsle_tab(zustand, tabId) {
    if (!zustand.tabs[tabId]) {
      return false;
    }
    var vorher = zustand.aktiv ? zustand.tabs[zustand.aktiv] : null;
    // OP-083: erst schliessen
    _tab_ressourcen_schliessen(vorher);
    zustand.aktiv = tabId;
    // OP-083: dann oeffnen
    _tab_ressourcen_oeffnen(zustand.tabs[tabId]);
    return true;
  }

  function schliesse_tab(zustand, tabId) {
    var tab = zustand.tabs[tabId];
    if (!tab) {
      return false;
    }
    var war_aktiv = zustand.aktiv === tabId;
    kanal_freigeben(zustand, tab.projekt);
    delete zustand.tabs[tabId];
    zustand.reihenfolge = zustand.reihenfolge.filter(function (x) {
      return x !== tabId;
    });
    if (war_aktiv) {
      zustand.aktiv = zustand.reihenfolge[0] || null;
      _tab_ressourcen_schliessen(tab);
      if (zustand.aktiv) {
        _tab_ressourcen_oeffnen(zustand.tabs[zustand.aktiv]);
      }
    }
    return true;
  }

  function synchronisiere(zustand) {
    var aktiv = zustand.aktiv ? zustand.tabs[zustand.aktiv] : null;
    return {
      tabs: Object.keys(zustand.tabs),
      aktiv: zustand.aktiv,
      projekt: aktiv ? aktiv.projekt : null,
    };
  }

  // Export fuer Drift-Guard (Python-Spiegelung) und externe Nutzung
  function neuer_tab(name) {
    // OP-305: Oeffentliche UI-Methode — neuen Tab anlegen + aktivieren.
    var id = neuerTab(name);
    wechsle(id);
    return id;
  }

  function oeffne_projekt(name) {
    var ids = Object.keys(tabDaten);
    for (var i = 0; i < ids.length; i++) {
      if (tabDaten[ids[i]].projekt === name) {
        wechsle(ids[i]);
        return ids[i];
      }
    }
    return neuer_tab(name);
  }

  window.WerkstattTabs = {
    neuer_zustand: neuer_zustand,
    kanal_holen: kanal_holen,
    kanal_freigeben: kanal_freigeben,
    oeffne_tab: oeffne_tab,
    neuer_tab: neuer_tab,
    oeffne_projekt: oeffne_projekt,
    wechsle_tab: wechsle_tab,
    schliesse_tab: schliesse_tab,
    synchronisiere: synchronisiere,
  };

})();