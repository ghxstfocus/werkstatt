from datetime import UTC, datetime

from werkstatt.roles.builder import _builder_system, _korrigiere_doku_datum


def test_datum_kommt_aus_utc():
    prompt = _builder_system()
    heute = datetime.now(UTC).date().isoformat()
    assert heute in prompt
    assert "{{date}}" not in prompt
    assert prompt.count(heute) >= 1


def test_korrigiere_doku_datum_zukunft():
    patch = {
        "file": "docs/STATUS.md",
        "new_string": "Stand: 2026-11-03\n",
    }
    ergebnis = _korrigiere_doku_datum([patch], heute="2026-11-01")
    assert "2026-11-01" in ergebnis[0]["new_string"]
    assert "2026-11-03" not in ergebnis[0]["new_string"]


def test_korrigiere_doku_datum_code_unveraendert():
    patch = {
        "file": "werkstatt/foo.py",
        "new_string": "x = '2026-11-03'\n",
    }
    ergebnis = _korrigiere_doku_datum([patch], heute="2026-11-01")
    assert ergebnis[0]["new_string"] == patch["new_string"]


def test_korrigiere_doku_datum_historie_unveraendert():
    patch = {
        "file": "PROGRESS.md",
        "new_string": "2026-10-15: erledigt\n",
    }
    ergebnis = _korrigiere_doku_datum([patch], heute="2026-11-01")
    assert ergebnis[0]["new_string"] == patch["new_string"]
