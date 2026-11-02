"use strict";

// Audit-Panel Frontend: Live-Stream via WebSocket + History via REST.
// Kein Framework, keine externen Imports. XSS-Schutz konsequent via textContent.

const LIVE_MAX = 200;
const HISTORY_LIMIT = 200;
const SELEKTOREN = {
  panel: "#audit-panel",
  live: "#audit-live",
  history: "#audit-history",
  filterKind: "#audit-filter-kind",
  filterRunId: "#audit-filter-run-id",
  buttonLaden: "#audit-history-laden",
  status: "#audit-status",
};

// Einheitliche Stringifizierung. Wird NIE als HTML interpretiert.
// Bewusster Kontrast zu einer escapeHtml-Loesung: hier gibt es keine,
// weil konsequent textContent verwendet wird.
function _escapeText(wert) {
  return String(wert ?? "");
}

// Akzeptiert ISO-String oder Zahl; gibt HH:MM:SS zurueck, bei
// unparsebarem Wert den Rohstring.
function _formatiereZeit(wert) {
  if (wert === null || wert === undefined || wert === "") {
    return "";
  }
  let datum;
  if (typeof wert === "number") {
    datum = new Date(wert);
  } else {
    datum = new Date(wert);
  }
  if (Number.isNaN(datum.getTime())) {
    return _escapeText(wert);
  }
  const hh = String(datum.getHours()).padStart(2, "0");
  const mm = String(datum.getMinutes()).padStart(2, "0");
  const ss = String(datum.getSeconds()).padStart(2, "0");
  return `${hh}:${mm}:${ss}`;
}

