import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


class FakeKanal:
    def __init__(self, projekt: str):
        self.projekt = projekt
        self.nutzer = 1
        self.geschlossen = 0
        self.gesendet: list[dict] = []

    def close(self) -> None:
        self.geschlossen += 1

    def senden(self, nachricht: dict) -> None:
        self.gesendet.append(nachricht)


class FakeFabrik:
    def __init__(self):
        self.aufrufe: dict[str, int] = {}
        self.erzeugte: list[FakeKanal] = []
        self.fehler_modus = False

    def erstelle(self, projekt: str) -> FakeKanal:
        if self.fehler_modus:
            raise RuntimeError(f"Fabrik-Fehler fuer {projekt}")
        self.aufrufe[projekt] = self.aufrufe.get(projekt, 0) + 1
        kanal = FakeKanal(projekt)
        self.erzeugte.append(kanal)
        return kanal


class Spiegel:
    def neuer_zustand(self, fabrik) -> dict:
        return {
            "tabs": {},
            "reihenfolge": [],
            "aktiv": None,
            "kanaele": {},
            "zaehler": 0,
            "kanal_fabrik": fabrik,
        }

    def kanal_holen(self, zustand: dict, projekt: str):
        eintrag = zustand["kanaele"].get(projekt)
        if eintrag is not None:
            eintrag["nutzer"] += 1
            return eintrag["kanal"]
        kanal = zustand["kanal_fabrik"].erstelle(projekt)
        zustand["kanaele"][projekt] = {"kanal": kanal, "nutzer": 1}
        return kanal

    def kanal_freigeben(self, zustand: dict, projekt: str) -> bool:
        eintrag = zustand["kanaele"].get(projekt)
        if eintrag is None:
            return False
        eintrag["nutzer"] -= 1
        if eintrag["nutzer"] <= 0:
            eintrag["kanal"].close()
            del zustand["kanaele"][projekt]
            return True
        return False

    def oeffne_tab(self, zustand: dict, projekt: str, titel: str) -> dict:
        kanal = self.kanal_holen(zustand, projekt)
        zustand["zaehler"] += 1
        tab_id = f"tab-{zustand['zaehler']}"
        tab = {
            "id": tab_id,
            "projekt": projekt,
            "titel": titel,
            "terminal": {"kanal": kanal},
            "chat": {"kanal": kanal},
            "audit": {"kanal": kanal},
        }
        zustand["tabs"][tab_id] = tab
        zustand["reihenfolge"].append(tab_id)
        zustand["aktiv"] = tab_id
        return tab

    def wechsle_tab(self, zustand: dict, tab_id: str) -> bool:
        if tab_id not in zustand["tabs"]:
            return False
        zustand["aktiv"] = tab_id
        return True

    def schliesse_tab(self, zustand: dict, tab_id: str) -> bool:
        tab = zustand["tabs"].get(tab_id)
        if tab is None:
            return False
        reihenfolge = zustand["reihenfolge"]
        index = reihenfolge.index(tab_id)
        reihenfolge.pop(index)
        del zustand["tabs"][tab_id]
        self.kanal_freigeben(zustand, tab["projekt"])
        if zustand["aktiv"] == tab_id:
            if reihenfolge:
                nachbar = reihenfolge[min(index, len(reihenfolge) - 1)]
                zustand["aktiv"] = nachbar
            else:
                zustand["aktiv"] = None
        return True

    def synchronisiere(self, zustand: dict) -> dict:
        tab = zustand["tabs"].get(zustand["aktiv"])
        if tab is None:
            return {
                "aktiv": None,
                "projekt": None,
                "terminal": None,
                "chat": None,
                "audit": None,
            }
        return {
            "aktiv": tab["id"],
            "projekt": tab["projekt"],
            "terminal": tab["terminal"],
            "chat": tab["chat"],
            "audit": tab["audit"],
        }


def _js_quelle() -> str:
    pfad = REPO / "static" / "tabs.js"
    assert pfad.is_file(), f"JS-Quelle fehlt: {pfad}"
    return pfad.read_text(encoding="utf-8")


