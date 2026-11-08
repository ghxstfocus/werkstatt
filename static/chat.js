// Werkstatt Chat (OP-232). Vanilla JS, kein Framework.
// Ein Panel pro Projekt, Session-Sidebar, Tool-Call-Karten,
// Streaming via WS /api/projects/{name}/chat/stream.
// API fuer tabs.js: window.WerkstattChat.setze_chat(projekt).

(function () {
  "use strict";

  var zustand = {
    projekt: "werkstatt",
    sessionId: null,
    socket: null,
    streamBuf: "",
    streamAktiv: false,
  };

  function _el(id) { return document.getElementById(id); }

  function _neueSession(projekt) {
    return fetch("/api/projects/" + encodeURIComponent(projekt) + "/chat/new",
                 {method: "POST", credentials: "same-origin"})
      .then(function (r) { return r.json(); })
      .then(function (d) {
        zustand.sessionId = d.session_id;
        return fetch("/api/projects/" + encodeURIComponent(projekt) +
                     "/chat/history?session_id=" + encodeURIComponent(d.session_id),
                     {credentials: "same-origin"})
          .catch(function () {})
          .then(function () { return d.session_id; });
      });
  }

  function _ladeSessions(projekt) {
    return fetch("/api/projects/" + encodeURIComponent(projekt) + "/chat/sessions",
                 {credentials: "same-origin"})
      .then(function (r) { return r.json(); })
      .then(function (d) { return d.sessions || []; });
  }

  function _ladeHistory(projekt, sid) {
    return fetch("/api/projects/" + encodeURIComponent(projekt) +
                 "/chat/history?session_id=" + encodeURIComponent(sid),
                 {credentials: "same-origin"})
      .then(function (r) { return r.json(); })
      .then(function (d) { return d.events || []; });
  }

  function _rendereSidebar(sessions) {
    var box = _el("chat-sessions");
    if (!box) return;
    box.innerHTML = "";
    sessions.forEach(function (sid) {
      var btn = document.createElement("button");
      btn.className = "chat-session" + (sid === zustand.sessionId ? " aktiv" : "");
      btn.textContent = sid.slice(0, 10);
      btn.dataset.sessionId = sid;
      btn.addEventListener("click", function () {
        _wechsleSession(sid);
      });
      box.appendChild(btn);
    });
    // Aktuelle Session, falls nicht in Liste (z.B. weil noch leer)
    if (zustand.sessionId && sessions.indexOf(zustand.sessionId) < 0) {
      var ghost = document.createElement("button");
      ghost.className = "chat-session aktiv";
      ghost.textContent = zustand.sessionId.slice(0, 10);
      ghost.dataset.sessionId = zustand.sessionId;
      ghost.addEventListener("click", function () {
        _wechsleSession(zustand.sessionId);
      });
      box.appendChild(ghost);
    }
  }

  function _renderSidebarAktuell() {
    _ladeSessions(zustand.projekt).then(_rendereSidebar);
  }

  function _wechsleSession(sid) {
    zustand.sessionId = sid;
    var titel = _el("chat-titel");
    if (titel) titel.textContent = "Chat · " + sid.slice(0, 8);
    var box = _el("chat-nachrichten");
    if (!box) return;
    box.innerHTML = "";
    _ladeHistory(zustand.projekt, sid).then(function (events) {
      events.forEach(function (ev) {
        var kind = ev.kind;
        var p = ev.payload || {};
        if (kind === "user") _karte("user", p.text || "");
        else if (kind === "assistant") _karte("assistant", p.text || "");
        else if (kind === "tool_call") {
          (p.tool_calls || []).forEach(function (tc) {
            _toolKarte(tc.function && tc.function.name || "?", null, "ok");
          });
        }
      });
    });
    _renderSidebarAktuell();
  }

  function _karte(rolle, text) {
    var box = _el("chat-nachrichten");
    if (!box) return null;
    var k = document.createElement("div");
    k.className = "chat-msg " + rolle;
    k.textContent = text;
    box.appendChild(k);
    box.scrollTop = box.scrollHeight;
    return k;
  }

  function _toolKarte(name, args, status) {
    var box = _el("chat-nachrichten");
    if (!box) return null;
    var k = document.createElement("details");
    k.className = "chat-tool " + status;
    var s = document.createElement("summary");
    s.textContent = "🔧 " + name + (status === "running" ? " …" : "");
    k.appendChild(s);
    if (args) {
      var pre = document.createElement("pre");
      pre.textContent = JSON.stringify(args, null, 2);
      k.appendChild(pre);
    }
    box.appendChild(k);
    box.scrollTop = box.scrollHeight;
    return k;
  }

  function _stelleToolErgebnis(name, inhalt) {
    var box = _el("chat-nachrichten");
    if (!box) return;
    var karten = box.querySelectorAll("details.chat-tool.running");
    for (var i = karten.length - 1; i >= 0; i--) {
      if (karten[i].querySelector("summary").textContent.indexOf(name) >= 0) {
        karten[i].classList.remove("running");
        karten[i].classList.add("ok");
        var pre = document.createElement("pre");
        pre.textContent = inhalt;
        karten[i].appendChild(pre);
        return;
      }
    }
  }

  function _socketVerbinde() {
    if (zustand.socket) {
      try { zustand.socket.close(); } catch (e) {}
    }
    var proto = location.protocol === "https:" ? "wss:" : "ws:";
    var url = proto + "//" + location.host + "/api/projects/" +
              encodeURIComponent(zustand.projekt) + "/chat/stream";
    var sock = new WebSocket(url);
    sock.addEventListener("message", _socketNachricht);
    sock.addEventListener("close", function () {
      zustand.socket = null;
      if (zustand.streamAktiv) {
        _karte("assistant", "[Verbindung unterbrochen]");
        zustand.streamAktiv = false;
      }
    });
    zustand.socket = sock;
  }

  function _socketNachricht(evt) {
    var obj;
    try { obj = JSON.parse(evt.data); } catch (e) { return; }
    if (obj.type === "chunk") {
      _streamChunk(obj.text || "");
    } else if (obj.type === "tool_call") {
      _toolKarte(obj.name || "?", obj.args, "running");
    } else if (obj.type === "tool_result") {
      _stelleToolErgebnis(obj.name || "?", obj.content || "");
    } else if (obj.type === "done") {
      _streamDone(obj.antwort || "");
    } else if (obj.type === "error") {
      _karte("assistant", "[Fehler] " + (obj.detail || "unbekannt"));
      zustand.streamAktiv = false;
    }
  }

  function _streamChunk(text) {
    if (!zustand.streamAktiv) {
      zustand.streamBuf = "";
      zustand.aktuelleKarte = _karte("assistant", "");
      zustand.streamAktiv = true;
    }
    zustand.streamBuf += text;
    if (zustand.aktuelleKarte) {
      zustand.aktuelleKarte.textContent = zustand.streamBuf;
      var box = _el("chat-nachrichten");
      if (box) box.scrollTop = box.scrollHeight;
    }
  }

  function _streamDone(voll) {
    if (!zustand.streamAktiv && voll) {
      _karte("assistant", voll);
    } else if (zustand.aktuelleKarte) {
      zustand.aktuelleKarte.textContent = voll || zustand.streamBuf;
    }
    zustand.streamAktiv = false;
    zustand.streamBuf = "";
    zustand.aktuelleKarte = null;
    _renderSidebarAktuell();
  }

  function _sende(text) {
    if (!text) return;
    if (!zustand.sessionId) {
      _neueSession(zustand.projekt).then(function () {
        _sende(text);
      });
      return;
    }
    _karte("user", text);
    if (!zustand.socket || zustand.socket.readyState !== WebSocket.OPEN) {
      _socketVerbinde();
      setTimeout(function () {
        _sendeUeberSocket(text);
      }, 150);
    } else {
      _sendeUeberSocket(text);
    }
  }

  function _sendeUeberSocket(text) {
    if (!zustand.socket || zustand.socket.readyState !== WebSocket.OPEN) {
      _karte("assistant", "[Verbindung nicht bereit]");
      return;
    }
    zustand.socket.send(JSON.stringify({
      session_id: zustand.sessionId,
      message: text,
      mode: "read",
    }));
  }

  function setze_chat(projekt) {
    if (!projekt) return;
    zustand.projekt = projekt;
    zustand.sessionId = null;
    zustand.socket = null;
    var titel = _el("chat-titel");
    if (titel) titel.textContent = "Chat — " + projekt;
    _renderSidebarAktuell();
    _ladeSessions(projekt).then(function (sessions) {
      if (sessions.length > 0) {
        _wechsleSession(sessions[sessions.length - 1]);
      }
    });
  }

  window.WerkstattChat = { setze_chat: setze_chat };

  document.addEventListener("DOMContentLoaded", function () {
    var form = _el("chat-form");
    var eingabe = _el("chat-eingabe");
    if (form) {
      form.addEventListener("submit", function (ev) {
        ev.preventDefault();
        if (!eingabe) return;
        var text = eingabe.value.trim();
        if (!text) return;
        eingabe.value = "";
        _sende(text);
      });
    }
    if (eingabe) {
      eingabe.addEventListener("keydown", function (ev) {
        if (ev.key === "Enter" && !ev.shiftKey && !ev.ctrlKey && !ev.metaKey) {
          ev.preventDefault();
          if (form) form.dispatchEvent(new Event("submit"));
        }
      });
      var _autoResize = function () {
        eingabe.style.height = "auto";
        eingabe.style.height = Math.min(eingabe.scrollHeight, 160) + "px";
      };
      eingabe.addEventListener("input", _autoResize);
    }

    // Header-Button: neue Session
    var neuBtn = _el("chat-neu");
    if (neuBtn) {
      neuBtn.addEventListener("click", function () {
        _neueSession(zustand.projekt).then(function () {
          var box = _el("chat-nachrichten");
          if (box) box.innerHTML = "";
          _renderSidebarAktuell();
        });
      });
    }
  });
})();
