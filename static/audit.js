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
  kalender: "#audit-kalender",
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

function createAuditPanel(options) {
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
  let elKalender = null;
  let gewaehlterTag = null;
  let kalenderMonat = null;

  let debounceTimer = null;

  function _streamUrl(projekt) {
    const loc = globalThis.location;
    const protokoll = loc && loc.protocol === "https:" ? "wss:" : "ws:";
    const host = loc ? loc.host : "";
    const pfad = `${basisPfad}/api/projects/${encodeURIComponent(projekt)}/audit/stream`;
    return `${protokoll}//${host}${pfad}`;
  }

  function _historyUrl(projekt, kind, runId, datum) {
    const basis = `${basisPfad}/api/projects/${encodeURIComponent(projekt)}/audit`;
    const params = new URLSearchParams();
    params.set("limit", String(HISTORY_LIMIT));
    if (kind) {
      params.set("kind", kind);
    }
    if (runId) {
      params.set("run_id", runId);
    }
    if (datum) {
      params.set("datum_von", datum);
      params.set("datum_bis", datum);
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
      // Feld heisst 'timestamp', nicht 'ts'
      zeit.textContent = _escapeText(_formatiereZeit(ev && (ev.timestamp || ev.ts)));

      const art = document.createElement("span");
      art.className = "audit-kind";
      art.textContent = _escapeText(ev && ev.kind);
      art.dataset.kind = String(ev && ev.kind || "");

      const text = document.createElement("span");
      text.className = "audit-text";
      // Es gibt kein 'payload'-Feld. Wir nehmen die Extra-Felder.
      var _extra = "";
      if (ev && typeof ev === "object") {
        var _skip = { audit_id: 1, timestamp: 1, ts: 1, agent: 1, project: 1, kind: 1 };
        var _teile = [];
        Object.keys(ev).forEach(function (k) {
          if (_skip[k]) return;
          var v = ev[k];
          var vs;
          try { vs = JSON.stringify(v); } catch (e) { vs = String(v); }
          if (vs && vs.length > 80) vs = vs.slice(0, 77) + "...";
          _teile.push(k + "=" + vs);
        });
        _extra = _teile.join(" ");
      }
      text.textContent = _escapeText(_extra);

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
      zeit.textContent = _escapeText(_formatiereZeit(ev && (ev.timestamp || ev.ts)));

      const art = document.createElement("span");
      art.className = "audit-kind";
      art.textContent = _escapeText(ev && ev.kind);
      art.dataset.kind = String(ev && ev.kind || "");

      const runId = document.createElement("span");
      runId.className = "audit-run-id";
      // run_id ist die Loop-Kennung (test-ui-xxx), audit_id nur Event-UID
      runId.textContent = _escapeText(ev && (ev.run_id || ev.audit_id || ""));

      const text = document.createElement("span");
      text.className = "audit-text";
      var _extra = "";
      if (ev && typeof ev === "object") {
        var _skip = { audit_id: 1, timestamp: 1, ts: 1, agent: 1, project: 1, kind: 1 };
        var _teile = [];
        Object.keys(ev).forEach(function (k) {
          if (_skip[k]) return;
          var v = ev[k];
          var vs;
          try { vs = JSON.stringify(v); } catch (e) { vs = String(v); }
          if (vs && vs.length > 120) vs = vs.slice(0, 117) + "...";
          _teile.push(k + "=" + vs);
        });
        _extra = _teile.join(" ");
      }
      text.textContent = _escapeText(_extra);

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

  async function oeffne(projekt) {
    const ziel = projekt ?? "";
    if (aktuellesProjekt === ziel && (verbunden || socket !== null)) {
      return;
    }
    aktuellesProjekt = ziel;
    liveEvents = [];
    reconnectVersuche = 0;
    if (reconnectTimer !== null) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
    _renderLive();
    if (!gewaehlterTag) {
      gewaehlterTag = new Date().toISOString().slice(0, 10);
    }
    if (!kalenderMonat) {
      kalenderMonat = gewaehlterTag.slice(0, 7);
    }
    await _ladeKalenderTage(kalenderMonat);
    await ladeHistory();
    _verbinde();
  }

  function schliesse() {
    if (reconnectTimer !== null) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
    if (socket) {
      try {
        socket.onopen = null;
        socket.onmessage = null;
        socket.onerror = null;
        socket.onclose = null;
        socket.close(1000, "tab-wechsel");
      } catch (err) {
        console.warn("audit: socket close fehlgeschlagen", err);
      }
      socket = null;
    }
    verbunden = false;
    aktuellesProjekt = null;
    liveEvents = [];
    _renderLive();
  }

  async function _ladeKalenderTage(monat) {
    if (!elKalender || !aktuellesProjekt) return;
    try {
      const antwort = await fetch(
        "/api/projects/" + encodeURIComponent(aktuellesProjekt) + "/audit/days?month=" + encodeURIComponent(monat),
        { headers: { Accept: "application/json" } }
      );
      if (!antwort.ok) return;
      const daten = await antwort.json();
      _renderKalender(daten.month, daten.tage || {});
    } catch (err) {
      console.warn("[audit] kalender fehler:", err);
    }
  }

  function _renderKalender(monat, tage) {
    if (!elKalender) return;
    // Label im Toggle-Summary aktualisieren
    var lbl = document.getElementById("audit-kalender-label");
    if (lbl && gewaehlterTag) {
      var t = new Date(gewaehlterTag + "T00:00:00");
      var heute = new Date().toISOString().slice(0, 10);
      if (gewaehlterTag === heute) {
        lbl.textContent = "Heute, " + t.toLocaleDateString("de-DE", { day: "2-digit", month: "short" });
      } else {
        lbl.textContent = t.toLocaleDateString("de-DE", { weekday: "short", day: "2-digit", month: "short" });
      }
    }
    elKalender.innerHTML = "";
    const teile = monat.split("-").map(Number);
    const jahr = teile[0], monatNr = teile[1];
    const titel = new Date(jahr, monatNr - 1, 1).toLocaleDateString("de-DE", { month: "long", year: "numeric" });
    const header = document.createElement("div");
    header.className = "kal-header";
    const prev = document.createElement("button");
    prev.className = "kal-nav";
    prev.textContent = "\u25C0";
    prev.addEventListener("click", function () {
      const d = new Date(jahr, monatNr - 2, 1);
      _ladeKalenderTage(d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0"));
    });
    const titelEl = document.createElement("span");
    titelEl.className = "kal-titel";
    titelEl.textContent = titel;
    const next = document.createElement("button");
    next.className = "kal-nav";
    next.textContent = "\u25B6";
    next.addEventListener("click", function () {
      const d = new Date(jahr, monatNr, 1);
      _ladeKalenderTage(d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0"));
    });
    header.appendChild(prev);
    header.appendChild(titelEl);
    header.appendChild(next);
    elKalender.appendChild(header);

    const grid = document.createElement("div");
    grid.className = "kal-grid";
    ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"].forEach(function (w) {
      const h = document.createElement("div");
      h.className = "kal-wtag";
      h.textContent = w;
      grid.appendChild(h);
    });
    const ersterTag = new Date(jahr, monatNr - 1, 1);
    const letzterTag = new Date(jahr, monatNr, 0).getDate();
    let startWtag = ersterTag.getDay() - 1;
    if (startWtag < 0) startWtag = 6;
    for (let i = 0; i < startWtag; i++) {
      const leer = document.createElement("div");
      leer.className = "kal-tag leer";
      grid.appendChild(leer);
    }
    const heuteStr = new Date().toISOString().slice(0, 10);
    for (let d = 1; d <= letzterTag; d++) {
      const datum = monat + "-" + String(d).padStart(2, "0");
      const anzahl = tage[datum] || 0;
      const btn = document.createElement("button");
      btn.className = "kal-tag";
      btn.textContent = d;
      btn.dataset.datum = datum;
      if (anzahl > 0) {
        btn.classList.add("hat-events");
        btn.title = anzahl + " Events";
      } else {
        btn.classList.add("keine-events");
        btn.disabled = true;
      }
      if (datum === heuteStr) btn.classList.add("heute");
      if (datum === gewaehlterTag) btn.classList.add("aktiv");
      btn.addEventListener("click", function () {
        gewaehlterTag = datum;
        kalenderMonat = monat;
        _renderKalender(monat, tage);
        // Kalender wieder einklappen
        var wrap = document.getElementById("audit-kalender-wrap");
        if (wrap) wrap.open = false;
        ladeHistory();
      });
      grid.appendChild(btn);
    }
    elKalender.appendChild(grid);
  }

  async function ladeHistory() {
    if (!aktuellesProjekt) {
      return;
    }
    const kind = elFilterKind ? _escapeText(elFilterKind.value).trim() : "";
    const runId = elFilterRunId ? _escapeText(elFilterRunId.value).trim() : "";
    let url;
    try {
      url = _historyUrl(aktuellesProjekt, kind, runId, gewaehlterTag);
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
      // Count im Toggle-Summary
      var cnt = document.getElementById("audit-kalender-count");
      if (cnt) {
        cnt.textContent = historyEvents.length > 0 ? "(" + historyEvents.length + ")" : "";
      }
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
    elKalender = document.querySelector(SELEKTOREN.kalender);

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
    oeffne,
    schliesse,
  };
}

if (typeof window !== "undefined") {
  window.WerkstattAudit = {
    oeffne: (projekt) => {
      const instanz = window.__werkstattAuditInstanz;
      if (instanz) {
        return instanz.oeffne(projekt);
      }
      return undefined;
    },
    schliesse: () => {
      const instanz = window.__werkstattAuditInstanz;
      if (instanz) {
        instanz.schliesse();
      }
    },
  };
}

// Init: Instanz erzeugen und mounten, sobald DOM da ist.
(function () {
  function _initAudit() {
    if (typeof window === "undefined") return;
    if (!window.__werkstattAuditInstanz && typeof createAuditPanel === "function") {
      try {
        window.__werkstattAuditInstanz = createAuditPanel({ projekt: "werkstatt" });
        if (window.__werkstattAuditInstanz && typeof window.__werkstattAuditInstanz.mount === "function") {
          window.__werkstattAuditInstanz.mount();
          if (typeof window.__werkstattAuditInstanz.oeffne === "function") {
            window.__werkstattAuditInstanz.oeffne("werkstatt").catch(function (e) {
              console.warn("[audit] initial oeffne fehler:", e);
            });
          }
          console.log("[audit] mount ok + oeffne(werkstatt)");
        } else {
          console.warn("[audit] createAuditPanel ohne mount");
        }
      } catch (e) {
        console.error("[audit] init fehler:", e);
      }
    }
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", _initAudit);
  } else {
    _initAudit();
  }
})();

