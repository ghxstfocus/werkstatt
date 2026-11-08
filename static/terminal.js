// Browser-Client fuer das Terminal-Panel.
// Reine String-Rueckgabe in formatiereEvent, kein DOM-Zugriff dort.

function formatiereEvent(event) {
  const ts = event.ts || "";
  const prefix = ts ? `[${ts}] ` : "";

  if (event.type === "spinner") {
    const label = event.label || "";
    const detail = event.detail || "";
    const state = event.state || "";
    return `${label} ${detail} ${state}`.trim();
  }

  if (event.type === "task_started") {
    return `${prefix}▶ Task ${event.nr}/${event.total}: ${event.name}`;
  }

  if (event.type === "task_done") {
    if (event.ok === true) {
      return `${prefix}✔ ${event.name || ""}`.trim();
    }
    return `${prefix}✖ ${event.name || ""} (${event.reason || ""})`.trim();
  }

  if (event.type === "summary") {
    return `${prefix}— Summary: ${event.success}, ${event.tasks_ok}/${event.tasks_total}`;
  }

  return `${prefix}${event.text || ""}`;
}

function haengeZeileAn(text) {
  const pre = document.getElementById("loop-log");
  if (!pre) {
    return;
  }
  pre.appendChild(document.createTextNode(text + "\n"));
  while (pre.childNodes.length > 5000) {
    pre.removeChild(pre.firstChild);
  }
  pre.scrollTop = pre.scrollHeight;
}

function haengeSpinnerAn(text) {
  const spinner = document.getElementById("loop-log-status");
  if (!spinner) {
    return;
  }
  spinner.textContent = text;
}

function verbindeTerminal(project, options) {
  const opts = options || {};
  const protokoll = window.location.protocol === "https:" ? "wss:" : "ws:";
  const url = `${protokoll}//${window.location.host}/ws/terminal/${encodeURIComponent(project)}`;
  let versuche = 0;
  let geschlossen = false;
  let ws = null;

  function oeffne() {
    ws = new WebSocket(url);

    ws.onmessage = function (event) {
      let daten;
      try {
        daten = JSON.parse(event.data);
      } catch (err) {
        console.error("terminal: ungueltiges JSON", err);
        return;
      }
      const text = formatiereEvent(daten);
      if (daten && daten.type === "spinner") {
        haengeSpinnerAn(text);
      } else {
        haengeZeileAn(text);
      }
    };

    ws.onclose = function () {
      if (geschlossen) {
        return;
      }
      const wartezeit = Math.min(10000, 1000 * 2 ** versuche);
      versuche += 1;
      setTimeout(oeffne, wartezeit);
    };

    ws.onerror = function (err) {
      console.error("terminal: websocket fehler", err);
    };
  }

  oeffne();

  return {
    schliesse: function () {
      geschlossen = true;
      if (ws) {
        ws.onclose = null;
        ws.close();
      }
    },
  };
}

let socket = null;
let aktuellesProjekt = null;
let zeilenZaehler = 0;

function rendereEvent(daten) {
  let event = daten;
  if (daten && daten.typ === "audit" && daten.event) {
    event = daten.event;
  }
  let text;
  if (event && event.typ === "log") {
    text = event.text || "";
  } else if (event && (event.text || event.zeile)) {
    text = event.text || event.zeile;
  } else {
    text = JSON.stringify(event);
  }
  haengeZeileAn(text);
  zeilenZaehler += 1;
}

function schliesse() {
  if (socket) {
    socket.onmessage = null;
    if (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING) {
      socket.close(1000, "tab-wechsel");
    }
    socket = null;
  }
  aktuellesProjekt = null;
  zeilenZaehler = 0;
}

function oeffne(project) {
  if (
    socket &&
    aktuellesProjekt === project &&
    socket.readyState === WebSocket.OPEN
  ) {
    return;
  }
  schliesse();
  aktuellesProjekt = project;
  const protokoll = location.protocol === "https:" ? "wss:" : "ws:";
  socket = new WebSocket(
    `${protokoll}//${location.host}/ws/terminal/${encodeURIComponent(project)}`
  );
  socket.onmessage = function (event) {
    let daten;
    try {
      daten = JSON.parse(event.data);
    } catch (err) {
      console.error("terminal: ungueltiges JSON", err);
      return;
    }
      // Render-Zeile: direkt anzeigen, kein JSON-Parsing
      if (daten && daten.typ === "render") {
        haengeZeileAn(daten.text);
        return;
      }
      // JSON-Audit-Events ignorieren (die zeigt das Audit-Panel)
      if (daten && daten.typ === "audit") {
        return;
      }
    rendereEvent(daten);
  };
}

document.addEventListener("DOMContentLoaded", function () {
  const pre = document.getElementById("loop-log");
  if (!pre) {
    return;
  }
  const project = pre.dataset.project;
  if (project) {
    oeffne(project);
  }
});

window.WerkstattTerminal = { oeffne, schliesse };
