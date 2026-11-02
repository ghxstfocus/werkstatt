from __future__ import annotations

import pytest

from werkstatt.web.chat import (
    layout_fuer,
    neuer_tab_zustand,
    parse_intent,
    wende_aktion_an,
)


def test_maximize_minimize_state():
    zustand = neuer_tab_zustand()
    assert layout_fuer(zustand)["modus"] == "split"
    assert layout_fuer(zustand)["fokus"] == ""

    zustand = wende_aktion_an(zustand, "maximize")

    assert zustand["admin"].maximiert is True
    assert zustand["bau"].minimiert is True
    assert zustand["bau"].maximiert is False
    assert layout_fuer(zustand)["modus"] == "focus"
    assert layout_fuer(zustand)["fokus"] == "admin"
    assert layout_fuer(zustand)["sichtbar"] == {"admin": True, "bau": False}

    zustand = wende_aktion_an(zustand, "maximize")

    assert zustand["admin"].maximiert is False
    assert zustand["admin"].minimiert is False
    assert zustand["bau"].maximiert is False
    assert zustand["bau"].minimiert is False
    assert layout_fuer(zustand)["modus"] == "split"

    with pytest.raises(ValueError):
        wende_aktion_an(zustand, "unbekannt")


def test_intent_parsing():
    ergebnis = parse_intent("admin: plan Refactor der Pipeline")
    assert ergebnis["ziel"] == "admin"
    assert ergebnis["intent"] == "plan"
    assert ergebnis["rest"] == "Refactor der Pipeline"

    ergebnis = parse_intent("bau: build Feature X")
    assert ergebnis["ziel"] == "bau"
    assert ergebnis["intent"] == "build"
    assert ergebnis["rest"] == "Feature X"

    for wort in ("ja", "j"):
        ergebnis = parse_intent(wort)
        assert ergebnis["intent"] == "approve"
        assert ergebnis["bestaetigt"] == "true"

    for wort in ("nein", "n"):
        ergebnis = parse_intent(wort)
        assert ergebnis["intent"] == "approve"
        assert ergebnis["bestaetigt"] == "false"

    ergebnis = parse_intent("approve ja")
    assert ergebnis["intent"] == "approve"
    assert ergebnis["bestaetigt"] == "true"

    ergebnis = parse_intent("admin: hallo")
    assert ergebnis["intent"] == "chat_only"
    assert ergebnis["rest"] == "hallo"

    ergebnis = parse_intent("")
    assert ergebnis["ziel"] == "bau"
    assert ergebnis["intent"] == "chat_only"
    assert ergebnis["rest"] == ""

    erlaubte_intents = {"plan", "build", "approve", "chat_only"}
    for eingabe in (
        "admin: plan Refactor der Pipeline",
        "bau: build Feature X",
        "ja",
        "j",
        "nein",
        "n",
        "approve ja",
        "admin: hallo",
        "",
    ):
        ergebnis = parse_intent(eingabe)
        # bestaetigt ist nur bei approve-Intent gesetzt (optional)
        keys_ohne_bestaetigt = set(ergebnis.keys()) - {"bestaetigt"}
        assert keys_ohne_bestaetigt == {"roh", "ziel", "intent", "rest"}
        assert ergebnis["intent"] in erlaubte_intents
