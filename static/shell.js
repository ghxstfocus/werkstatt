// PTY-Shell via xterm.js (Stellschraube 2026-11-04).
// Toggle: #shell-toggle wechselt zwischen Audit-Tail (#terminal) und
// xterm.js-Shell (#terminal-xterm). Shell wird beim ersten Klick
// verbunden, danach gehalten.

(function () {
  "use strict";

  var term = null;
  var fitAddon = null;
  var socket = null;
  var aktiv = false;
  var verbunden = false;

  function _init_xterm() {
    if (term || !window.Terminal) {
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
    term.open(el);
    if (fitAddon) {
      try { fitAddon.fit(); } catch (e) { /* ignore */ }
    }
    term.onData(function (data) {
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ typ: "input", data: data }));
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
      }
      if (!verbunden) {
        _verbinde();
      }
      setTimeout(function () {
        if (fitAddon) { try { fitAddon.fit(); } catch (e) {} }
        _sende_resize();
        if (term) { try { term.focus(); } catch (e) {} }
      }, 100);
    } else {
      elXterm.hidden = true;
      elTail.hidden = false;
      aktiv = false;
      if (btn) {
        btn.classList.remove("ist-aktiv");
        btn.textContent = "$";
      }
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    var btn = document.getElementById("shell-toggle");
    if (btn) {
      btn.addEventListener("click", function () { _toggle(); });
    }
  });

  window.WerkstattShell = {
    toggle: _toggle,
    verbinden: _verbinde,
    aktiv: function () { return aktiv; },
  };
})();
