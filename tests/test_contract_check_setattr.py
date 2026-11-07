import textwrap

from tools.contract_check import _pruefe_setattr_aufrufe
from werkstatt.state import RunState

FELDER = set(RunState.__dataclass_fields__)


def test_setattr_unbekanntes_feld_failt(tmp_path):
    pfad = tmp_path / "probe.py"
    pfad.write_text(
        textwrap.dedent(
            'def f(state):\n    setattr(state, "phase_review_gate_auto", True)\n'
        )
    )
    assert "phase_review_gate_auto" not in FELDER

    fehler = _pruefe_setattr_aufrufe(pfad, FELDER)

    assert len(fehler) == 1
    assert "phase_review_gate_auto" in fehler[0]
    assert str(pfad) in fehler[0]
    assert ":2:" in fehler[0]


def test_setattr_bekanntes_feld_ok(tmp_path):
    pfad = tmp_path / "probe.py"
    pfad.write_text(
        textwrap.dedent('def f(state):\n    setattr(state, "tasks", [])\n')
    )
    assert "tasks" in FELDER

    fehler = _pruefe_setattr_aufrufe(pfad, FELDER)

    assert fehler == []


def test_setattr_dynamischer_name_skip(tmp_path):
    pfad = tmp_path / "probe.py"
    pfad.write_text(
        textwrap.dedent(
            'def f(state, feldname):\n    setattr(state, feldname, 1)\n'
        )
    )

    fehler = _pruefe_setattr_aufrufe(pfad, FELDER)

    assert fehler == []
