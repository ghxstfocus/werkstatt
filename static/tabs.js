(function () {
  "use strict";

  var vorlage = document.getElementById("tab-vorlage");
  var leiste = document.getElementById("tab-leiste");
  var neuBtn = document.getElementById("tab-neu");
  var zaehler = 0;
  var aktiverTabId = null;
  var tabDaten = {};  // tabId -> { projekt, terminal: [], chat: [], audit: [] }

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

    rendereListe("terminal-scrollback", daten.terminal);
    rendereListe("chat-nachrichten", daten.chat);
    rendereListe("audit-live", daten.audit);
  }

  function schliesse(tabId) {
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
  if (chatForm) {
    chatForm.addEventListener("submit", function (ev) {
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
      tabDaten[aktiverTabId].chat.push("(Demo: Chat-Backend noch nicht verdrahtet)");
      eingabe.value = "";
      rendereListe("chat-nachrichten", tabDaten[aktiverTabId].chat);
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