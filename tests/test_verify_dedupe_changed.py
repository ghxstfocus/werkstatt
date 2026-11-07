"""OP-? 2026-11-07: _expand_cmd_placeholders dedupliziert changed_files.

Anlass Loop-Test 9 (12:14-12:16): Builder baute reviewer.py in Runde 1,
dann Reflection-Runden 2-5 reparierten. state.patches hatte 5 Eintraege
fuer dieselbe Datei. `mypy {changed_py_files}` expandierte zu
"werkstatt/reviewer.py werkstatt/reviewer.py werkstatt/reviewer.py ..."
und meldete `Duplicate module named "werkstatt.reviewer"`. Der Fehler
verschwand nie, weil er kuenstlich war. Bug-B (verify_gleich) konnte
nicht greifen, weil die Fehler wechselten (PIE810 <-> Duplicate).

Fix: dict.fromkeys() dedupliziert, Reihenfolge bleibt erhalten.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, "/opt/werkstatt")

_here = Path(__file__).parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))
from factories import mk_state  # noqa: E402

from werkstatt.verify import _expand_cmd_placeholders  # noqa: E402


def test_changed_py_files_wird_dedupliziert(tmp_path):
    """Spec: derselbe Pfad 5x in state.patches -> 1x im Command."""
    f = tmp_path / "werkstatt" / "reviewer.py"
    f.parent.mkdir(parents=True)
    f.write_text("x = 1\n")

    s = mk_state(
        project_dir=str(tmp_path),
        project_name="test",
        patches=[{"file": "werkstatt/reviewer.py"}] * 5,
    )
    cmd = ["python3", "-m", "mypy", "--", "{changed_py_files}"]
    out = _expand_cmd_placeholders(cmd, s, tmp_path)
    assert out is not None
    # Ausgabe: ["python3", "-m", "mypy", "--", "werkstatt/reviewer.py"]
    # — also nur EIN Pfad am Ende, nicht 5.
    assert out[-1] == "werkstatt/reviewer.py"
    # Und der Pfad darf nicht 5x drin sein
    assert out.count("werkstatt/reviewer.py") == 1


def test_changed_files_verschiedene_pfade_reihenfolge(tmp_path):
    """Spec: Dedupe darf die Reihenfolge NICHT umsortieren."""
    for fname in ("a.py", "b.py", "a.py", "c.py", "b.py"):
        p = tmp_path / fname
        p.write_text("x = 1\n")

    s = mk_state(
        project_dir=str(tmp_path),
        project_name="test",
        patches=[
            {"file": "a.py"}, {"file": "b.py"}, {"file": "a.py"},
            {"file": "c.py"}, {"file": "b.py"},
        ],
    )
    cmd = ["tool", "{changed_files}"]
    out = _expand_cmd_placeholders(cmd, s, tmp_path)
    assert out is not None
    # Erwartet: ["tool", "a.py", "b.py", "c.py"] — Reihenfolge des
    # ersten Auftretens, keine Duplikate.
    assert out[1:] == ["a.py", "b.py", "c.py"]


def test_changed_test_files_wird_dedupliziert(tmp_path):
    """Spec: derselbe Test-Pfad mehrfach -> 1x im Command."""
    f = tmp_path / "tests" / "test_x.py"
    f.parent.mkdir(parents=True)
    f.write_text("def test_y(): pass\n")

    s = mk_state(
        project_dir=str(tmp_path),
        project_name="test",
        patches=[{"file": "tests/test_x.py"}] * 3,
    )
    cmd = ["pytest", "{changed_test_files}"]
    out = _expand_cmd_placeholders(cmd, s, tmp_path)
    assert out is not None
    assert out.count("tests/test_x.py") == 1
