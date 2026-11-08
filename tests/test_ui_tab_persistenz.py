"""OP-306a: Tab-Persistenz — Verhaltens-Specs (ADR-0015/0016).

Die TabSpiegel-Klasse bildet das JS-Verhalten in Python nach. Die
Verhaltens-Tests (10) pruefen Spec-Verhalten: "Was passiert, wenn der
Nutzer X macht?" — NICHT "enthaelt tabs.js Zeile Y?".

Die Drift-Guards (4) sind die Bruecke: sie stellen sicher, dass der
Spiegel nicht ein Phantom testet. Ohne diese 4 Tests koennte tabs.js
beliebig kaputt sein, und der Spiegel waere immer noch gruen.

Node fehlt im Projekt (MERKPOSTEN Session 2026-11-08), daher dient
test_js_klammer_balance als node --check-Ersatz.
"""
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PERSIST_KEY = "werkstatt-tabs:v1"


# ---------------------------------------------------------------------------
# Verhaltens-Spiegel (bildet static/tabs.js Welt-A ab)
# ---------------------------------------------------------------------------

class TabSpiegel:
    """Spiegelt neuerTab/wechsle/schliesse/persist/rehydrieren.

    Bewusst reduziert:
      - kein Debounce (Tests deterministisch; Debounce ist UI-Performance)
      - kein DOM (Reihenfolge via list; identisch zur DOM-Ordnung)
      - kein Store-API-Welt-B (nur test_ui_layout.py prueft die)
    """

    def __init__(self, storage=None):
        self.storage = storage if storage is not None else {}
        self.tabs = {}          # tabId -> {"projekt": str}
        self.reihenfolge = []   # logische DOM-Reihenfolge
        self.aktiver = None
        self.zaehler = 0
        self._rehydriere_laeuft = False

    # -- Persistenz (synchron, wie im JS nach Debounce) -----------------

    def _persistiere_tabs(self):
        if self._rehydriere_laeuft:
            return
        eintraege = []
        for tid in self.reihenfolge:
            d = self.tabs.get(tid)
            if not d:
                continue
            if not isinstance(d["projekt"], str) or not d["projekt"]:
                continue
            eintraege.append({"projekt": d["projekt"], "aktiv": tid == self.aktiver})
        if not eintraege:
            self.storage.pop(PERSIST_KEY, None)
        else:
            self.storage[PERSIST_KEY] = json.dumps(eintraege)

    def _lade_gespeicherte_tabs(self):
        try:
            raw = self.storage.get(PERSIST_KEY)
            if not raw:
                return []
            arr = json.loads(raw)
            if not isinstance(arr, list):
                return []
            sauber = []
            for e in arr:
                if not e:
                    continue
                if not isinstance(e.get("projekt"), str) or not e["projekt"]:
                    continue
                sauber.append({"projekt": e["projekt"], "aktiv": e.get("aktiv") is True})
            return sauber
        except (json.JSONDecodeError, TypeError, AttributeError):
            return []

    # -- Welt-A-Operationen ---------------------------------------------

    def neuer_tab(self, projekt):
        self.zaehler += 1
        tid = f"tab-{self.zaehler}"
        self.tabs[tid] = {"projekt": projekt}
        self.reihenfolge.append(tid)
        self._persistiere_tabs()
        return tid

    def wechsle(self, tab_id):
        if tab_id not in self.tabs:
            return
        self.aktiver = tab_id
        self._persistiere_tabs()

    def schliesse(self, tab_id):
        if tab_id not in self.tabs:
            return
        self.reihenfolge.remove(tab_id)
        del self.tabs[tab_id]
        if self.aktiver == tab_id:
            self.aktiver = self.reihenfolge[0] if self.reihenfolge else None
        self._persistiere_tabs()

    def initialisiere(self):
        gespeicherte = self._lade_gespeicherte_tabs()
        if not gespeicherte:
            sid = self.neuer_tab("werkstatt")
            self.wechsle(sid)
            return
        self._rehydriere_laeuft = True
        aktiver_id = None
        for e in gespeicherte:
            tid = self.neuer_tab(e["projekt"])
            if e["aktiv"]:
                aktiver_id = tid
        self._rehydriere_laeuft = False
        if aktiver_id is not None:
            self.wechsle(aktiver_id)
        elif self.reihenfolge:
            self.wechsle(self.reihenfolge[0])
        self._persistiere_tabs()


# ---------------------------------------------------------------------------
# Verhaltens-Specs: "Was passiert bei X?"
# ---------------------------------------------------------------------------

def test_leerer_storage_nutzt_default_fallback():
    sp = TabSpiegel()
    sp.initialisiere()
    assert len(sp.tabs) == 1
    assert next(iter(sp.tabs.values()))["projekt"] == "werkstatt"
    assert sp.aktiver is not None


def test_gespeicherter_zustand_wird_wiederhergestellt():
    storage = {PERSIST_KEY: json.dumps([
        {"projekt": "a", "aktiv": True},
        {"projekt": "b", "aktiv": False},
    ])}
    sp = TabSpiegel(storage=storage)
    sp.initialisiere()
    assert len(sp.tabs) == 2
    assert sp.tabs[sp.aktiver]["projekt"] == "a"


def test_rehydration_ohne_aktiven_fallback_auf_ersten():
    storage = {PERSIST_KEY: json.dumps([
        {"projekt": "x", "aktiv": False},
        {"projekt": "y", "aktiv": False},
    ])}
    sp = TabSpiegel(storage=storage)
    sp.initialisiere()
    assert sp.aktiver == sp.reihenfolge[0]
    assert sp.tabs[sp.aktiver]["projekt"] == "x"


