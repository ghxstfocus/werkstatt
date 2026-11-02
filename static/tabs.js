(function () {
  "use strict";

  function standard_kanal_fabrik(projekt) {
    var basis = location.origin.replace(/^http/, "ws");
    return new WebSocket(basis + "/ws/projects/" + encodeURIComponent(projekt));
  }

  function neuer_zustand(optionen) {
    var opts = optionen || {};
    var fabrik = opts.kanal_fabrik || standard_kanal_fabrik;
    return {
      tabs: {},
      reihenfolge: [],
      aktiv: null,
      kanaele: {},
      zaehler: 0,
      kanal_fabrik: fabrik
    };
  }

  function kanal_holen(zustand, projekt) {
    if (Object.prototype.hasOwnProperty.call(zustand.kanaele, projekt)) {
      var vorhanden = zustand.kanaele[projekt];
      vorhanden.nutzer = vorhanden.nutzer + 1;
      return vorhanden;
    }
    var kanal = { projekt: projekt, nutzer: 1, ws: null, audit_abort: null };
    var ws;
    try {
      ws = zustand.kanal_fabrik(projekt);
    } catch (fehler) {
      var umhuellt = new Error("Kanal-Fabrik fehlgeschlagen fuer " + projekt);
      umhuellt.code = "kanal_fabrik_fehler";
      umhuellt.ursache = fehler;
      throw umhuellt;
    }
    kanal.ws = ws;
    zustand.kanaele[projekt] = kanal;
    return kanal;
  }

  function kanal_freigeben(zustand, projekt) {
    if (!Object.prototype.hasOwnProperty.call(zustand.kanaele, projekt)) {
      return;
    }
    var kanal = zustand.kanaele[projekt];
    kanal.nutzer = kanal.nutzer - 1;
    if (kanal.nutzer > 0) {
      return;
    }
    if (kanal.audit_abort && typeof kanal.audit_abort.abort === "function") {
      try {
        kanal.audit_abort.abort();
      } catch (fehler) {
        /* Abort-Fehler ignorieren */
      }
    }
    if (kanal.ws && typeof kanal.ws.close === "function") {
      try {
        kanal.ws.close();
      } catch (fehler) {
        /* Close-Fehler ignorieren */
      }
    }
    delete zustand.kanaele[projekt];
  }

  function oeffne_tab(zustand, tab_id, projekt) {
    if (Object.prototype.hasOwnProperty.call(zustand.tabs, tab_id)) {
      return zustand.tabs[tab_id];
    }
    var kanal = kanal_holen(zustand, projekt);
    var tab = {
      id: tab_id,
      projekt: projekt,
      kanal: kanal,
      nachrichten: [],
      zustand: {}
    };
    zustand.tabs[tab_id] = tab;
    zustand.reihenfolge.push(tab_id);
    zustand.zaehler = zustand.zaehler + 1;
    if (zustand.aktiv === null) {
      zustand.aktiv = tab_id;
    }
    return tab;
  }

  function schliesse_tab(zustand, tab_id) {
    if (!Object.prototype.hasOwnProperty.call(zustand.tabs, tab_id)) {
      return;
    }
    var tab = zustand.tabs[tab_id];
    kanal_freigeben(zustand, tab.projekt);
    delete zustand.tabs[tab_id];
    var idx = zustand.reihenfolge.indexOf(tab_id);
    if (idx >= 0) {
      zustand.reihenfolge.splice(idx, 1);
    }
    if (zustand.aktiv === tab_id) {
      zustand.aktiv = zustand.reihenfolge.length > 0 ? zustand.reihenfolge[0] : null;
    }
  }

  function wechsle_tab(zustand, tab_id) {
    if (!Object.prototype.hasOwnProperty.call(zustand.tabs, tab_id)) {
      return null;
    }
    zustand.aktiv = tab_id;
    return zustand.tabs[tab_id];
  }

  window.WerkstattTabs = {
    neuer_zustand: neuer_zustand,
    kanal_holen: kanal_holen,
    kanal_freigeben: kanal_freigeben,
    oeffne_tab: oeffne_tab,
    schliesse_tab: schliesse_tab,
    wechsle_tab: wechsle_tab,
    neuerZustand: neuer_zustand,
    kanalHolen: kanal_holen,
    kanalFreigeben: kanal_freigeben,
    oeffneTab: oeffne_tab,
    schliesseTab: schliesse_tab,
    wechsleTab: wechsle_tab
  };
})();
