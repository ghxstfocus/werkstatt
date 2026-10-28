"""K48: Aider-Format (context+old+new) -> old_string/new_string."""
import json
from unittest.mock import patch

from werkstatt.builder import run_builder


def _mock_llm(content: str):
    return type("R", (), {"ok": True, "content": content, "error": ""})()


def _st(tmp_path, datei: str):
    ziel = tmp_path / datei
    return type("S", (), {
        "project_dir": tmp_path, "project_name": "t", "api_key": "x",
        "aktuelle_task": {"id": "t1", "name": "x", "description": "x",
                          "action": "update", "task_files": [datei]},
        "tasks": [{"task_files": [datei]}], "file_whitelist": [datei],
        "gelesene_dateien": {datei: ziel.stat().st_mtime},
        "patches": [], "builder_feedback": {}, "reviewer_bugs": [],
        "last_verify_errors": [], "reflection_history": [],
        "reflection_phase": False, "architect_beschreibung": "",
    })()


def test_aider_patch_wird_normalisiert(tmp_path):
    ziel = tmp_path / "a.py"
    ziel.write_text(
        "def helper():\n    return 1\n\ndef ziel():\n    return 2\n",
        encoding="utf-8",
    )
    patch_obj = {
        "patches": [{
            "action": "update", "file": "a.py",
            "context": "def helper():\n    return 1\n",
            "old": "def ziel():\n    return 2\n",
            "new": "def ziel():\n    return 42\n",
        }],
    }
    aider_json = json.dumps(patch_obj, ensure_ascii=False)
    st = _st(tmp_path, "a.py")
    with patch("werkstatt.builder.ask_llm", return_value=_mock_llm(aider_json)), \
         patch("werkstatt.builder.audit"):
        ok = run_builder(st)
    assert ok is True
    p = st.patches[0]
    assert "context" not in p and "old" not in p and "new" not in p
    assert p["old_string"] == "def helper():\n    return 1\ndef ziel():\n    return 2\n"
    assert p["new_string"] == "def helper():\n    return 1\ndef ziel():\n    return 42\n"


def test_legacy_patch_bleibt_unveraendert(tmp_path):
    ziel = tmp_path / "a.py"
    ziel.write_text("x = 1\n", encoding="utf-8")
    legacy_json = json.dumps({
        "patches": [{"action": "update", "file": "a.py",
                     "old_string": "x = 1", "new_string": "x = 2"}],
    })
    st = _st(tmp_path, "a.py")
    with patch("werkstatt.builder.ask_llm", return_value=_mock_llm(legacy_json)), \
         patch("werkstatt.builder.audit"):
        ok = run_builder(st)
    assert ok is True
    p = st.patches[0]
    assert p["old_string"] == "x = 1" and p["new_string"] == "x = 2"
    assert "context" not in p


def test_prompt_enthaelt_aider_format():
    from werkstatt.builder import BUILDER_SYSTEM
    assert '"context"' in BUILDER_SYSTEM
    assert "old_string MUSS zeichengenau" in BUILDER_SYSTEM