def _html_quelle() -> str:
    pfad = REPO / "static" / "layout.html"
    assert pfad.is_file(), f"HTML-Quelle fehlt: {pfad}"
    return pfad.read_text(encoding="utf-8")


def test_tab_wechsel_synchronisiert_bereiche():
    fabrik = FakeFabrik()
    s = Spiegel()
    zustand = s.neuer_zustand(fabrik)
    tab_a = s.oeffne_tab(zustand, "projekt-a", "A")
    tab_b = s.oeffne_tab(zustand, "projekt-b", "B")

    assert zustand["aktiv"] == tab_b["id"]
    assert s.wechsle_tab(zustand, tab_a["id"]) is True

    sync = s.synchronisiere(zustand)
    assert sync["aktiv"] == tab_a["id"]
    assert sync["projekt"] == "projekt-a"
    assert sync["terminal"] == tab_a["terminal"]
    assert sync["chat"] == tab_a["chat"]
    assert sync["audit"] == tab_a["audit"]

    assert s.wechsle_tab(zustand, "gibt-es-nicht") is False
    assert zustand["aktiv"] == tab_a["id"]


def test_kanal_freigabe_und_fehlerpfad():
    fabrik = FakeFabrik()
    s = Spiegel()
    zustand = s.neuer_zustand(fabrik)

    kanal_1 = s.kanal_holen(zustand, "projekt-a")
    kanal_2 = s.kanal_holen(zustand, "projekt-a")
    assert kanal_1 is kanal_2
    assert fabrik.aufrufe["projekt-a"] == 1
    assert zustand["kanaele"]["projekt-a"]["nutzer"] == 2

    assert s.kanal_freigeben(zustand, "projekt-a") is False
    assert kanal_1.geschlossen == 0
    assert s.kanal_freigeben(zustand, "projekt-a") is True
    assert kanal_1.geschlossen == 1
    assert "projekt-a" not in zustand["kanaele"]
    assert s.kanal_freigeben(zustand, "projekt-a") is False

    fabrik.fehler_modus = True
    try:
        s.kanal_holen(zustand, "projekt-b")
    except RuntimeError:
        pass
    else:
        raise AssertionError("RuntimeError erwartet")
    assert "projekt-b" not in zustand["kanaele"]


def test_js_quelle_enthaelt_store_namen():
    quelle = _js_quelle()
    for name in ("neuer_zustand", "kanal_holen"):
        assert re.search(rf"\b{name}\b", quelle), f"{name} fehlt in tabs.js"


def test_html_quelle_enthaelt_bereiche():
    quelle = _html_quelle()
    for bereich in ("terminal", "chat", "audit"):
        assert bereich in quelle, f"{bereich} fehlt in layout.html"


def test_spiegel_zustand_ist_json_serialisierbar():
    fabrik = FakeFabrik()
    s = Spiegel()
    zustand = s.neuer_zustand(fabrik)
    s.oeffne_tab(zustand, "projekt-a", "A")
    sync = s.synchronisiere(zustand)
    serialisierbar = {
        "aktiv": sync["aktiv"],
        "projekt": sync["projekt"],
        "terminal": sync["terminal"] is not None,
        "chat": sync["chat"] is not None,
        "audit": sync["audit"] is not None,
    }
    assert json.loads(json.dumps(serialisierbar))["projekt"] == "projekt-a"


def test_tab_schliessen_stop_ws():
    fabrik = FakeFabrik()
    s = Spiegel()
    zustand = s.neuer_zustand(fabrik)
    tab_a = s.oeffne_tab(zustand, "projekt-a", "A")
    tab_b = s.oeffne_tab(zustand, "projekt-b", "B")

    assert s.schliesse_tab(zustand, tab_b["id"]) is True
    assert tab_b["id"] not in zustand["tabs"]
    assert tab_b["id"] not in zustand["reihenfolge"]
    assert zustand["aktiv"] == tab_a["id"]
    assert fabrik.erzeugte[-1].geschlossen == 1

    assert s.schliesse_tab(zustand, tab_a["id"]) is True
    assert zustand["aktiv"] is None
    assert zustand["reihenfolge"] == []
    assert s.schliesse_tab(zustand, "gibt-es-nicht") is False