export function createAuditPanel(options) {
  const opts = options || {};
  const basisPfad = opts.basisPfad ?? "";

  let aktuellesProjekt = opts.projekt ?? "";
  let socket = null;
  let liveEvents = [];
  let historyEvents = [];
  let verbunden = false;
  let reconnectTimer = null;
  let reconnectVersuche = 0;

  let elPanel = null;
  let elLive = null;
  let elHistory = null;
  let elFilterKind = null;
  let elFilterRunId = null;
  let elButtonLaden = null;
  let elStatus = null;

  let debounceTimer = null;

  function _streamUrl(projekt) {
    const loc = globalThis.location;
    const protokoll = loc && loc.protocol === "https:" ? "wss:" : "ws:";
    const host = loc ? loc.host : "";
    const pfad = `${basisPfad}/api/projects/${encodeURIComponent(projekt)}/audit/stream`;
    return `${protokoll}//${host}${pfad}`;
  }

  function _historyUrl(projekt, kind, runId) {
    const basis = `${basisPfad}/api/projects/${encodeURIComponent(projekt)}/audit`;
    const params = new URLSearchParams();
    params.set("limit", String(HISTORY_LIMIT));
    if (kind) {
      params.set("kind", kind);
    }
    if (runId) {
      params.set("run_id", runId);
    }
    return `${basis}?${params.toString()}`;
  }

  function _setzeStatus(text) {
    if (elStatus) {
      elStatus.textContent = _escapeText(text);
    }
  }

  function _renderLive() {
    if (!elLive) {
      return;
    }
    elLive.textContent = "";
    for (const ev of liveEvents) {
      const zeile = document.createElement("div");
      zeile.className = "audit-live-zeile";

      const zeit = document.createElement("span");
      zeit.className = "audit-zeit";
      zeit.textContent = _escapeText(_formatiereZeit(ev && ev.ts));

      const art = document.createElement("span");
      art.className = "audit-kind";
      art.textContent = _escapeText(ev && ev.kind);

      const text = document.createElement("span");
      text.className = "audit-text";
      text.textContent = _escapeText(ev && ev.payload);

      zeile.appendChild(zeit);
      zeile.appendChild(art);
      zeile.appendChild(text);
      elLive.appendChild(zeile);
    }
  }

  function _renderHistory() {
    if (!elHistory) {
      return;
    }
    elHistory.textContent = "";
    for (const ev of historyEvents) {
      const zeile = document.createElement("div");
      zeile.className = "audit-history-zeile";

      const zeit = document.createElement("span");
      zeit.className = "audit-zeit";
      zeit.textContent = _escapeText(_formatiereZeit(ev && ev.ts));

      const art = document.createElement("span");
      art.className = "audit-kind";
      art.textContent = _escapeText(ev && ev.kind);

      const runId = document.createElement("span");
      runId.className = "audit-run-id";
      runId.textContent = _escapeText(ev && ev.run_id);

      const text = document.createElement("span");
      text.className = "audit-text";
      text.textContent = _escapeText(ev && ev.payload);

      zeile.appendChild(zeit);
      zeile.appendChild(art);
      zeile.appendChild(runId);
      zeile.appendChild(text);
      elHistory.appendChild(zeile);
    }
  }

  function _schliesseSocket() {
    if (socket) {
      try {
        socket.onopen = null;
        socket.onmessage = null;
        socket.onerror = null;
        socket.onclose = null;
        socket.close();
      } catch (err) {
        console.warn("audit: socket close fehlgeschlagen", err);
      }
      socket = null;
    }
    verbunden = false;
  }

  function _planeReconnect() {
    if (reconnectTimer !== null) {
      return;
    }
    const delay = Math.min(30000, 1000 * Math.pow(2, reconnectVersuche));
    reconnectVersuche += 1;
    reconnectTimer = setTimeout(() => {
      reconnectTimer = null;
      _verbinde();
    }, delay);
  }

  function _verbinde() {
    if (!aktuellesProjekt) {
      return;
    }
    _schliesseSocket();
    let url;
    try {
      url = _streamUrl(aktuellesProjekt);
    } catch (err) {
      console.warn("audit: stream-url fehlgeschlagen", err);
      return;
    }
    let ws;
    try {
      ws = new WebSocket(url);
    } catch (err) {
      console.warn("audit: WebSocket konnte nicht geoeffnet werden", err);
      _planeReconnect();
      return;
    }
    socket = ws;

    ws.onopen = () => {
      verbunden = true;
      reconnectVersuche = 0;
      _setzeStatus("verbunden");
    };

    ws.onmessage = (nachricht) => {
      let daten;
      try {
        daten = JSON.parse(nachricht.data);
      } catch (err) {
        console.warn("audit: ungueltiges JSON im Stream", err);
        return;
      }
      liveEvents.push(daten);
      if (liveEvents.length > LIVE_MAX) {
        liveEvents = liveEvents.slice(liveEvents.length - LIVE_MAX);
      }
      _renderLive();
    };

    ws.onerror = () => {
      _setzeStatus("fehler");
    };

    ws.onclose = () => {
      verbunden = false;
      socket = null;
      _setzeStatus("getrennt");
      _planeReconnect();
    };
  }

  function setzeProjekt(projekt) {
    aktuellesProjekt = projekt ?? "";
    liveEvents = [];
    historyEvents = [];
    reconnectVersuche = 0;
    if (reconnectTimer !== null) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
    _renderLive();
    _renderHistory();
    _verbinde();
  }

  async function ladeHistory() {
    if (!aktuellesProjekt) {
      return;
    }
    const kind = elFilterKind ? _escapeText(elFilterKind.value).trim() : "";
    const runId = elFilterRunId ? _escapeText(elFilterRunId.value).trim() : "";
    let url;
    try {
      url = _historyUrl(aktuellesProjekt, kind, runId);
    } catch (err) {
      console.warn("audit: history-url fehlgeschlagen", err);
      return;
    }
    _setzeStatus("lade history...");
    try {
      const antwort = await fetch(url, { headers: { Accept: "application/json" } });
      if (!antwort.ok) {
        _setzeStatus(`history-fehler ${antwort.status}`);
        return;
      }
      const daten = await antwort.json();
      if (Array.isArray(daten)) {
        historyEvents = daten.slice(-HISTORY_LIMIT);
      } else if (daten && Array.isArray(daten.events)) {
        historyEvents = daten.events.slice(-HISTORY_LIMIT);
      } else {
        historyEvents = [];
      }
      _renderHistory();
      _setzeStatus(`${historyEvents.length} eintraege`);
    } catch (err) {
      console.warn("audit: history laden fehlgeschlagen", err);
      _setzeStatus("history-fehler");
    }
  }

  function _debouncedLadeHistory() {
    if (debounceTimer !== null) {
      clearTimeout(debounceTimer);
    }
    debounceTimer = setTimeout(() => {
      debounceTimer = null;
      ladeHistory();
    }, 250);
  }

  function mount() {
    elPanel = document.querySelector(SELEKTOREN.panel);
    elLive = document.querySelector(SELEKTOREN.live);
    elHistory = document.querySelector(SELEKTOREN.history);
    elFilterKind = document.querySelector(SELEKTOREN.filterKind);
    elFilterRunId = document.querySelector(SELEKTOREN.filterRunId);
    elButtonLaden = document.querySelector(SELEKTOREN.buttonLaden);
    elStatus = document.querySelector(SELEKTOREN.status);

    if (!elPanel || !elLive || !elHistory) {
      console.warn("audit: Pflichtelemente fehlen, mount abgebrochen");
      return;
    }

    if (elButtonLaden) {
      elButtonLaden.addEventListener("click", () => {
        ladeHistory();
      });
    }
    if (elFilterKind) {
      elFilterKind.addEventListener("change", _debouncedLadeHistory);
      elFilterKind.addEventListener("input", _debouncedLadeHistory);
    }
    if (elFilterRunId) {
      elFilterRunId.addEventListener("change", _debouncedLadeHistory);
      elFilterRunId.addEventListener("input", _debouncedLadeHistory);
    }

    setzeProjekt(aktuellesProjekt);
  }

  function zerstoere() {
    if (debounceTimer !== null) {
      clearTimeout(debounceTimer);
      debounceTimer = null;
    }
    if (reconnectTimer !== null) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
    _schliesseSocket();
    liveEvents = [];
    historyEvents = [];
    _renderLive();
    _renderHistory();
  }

  return {
    mount,
    setzeProjekt,
    ladeHistory,
    zerstoere,
  };
}
