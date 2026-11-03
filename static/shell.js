// PTY-Shell via xterm.js (Stellschraube 2026-11-04).
// Toggle: #shell-toggle wechselt zwischen Audit-Tail (#terminal) und
// xterm.js-Shell (#terminal-xterm). Shell wird beim ersten Klick
// verbunden, danach gehalten.

(function () {
  "use strict";

  // Stub SOFORT setzen, damit onclick garantiert funktioniert —
  // auch wenn spaetere Initialisierung crasht.
  window.WerkstattShell = {
    toggle: function () { console.warn("[shell] noch nicht bereit"); },
    verbinden: function () {},
    aktiv: function () { return false; },
  };

  var term = null;
  var fitAddon = null;
  var socket = null;
  var aktiv = false;
  var verbunden = false;

  function _init_xterm() {
    if (term) {
      return true;
    }
    if (!window.Terminal) {
      console.warn("[shell] init abgebrochen: kein Terminal");
      return false;
    }
    var el = document.getElementById("terminal-xterm");
    if (!el) {
      return false;
    }
    term = new window.Terminal({
      fontFamily: '"JetBrains Mono", "SF Mono", Consolas, monospace',
      fontSize: 12,
      theme: {
        background: "#1a1b1e",
        foreground: "#e4e4e7",
        cursor: "#4d6bfe",
        cursorAccent: "#1a1b1e",
        selectionBackground: "#4d6bfe",
        black: "#1a1b1e",
        red: "#ef4444",
        green: "#10b981",
        yellow: "#f59e0b",
        blue: "#4d6bfe",
        magenta: "#a78bfa",
        cyan: "#06b6d4",
        white: "#e4e4e7",
        brightBlack: "#4b5563",
        brightRed: "#f87171",
        brightGreen: "#34d399",
        brightYellow: "#fbbf24",
        brightBlue: "#60a5fa",
        brightMagenta: "#c4b5fd",
        brightCyan: "#22d3ee",
        brightWhite: "#f3f4f6",
      },
      cursorBlink: true,
      allowProposedApi: true,
      scrollback: 5000,
    });
    if (window.FitAddon && window.FitAddon.FitAddon) {
      fitAddon = new window.FitAddon.FitAddon();
      term.loadAddon(fitAddon);
    }
    // Search-Addon (Ctrl+F / History-Suche)
    if (window.SearchAddon && window.SearchAddon.SearchAddon) {
      try {
        term.loadAddon(new window.SearchAddon.SearchAddon());
      } catch (e) { console.warn("[shell] Search-Addon:", e); }
    }
    // WebLinks-Addon (URLs klickbar)
    if (window.WebLinksAddon && window.WebLinksAddon.WebLinksAddon) {
      try {
        term.loadAddon(new window.WebLinksAddon.WebLinksAddon());
      } catch (e) { console.warn("[shell] WebLinks-Addon:", e); }
    }
    term.open(el);
    if (fitAddon) {
      try { fitAddon.fit(); } catch (e) { /* ignore */ }
    }
    term.onData(function (data) {
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ typ: "input", data: data }));
      }
    });

    // Paste-Handling: xterm.js hat's default nur mit Clipboard-API-
    // Permission. Chrome/Safari in modernen Versionen blockieren das
    // oft. Wir fangen Ctrl+V/Cmd+V/Shift+Insert zusaetzlich ab und
    // lesen das Clipboard direkt.

    function _sende_paste(text) {
      if (!text) { return; }
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ typ: "input", data: text }));
      }
    }

    // Ctrl+V, Cmd+V, Shift+Insert abfangen
    term.attachCustomKeyEventHandler(function (ev) {
      if (ev.type !== "keydown") { return true; }
      // Ctrl+F: Search-Dialog (PowerShell-Feel: History durchsuchen)
      if ((ev.ctrlKey || ev.metaKey) && ev.key === "f" && !ev.shiftKey) {
        ev.preventDefault();
        var query = window.prompt("Search (History/Output):", "");
        if (query && term._searchAddon) {
          // Search-Addon unterstuetzt selectPreviousSearch mit default-Optionen
          try { term._searchAddon.findPrevious(query); } catch (e) {}
        }
        return false;
      }
      var is_paste = (
        ((ev.ctrlKey || ev.metaKey) && (ev.key === "v" || ev.key === "V"))
        || (ev.shiftKey && ev.key === "Insert")
      );
      if (!is_paste) { return true; }
      if (navigator.clipboard && navigator.clipboard.readText) {
        navigator.clipboard.readText().then(function (text) {
          _sende_paste(text);
        }).catch(function (e) {
          console.warn("[shell] clipboard read fehlgeschlagen:", e);
        });
      }
      // xterm.js default-Handler NICHT ausfuehren (wir haben paste
      // schon gesendet)
      return false;
    });

    // Browser paste-Event als Fallback (wenn Ctrl+V nicht intercepted)
    el.addEventListener("paste", function (ev) {
      var text = (ev.clipboardData || window.clipboardData).getData("text");
      if (text) {
        _sende_paste(text);
        ev.preventDefault();
      }
    });

    // Rechtsklick-Paste: Kontextmenue unterdruecken + Paste ausfuehren
    el.addEventListener("contextmenu", function (ev) {
      ev.preventDefault();
      if (navigator.clipboard && navigator.clipboard.readText) {
        navigator.clipboard.readText().then(function (text) {
          _sende_paste(text);
        }).catch(function (e) {
          console.warn("[shell] contextmenu-paste fehlgeschlagen:", e);
        });
      }
    });
    // Resize-Handler
    var resizeTimer = null;
    window.addEventListener("resize", function () {
      if (!aktiv) return;
      if (resizeTimer !== null) clearTimeout(resizeTimer);
      resizeTimer = setTimeout(function () {
        resizeTimer = null;
        _sende_resize();
      }, 100);
    });
    return true;
  }

  function _sende_resize() {
    if (!fitAddon || !term || !socket || socket.readyState !== WebSocket.OPEN) {
      return;
    }
    try { fitAddon.fit(); } catch (e) { return; }
    socket.send(JSON.stringify({
      typ: "resize",
      cols: term.cols,
      rows: term.rows,
    }));
  }

  function _verbinde() {
    if (socket && socket.readyState === WebSocket.OPEN) {
      return;
    }
    var protokoll = location.protocol === "https:" ? "wss:" : "ws:";
    socket = new WebSocket(protokoll + "//" + location.host + "/ws/shell");
    socket.onopen = function () {
      verbunden = true;
      if (term) {
        term.writeln("\x1b[90m[Werkstatt-Shell] \x1b[0mverbunden\r\n");
        _sende_resize();
      }
    };
    socket.onmessage = function (event) {
      if (term) {
        term.write(event.data);
      }
    };
    socket.onclose = function () {
      verbunden = false;
      if (term) {
        term.writeln("\r\n\x1b[90m[Werkstatt-Shell] \x1b[0mtrennen");
      }
    };
    socket.onerror = function () {
      verbunden = false;
      if (term) {
        term.writeln("\r\n\x1b[31m[Werkstatt-Shell] \x1b[0mfehler");
      }
    };
  }

  function _toggle(force) {
    var elXterm = document.getElementById("terminal-xterm");
    var elTail = document.getElementById("terminal");
    var btn = document.getElementById("shell-toggle");
    if (!elXterm || !elTail) {
      return;
    }
    if (force === true || (force === undefined && !aktiv)) {
      if (!_init_xterm()) {
        return;
      }
      elTail.hidden = true;
      elXterm.hidden = false;
      aktiv = true;
      if (btn) {
        btn.classList.add("ist-aktiv");
        btn.textContent = "\u25A3";
        btn.style.background = "#4d6bfe";
        btn.style.color = "#fff";
        btn.style.borderColor = "#4d6bfe";
      }
      if (!verbunden) {
        _verbinde();
      }
      // Bei Wieder-Öffnen: fit + resize + focus garantieren.
      // term existiert dann schon, aber fit()/resize muessen erneut
      // laufen weil das Element vorher hidden war (0x0 Layout).
      setTimeout(function () {
        if (fitAddon) {
          try { fitAddon.fit(); } catch (e) { console.warn("[shell] fit:", e); }
        }
        _sende_resize();
        if (term) {
          try { term.focus(); } catch (e) { console.warn("[shell] focus:", e); }
        }
        // Doppel-sicher: nochmal fit nach Browser-Reflow
        setTimeout(function () {
          if (fitAddon) { try { fitAddon.fit(); } catch (e) {} }
          _sende_resize();
        }, 200);
      }, 100);
    } else {
      elXterm.hidden = true;
      elTail.hidden = false;
      aktiv = false;
      if (btn) {
        btn.classList.remove("ist-aktiv");
        btn.textContent = "$";
        btn.style.background = "transparent";
        btn.style.color = "#9ca3af";
        btn.style.borderColor = "#2c2e33";
      }
    }
  }

  // Diagnose beim Laden: prueft was der Browser wirklich sieht
  document.addEventListener("DOMContentLoaded", function () {
    var diag = document.getElementById("shell-diag");
    var fehlt = [];
    if (!window.Terminal) fehlt.push("xterm.js");
    if (!window.FitAddon) fehlt.push("addon-fit");
    if (fehlt.length > 0) {
      var msg = "Fehlt: " + fehlt.join(", ");
      console.error("[shell] " + msg);
      if (diag) { diag.textContent = msg; }
    } else {
      console.log("[shell] geladen: xterm.js + addon-fit OK");
      if (diag) { diag.textContent = ""; }
    }
  });

  // Button komplett selbst erzeugen — kein HTML/CSS-Cache-Problem
  // mehr, keine Duplikate. Wird bei DOMContentLoaded eingefuegt.
  function _baue_button() {
    var container = document.getElementById("shell-toggle-container");
    if (!container) {
      console.error("[shell] #shell-toggle-container fehlt im HTML");
      return;
    }
    // Alten Button im Container loeschen (idempotent)
    container.innerHTML = "";
    var btn = document.createElement("button");
    btn.type = "button";
    btn.id = "shell-toggle";
    btn.textContent = "$";
    btn.title = "SSH-Shell oeffnen/schliessen";
    // Inline-Style: robust gegen CSS-Lade-Probleme
    btn.style.cssText =
      "padding:3px 10px;background:transparent;color:#9ca3af;" +
      "border:1px solid #2c2e33;border-radius:6px;cursor:pointer;" +
      "font-family:monospace;font-size:12px;font-weight:600;" +
      "line-height:1;pointer-events:auto;position:relative;z-index:100;";
    btn.addEventListener("mouseenter", function () {
      btn.style.color = "#e4e4e7";
      btn.style.borderColor = "#4d6bfe";
      btn.style.background = "rgba(77,107,254,0.12)";
    });
    btn.addEventListener("mouseleave", function () {
      if (aktiv) return;  // im aktiven Zustand nicht ueberschreiben
      btn.style.color = "#9ca3af";
      btn.style.borderColor = "#2c2e33";
      btn.style.background = "transparent";
    });
    btn.addEventListener("click", function (ev) {
      console.log("[shell] Button-Klick");
      ev.stopPropagation();
      _toggle();
    });
    container.appendChild(btn);
    console.log("[shell] Button erzeugt und eingefuegt");
  }

  document.addEventListener("DOMContentLoaded", function () {
    _baue_button();
  });

  window.WerkstattShell = {
    toggle: _toggle,
    verbinden: _verbinde,
    aktiv: function () { return aktiv; },
    baue_button: _baue_button,
  };
})();
