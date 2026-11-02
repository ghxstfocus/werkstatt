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
})();
