"""OP-034: pytest_regression-Stage + changed_non_test_py_files + requires-Gate."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, "/opt/werkstatt")

from werkstatt.state import RunState
from werkstatt.verify import _expand_cmd_placeholders, _ist_test_datei


def _state(patches: list[dict], project_dir: Path) -> RunState:
    """OP-034: RunState mit allen Pflichtfeldern."""
    s = RunState(
        block_id="t",
        aufgabe="t",
        start_ts="t",
        docs={},
        agents={},
        always={},
        optional={},
        file_whitelist=[],
        api_key="x",
        budget={},
        agent_docs={},
        project_dir=project_dir,
    )
    s.patches = patches  # type: ignore[attr-defined]
    return s


def test_ist_test_datei_erkennt_tests_pfad(tmp_path):
    assert _ist_test_datei("tests/unit/foo.py") is True
    assert _ist_test_datei("core/tests/bar.py") is True
    assert _ist_test_datei("test/x.py") is True


def test_ist_test_datei_erkennt_name(tmp_path):
    assert _ist_test_datei("foo/test_bar.py") is True
    assert _ist_test_datei("a/b/bar_test.py") is True
    assert _ist_test_datei("a/conftest.py") is True


def test_ist_test_datei_erkennt_code_nicht(tmp_path):
    assert _ist_test_datei("core/inventory/repository.py") is False
    assert _ist_test_datei("apps/main.py") is False
    assert _ist_test_datei("scripts/migrate.py") is False


def test_placeholder_non_test_skip_wenn_nur_tests(tmp_path):
    """Wenn nur Test-Files geaendert: non_test_py_files leer -> None."""
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests/test_foo.py").write_text("x", encoding="utf-8")
    state = _state([{"file": "tests/test_foo.py"}], tmp_path)
    res = _expand_cmd_placeholders(
        ["python3", "-m", "pytest", "{changed_non_test_py_files}"],
        state, tmp_path,
    )
    assert res is None


def test_placeholder_non_test_expand_wenn_code(tmp_path):
    (tmp_path / "core").mkdir()
    (tmp_path / "core/mod.py").write_text("x", encoding="utf-8")
    state = _state([{"file": "core/mod.py"}], tmp_path)
    res = _expand_cmd_placeholders(
        ["python3", "-m", "pytest", "{changed_non_test_py_files}"],
        state, tmp_path,
    )
    assert res == ["python3", "-m", "pytest", "core/mod.py"]


def test_placeholder_non_test_skip_wenn_nur_code_und_nur_tests_platzhalter(tmp_path):
    """Kombi: 1 Code + 1 Test -> non_test enthaelt nur Code."""
    (tmp_path / "core").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "core/mod.py").write_text("x", encoding="utf-8")
    (tmp_path / "tests/test_mod.py").write_text("x", encoding="utf-8")
    state = _state([
        {"file": "core/mod.py"},
        {"file": "tests/test_mod.py"},
    ], tmp_path)
    res = _expand_cmd_placeholders(
        ["pytest", "{changed_non_test_py_files}"],
        state, tmp_path,
    )
    assert res == ["pytest", "core/mod.py"]


def test_alle_3_json_haben_pytest_regression():
    for f in [
        "/opt/werkstatt/werkstatt/templates/.werkstatt/verify.json",
        "/opt/werkstatt/.werkstatt/verify.json",
        "/opt/security-ai/.werkstatt/verify.json",
    ]:
        p = Path(f)
        if not p.exists():
            continue
        data = json.loads(p.read_text())
        ids = [s.get("id") for s in data.get("stages", [])]
        assert "pytest_regression" in ids, f"{f}: pytest_regression fehlt"


def test_pytest_regression_requires_gesetzt():
    for f in [
        "/opt/werkstatt/werkstatt/templates/.werkstatt/verify.json",
        "/opt/werkstatt/.werkstatt/verify.json",
        "/opt/security-ai/.werkstatt/verify.json",
    ]:
        p = Path(f)
        if not p.exists():
            continue
        data = json.loads(p.read_text())
        stages = data.get("stages", [])
        stage = next(s for s in stages if s.get("id") == "pytest_regression")
        assert stage.get("requires") == "{changed_non_test_py_files}"
        assert stage.get("phase") == "phase_end"
