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

    leiste.insertBefore(klon, neuBtn);

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
    return id;
  }

  function wechsle(tabId) {
    if (!tabDaten[tabId]) {
      return;
    }
    aktiverTabId = tabId;
    document.querySelectorAll(".tab").forEach(function (t) {
      t.classList.toggle("ist-aktiv", t.dataset.tabId === tabId);
    });
    var daten = tabDaten[tabId];

    document.getElementById("terminal-titel").textContent =
      "Terminal — " + daten.projekt;
    document.getElementById("chat-titel").textContent =
      "Chat — " + daten.projekt;

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
      if (window.WerkstattStatus && window.WerkstattStatus.lade) {
        window.WerkstattStatus.lade(daten.projekt);
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
      }
    }
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

  // Neuer Tab
  neuBtn.addEventListener("click", function () {
    var name = window.prompt("Projekt-Name:", "werkstatt");
    if (name) {
      var id = neuerTab(name);
      wechsle(id);
    }
  });

  // Chat-Form: Text anhaengen
  var chatForm = document.getElementById("chat-form");
  if (false) {  // deaktiviert: chat.js übernimmt Form (OP-084)    chatForm.addEventListener("submit", function (ev) {
      ev.preventDefault();
      if (!aktiverTabId) {
        return;
      }
      var eingabe = document.getElementById("chat-eingabe");
      var text = eingabe.value.trim();
      if (!text) {
        return;
      }
      tabDaten[aktiverTabId].chat.push("> " + text);

      eingabe.value = "";

      rendereListe("chat-nachrichten", tabDaten[aktiverTabId].chat);

      var _chatId = "admin";

      var _tabId = aktiverTabId;

      fetch("/api/chat/" + encodeURIComponent(_chatId), {

        method: "POST",

        headers: { "Content-Type": "application/json" },

        body: JSON.stringify({ tab_id: _tabId, nachricht: text }),

      })

        .then(function (r) { return r.json().catch(function () { return {}; }); })

        .then(function (daten) {

          var antwort = daten.antwort || daten.message || "(leer)";

          if (tabDaten[_tabId]) {

            tabDaten[_tabId].chat.push("< " + antwort);

            if (aktiverTabId === _tabId) {

              rendereListe("chat-nachrichten", tabDaten[_tabId].chat);

            }

          }

        })

        .catch(function (err) {

          if (tabDaten[_tabId]) {

            tabDaten[_tabId].chat.push("! Fehler: " + err);

            if (aktiverTabId === _tabId) {

              rendereListe("chat-nachrichten", tabDaten[_tabId].chat);

            }

          }

        });
    });
    document.getElementById("chat-eingabe").addEventListener("keydown", function (ev) {
      if (ev.key === "Enter" && ev.ctrlKey) {
        chatForm.dispatchEvent(new Event("submit"));
      }
    });
  }

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

  // Start: ein Demo-Tab
  var startId = neuerTab("werkstatt");
  wechsle(startId);

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
  window.WerkstattTabs = {
    neuer_zustand: neuer_zustand,
    kanal_holen: kanal_holen,
    kanal_freigeben: kanal_freigeben,
    oeffne_tab: oeffne_tab,
    wechsle_tab: wechsle_tab,
    schliesse_tab: schliesse_tab,
    synchronisiere: synchronisiere,
  };

})();