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
  const pre = document.getElementById("terminal");
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
  const spinner = document.getElementById("terminal-spinner");
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

document.addEventListener("DOMContentLoaded", function () {
  const pre = document.getElementById("terminal");
  if (!pre) {
    return;
  }
  const project = pre.dataset.project;
  if (project) {
    verbindeTerminal(project);
  }
});
