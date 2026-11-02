(function () {
  "use strict";

  const CHAT_IDS = ["admin", "bau"];
  const CHAT_LABELS = { admin: "Architect", bau: "Builder" };
  const API_BASIS = "/api/chat";
  const zustandProTab = {};
  let aktuellerChat = null;

  function holeTabZustand(tabId) {
    if (!zustandProTab[tabId]) {
      zustandProTab[tabId] = {
        admin: { maximiert: false, minimiert: false },
        bau: { maximiert: false, minimiert: false },
      };
    }
    return zustandProTab[tabId];
  }

  function layoutKlasse(tabId) {
    const zustand = holeTabZustand(tabId);
    const maximiert = CHAT_IDS.filter(function (chatId) {
      return zustand[chatId].maximiert;
    });
    if (maximiert.length === 1) {
      return { modus: "chat-focus", fokus: maximiert[0] };
    }
    return { modus: "chat-split", fokus: "" };
  }

  function bauePanel(tabId, chatId) {
    const zustand = holeTabZustand(tabId);
    const layout = layoutKlasse(tabId);

    const panel = document.createElement("section");
    panel.className = "chat-panel";
    panel.dataset.chatId = chatId;

    const kopf = document.createElement("div");
    kopf.className = "chat-panel__kopf";

    const titel = document.createElement("span");
    titel.className = "chat-panel__titel";
    titel.textContent = CHAT_LABELS[chatId];
    kopf.appendChild(titel);

    const aktionen = document.createElement("div");
    aktionen.className = "chat-panel__aktionen";

    const maxButton = document.createElement("button");
    maxButton.type = "button";
    maxButton.className = "chat-panel__button";
    maxButton.textContent = "\u25A2";
    maxButton.setAttribute("aria-label", "Chat maximieren");
    maxButton.addEventListener("click", function () {
      toggleMaximize(tabId, chatId);
    });
    aktionen.appendChild(maxButton);

    const minButton = document.createElement("button");
    minButton.type = "button";
    minButton.className = "chat-panel__button";
    minButton.textContent = "\u2013";
    minButton.setAttribute("aria-label", "Chat minimieren");
    minButton.addEventListener("click", function () {
      toggleMinimize(tabId, chatId);
    });
    aktionen.appendChild(minButton);

    kopf.appendChild(aktionen);
    panel.appendChild(kopf);

    const body = document.createElement("div");
    body.className = "chat-panel__body";
    panel.appendChild(body);

    const eingabe = document.createElement("div");
    eingabe.className = "chat-panel__eingabe";

    const textarea = document.createElement("textarea");
    textarea.className = "chat-panel__textarea";
    textarea.setAttribute("aria-label", "Nachricht an " + CHAT_LABELS[chatId]);
    eingabe.appendChild(textarea);

    const sendenButton = document.createElement("button");
    sendenButton.type = "button";
    sendenButton.className = "chat-panel__senden";
    sendenButton.textContent = "Senden";
    sendenButton.addEventListener("click", function () {
      sendeNachricht(tabId, chatId, textarea.value).then(function (ok) {
        if (ok) {
          textarea.value = "";
        }
      });
    });
    eingabe.appendChild(sendenButton);

    panel.appendChild(eingabe);

    if (zustand[chatId].minimiert) {
      panel.classList.add("chat-panel--minimiert");
    }
    if (layout.fokus === chatId) {
      panel.classList.add("chat-panel--fokus");
    }

    return panel;
  }

  function aktualisiereLayout(tabId, container) {
    const layout = layoutKlasse(tabId);
    container.classList.toggle("chat-split", layout.modus === "chat-split");
    container.classList.toggle("chat-focus", layout.modus === "chat-focus");

    const panels = container.querySelectorAll(".chat-panel");
    panels.forEach(function (panel) {
      const chatId = panel.dataset.chatId;
      panel.classList.toggle("chat-panel--fokus", layout.fokus === chatId);
      panel.classList.toggle(
        "chat-panel--minimiert",
        holeTabZustand(tabId)[chatId].minimiert
      );
    });
  }

  function renderChats(tabId, container) {
    if (!container) {
      return;
    }
    container.innerHTML = "";
    CHAT_IDS.forEach(function (chatId) {
      container.appendChild(bauePanel(tabId, chatId));
    });
    aktualisiereLayout(tabId, container);
  }

  function toggleMaximize(tabId, chatId) {
    const zustand = holeTabZustand(tabId);
    const neuerWert = !zustand[chatId].maximiert;
    CHAT_IDS.forEach(function (id) {
      zustand[id].maximiert = false;
    });
    zustand[chatId].maximiert = neuerWert;
    const container = document.querySelector(
      '[data-tab-id="' + tabId + '"] .chat-container'
    );
    if (container) {
      aktualisiereLayout(tabId, container);
    }
  }

  function toggleMinimize(tabId, chatId) {
    const zustand = holeTabZustand(tabId);
    zustand[chatId].minimiert = !zustand[chatId].minimiert;
    const container = document.querySelector(
      '[data-tab-id="' + tabId + '"] .chat-container'
    );
    if (container) {
      aktualisiereLayout(tabId, container);
    }
  }

  function sendeNachricht(tabId, chatId, text) {
    const inhalt = (text || "").trim();
    if (!inhalt) {
      return Promise.resolve(false);
    }
    return fetch(API_BASIS + "/" + encodeURIComponent(chatId), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tab: tabId, nachricht: inhalt }),
    })
      .then(function (antwort) {
        return antwort.ok;
      })
      .catch(function () {
        return false;
      });
  }

  function holeSendeButton() {
    return document.querySelector(".chat-panel__senden");
  }

  function holeNachrichtenfenster() {
    return document.querySelector(".chat-panel__body");
  }

  function haengeBlase(text, klasse) {
    const fenster = holeNachrichtenfenster();
    if (!fenster) {
      return;
    }
    const blase = document.createElement("div");
    blase.className = "chat-blase " + (klasse || "");
    blase.textContent = text;
    fenster.appendChild(blase);
  }

  function setze_chat(chat_id) {
    if (!chat_id) {
      schliesse();
      return;
    }
    aktuellerChat = chat_id;
    const fenster = holeNachrichtenfenster();
    if (fenster) {
      fenster.innerHTML = "";
    }
    const button = holeSendeButton();
    if (button) {
      button.disabled = false;
    }
  }

  function schliesse() {
    aktuellerChat = null;
    const button = holeSendeButton();
    if (button) {
      button.disabled = true;
    }
  }

  function sende() {
    const textarea = document.querySelector(".chat-panel__textarea");
    const eingabe = textarea ? textarea.value.trim() : "";
    if (!eingabe) {
      return Promise.resolve(false);
    }
    if (!aktuellerChat) {
      haengeBlase("Kein Chat ausgewaehlt.", "chat-blase--hinweis");
      return Promise.resolve(false);
    }
    haengeBlase(eingabe, "chat-blase--nutzer");
    if (textarea) {
      textarea.disabled = true;
    }
    return fetch("/api/chat/" + encodeURIComponent(aktuellerChat), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: eingabe }),
    })
      .then(function (response) {
        if (!response.ok) {
          haengeBlase(
            "Fehler: " + response.status,
            "chat-blase--fehler"
          );
          return false;
        }
        return response.json().then(function (antwort) {
          const inhalt =
            antwort.antwort ?? antwort.text ?? JSON.stringify(antwort);
          haengeBlase(inhalt, "chat-blase--antwort");
          if (textarea) {
            textarea.value = "";
          }
          return true;
        });
      })
      .catch(function () {
        haengeBlase("Fehler: Netzwerk", "chat-blase--fehler");
        return false;
      })
      .finally(function () {
        if (textarea) {
          textarea.disabled = false;
        }
      });
  }

  window.WerkstattChat = {
    renderChats: renderChats,
    toggleMaximize: toggleMaximize,
    toggleMinimize: toggleMinimize,
    sendeNachricht: sendeNachricht,
    holeTabZustand: holeTabZustand,
    setze_chat: setze_chat,
    schliesse: schliesse,
    sende: sende,
  };
})();

// Init (Stellschraube 2026-11-03): Chat bei DOMContentLoaded initialisieren.
(function () {
  function _initChat() {
    if (typeof window === "undefined") return;
    if (!window.WerkstattChat) {
      console.warn("[chat] window.WerkstattChat nicht gesetzt");
      return;
    }
    // Chat-Fenster in den #chat-nachrichten-Container mounten, falls API vorhanden
    var mountFn = window.WerkstattChat.mount || window.WerkstattChat.init;
    if (typeof mountFn === "function") {
      try {
        mountFn();
        console.log("[chat] mount ok");
      } catch (e) {
        console.error("[chat] mount fehler:", e);
      }
    } else if (typeof window.WerkstattChat.setze_chat === "function") {
      // Fallback: nur setze_chat, Panel bleibt DOM-still.
      console.log("[chat] setze_chat vorhanden, kein mount");
    } else {
      console.warn("[chat] keine mount/setze_chat-API");
    }
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", _initChat);
  } else {
    _initChat();
  }
})();