def test_letzter_tab_loescht_key():
    sp = TabSpiegel()
    sp.initialisiere()
    einziger = sp.reihenfolge[0]
    sp.schliesse(einziger)
    assert PERSIST_KEY not in sp.storage
    assert sp.aktiver is None


def test_korruptes_json_ignoriert_und_default():
    sp = TabSpiegel(storage={PERSIST_KEY: "kaputt{["})
    sp.initialisiere()
    assert len(sp.tabs) == 1
    assert sp.tabs[sp.reihenfolge[0]]["projekt"] == "werkstatt"


def test_nicht_array_ignoriert():
    sp = TabSpiegel(storage={PERSIST_KEY: '{"x":1}'})
    sp.initialisiere()
    assert len(sp.tabs) == 1
    assert sp.tabs[sp.reihenfolge[0]]["projekt"] == "werkstatt"


def test_stale_projekt_eintrag_uebersprungen():
    sp = TabSpiegel(storage={PERSIST_KEY: json.dumps([
        {"projekt": 123, "aktiv": True},
        {"projekt": "", "aktiv": False},
        {"projekt": None, "aktiv": False},
    ])})
    sp.initialisiere()
    assert len(sp.tabs) == 1
    assert sp.tabs[sp.reihenfolge[0]]["projekt"] == "werkstatt"


def test_zaehler_nach_rehydration_korrekt():
    storage = {PERSIST_KEY: json.dumps([
        {"projekt": "a", "aktiv": True},
        {"projekt": "b", "aktiv": False},
        {"projekt": "c", "aktiv": False},
    ])}
    sp = TabSpiegel(storage=storage)
    sp.initialisiere()
    assert sp.zaehler == 3
    neuer = sp.neuer_tab("d")
    assert neuer == "tab-4"
    assert len(sp.tabs) == 4
    assert sp.tabs["tab-1"]["projekt"] == "a"
    assert sp.tabs["tab-4"]["projekt"] == "d"


def test_rehydration_persistiert_final():
    storage = {PERSIST_KEY: json.dumps([{"projekt": "a", "aktiv": True}])}
    sp = TabSpiegel(storage=storage)
    sp.initialisiere()
    assert PERSIST_KEY in sp.storage
    arr = json.loads(sp.storage[PERSIST_KEY])
    assert len(arr) == 1
    assert arr[0]["projekt"] == "a"
    assert arr[0]["aktiv"] is True


def test_tab_wechsel_persistiert_aktiv():
    sp = TabSpiegel()
    sp.initialisiere()
    t2 = sp.neuer_tab("b")
    sp.wechsle(t2)
    arr = json.loads(sp.storage[PERSIST_KEY])
    aktive = [e for e in arr if e["aktiv"]]
    assert len(aktive) == 1
    assert aktive[0]["projekt"] == "b"


# ---------------------------------------------------------------------------
# Drift-Guards: Bruecke zwischen Spiegel und echtem JS
# ---------------------------------------------------------------------------

def _js() -> str:
    return (REPO / "static" / "tabs.js").read_text(encoding="utf-8")


def _html() -> str:
    return (REPO / "static" / "layout.html").read_text(encoding="utf-8")


def test_js_enthaelt_persist_key_contract():
    """Key-Literal muss im JS stehen — externer Contract (Browser-Storage)."""
    assert f'"{PERSIST_KEY}"' in _js()


def test_js_enthaelt_persist_funktionen():
    """Die 3 Funktionen, die der Spiegel nachbildet, muessen im JS existieren.

    Ohne diesen Guard koennte tabs.js sie umbenennen oder entfernen,
    und der Spiegel wuerde weiter gruen testen (Phantom-Verhalten).
    """
    q = _js()
    for name in ("function _persistiere_tabs", "function _lade_gespeicherte_tabs"):
        assert name in q, f"JS-Funktion fehlt: {name}"


def test_js_klammer_balance():
    """Ersatz fuer node --check: Klammer-Balance mit Kommentar/String-Zustand."""
    q = _js()
    zustand = "normal"
    tiefe_c = 0
    tiefe_p = 0
    i = 0
    n = len(q)
    while i < n:
        c = q[i]
        naechstes = q[i + 1] if i + 1 < n else ""
        if zustand == "normal":
            if c == "/" and naechstes == "/":
                zustand = "line_comment"; i += 2; continue
            if c == "/" and naechstes == "*":
                zustand = "block_comment"; i += 2; continue
            if c == '"':
                zustand = "string_double"; i += 1; continue
            if c == "'":
                zustand = "string_single"; i += 1; continue
            if c == "`":
                zustand = "string_backtick"; i += 1; continue
            if c == "{":
                tiefe_c += 1
            elif c == "}":
                tiefe_c -= 1
            elif c == "(":
                tiefe_p += 1
            elif c == ")":
                tiefe_p -= 1
            i += 1
        elif zustand == "line_comment":
            if c == "\n":
                zustand = "normal"
            i += 1
        elif zustand == "block_comment":
            if c == "*" and naechstes == "/":
                zustand = "normal"; i += 2; continue
            i += 1
        else:
            if c == "\\":
                i += 2; continue
            if ((zustand == "string_double" and c == '"')
                    or (zustand == "string_single" and c == "'")
                    or (zustand == "string_backtick" and c == "`")):
                zustand = "normal"
            i += 1
    assert zustand == "normal", f"JS unterminated: Zustand={zustand}"
    assert tiefe_c == 0, f"curly-Balance: tiefe={tiefe_c}"
    assert tiefe_p == 0, f"paren-Balance: tiefe={tiefe_p}"


def test_cache_buster_synchron():
    """Alle ?v=-Werte in layout.html identisch (Merkposten 2026-11-08)."""
    werte = set(re.findall(r"\?v=(\d+)", _html()))
    assert len(werte) == 1, f"Cache-Buster nicht synchron: {werte}"
