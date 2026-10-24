"""Tests fuer werkstatt/builder.py (Phase 6)."""
from __future__ import annotations

from unittest.mock import patch

from werkstatt.builder import run_builder
from werkstatt.state import RunState


def _state(tmp_path, tasks=None, api_key="fake"):
    return RunState(
        block_id="t", aufgabe="Baue Feature X", start_ts="",
        docs={}, agents={}, always={}, optional={},
        file_whitelist=[], api_key=api_key, budget={},
        agent_docs={}, project_dir=tmp_path, project_name="p"
    )


def test_builder_erstellt_patches(tmp_path):
    st = _state(tmp_path)
    st.tasks = [{"id": "t1", "name": "A", "description": "B"}]
    fake_json = '{"patches": [{"file": "a.py", "old_string": "x", "new_string": "y"}]}'

    class FakeReply:
        ok = True
        content = fake_json

    with patch("werkstatt.builder.ask_llm", return_value=FakeReply()):
        result = run_builder(st)
        assert result is True
        assert len(st.patches) == 1


def test_builder_ohne_key(tmp_path):
    st = _state(tmp_path, api_key="")
    st.tasks = [{"id": "t1"}]
    assert run_builder(st) is False


def test_builder_ohne_tasks(tmp_path):
    st = _state(tmp_path)
    st.tasks = []
    assert run_builder(st) is False


def test_builder_read_only_task_kein_patch(tmp_path):
    """M-306a: action='read' -> kein LLM-Call, kein Patch."""
    st = _state(tmp_path)
    st.tasks = [{"id": "t1", "name": "Bestandsaufnahme", "action": "read"}]

    with patch("werkstatt.builder.ask_llm") as mock_llm, \
         patch("werkstatt.builder.audit"):
        result = run_builder(st)
    assert result is True
    assert mock_llm.call_count == 0  # kein LLM-Call
    assert st.patches == []  # keine Patches


def test_builder_idempotent_bei_korrekter_datei(tmp_path):
    """M-317: existierende korrekte Zieldatei + action=create -> idempotent."""
    from werkstatt.builder import run_builder

    st = _state(tmp_path)
    st.tasks = [{"id": "t1", "name": "test_checks.py schreiben", "action": "create"}]

    # Datei existiert und ist syntaktisch korrekt
    (tmp_path / "test_checks.py").write_text(
        "def test_foo():\n    assert True\n", encoding="utf-8"
    )

    with patch("werkstatt.builder.audit") as mock_audit:
        result = run_builder(st)

    assert result is True
    assert st.patches == []
    # Audit-Ruf "builder_nichts_zu_tun"
    assert any(
        c[0][0] == "builder_nichts_zu_tun" for c in mock_audit.call_args_list
    )


def test_builder_reflection_bei_inkorrekter_datei(tmp_path):
    """M-316: existierende inkorrekte Zieldatei -> kein task_ok, Reflection."""
    from werkstatt.builder import run_builder

    st = _state(tmp_path)
    st.tasks = [{"id": "t1", "name": "test_checks.py schreiben", "action": "write"}]

    # Datei existiert, ist syntaktisch FALSCH
    (tmp_path / "test_checks.py").write_text(
        "def test_foo(:\n    assert True\n", encoding="utf-8"
    )

    with patch("werkstatt.builder.ask_llm") as mock_llm, \
         patch("werkstatt.builder.audit") as mock_audit:
        mock_llm.return_value = type("R", (), {"ok": True, "content": '{"patches": []}', "error": ""})()
        _result = run_builder(st)

    # Soll NICHT idempotent-True sein
    assert not any(
        c[0][0] == "builder_nichts_zu_tun" for c in mock_audit.call_args_list
    )


def test_builder_idempotent_bei_create_und_update(tmp_path):
    """M-318: Idempotenz-Check bei create+update (M-317 war zu strikt)."""
    from werkstatt.builder import run_builder

    st = _state(tmp_path)
    # Datei existiert + ist korrekt
    (tmp_path / "test_checks.py").write_text(
        "def test_foo():\n    assert True\n", encoding="utf-8"
    )

    # Task: action=create, Datei existiert -> idempotent (nichts zu tun)
    st.tasks = [{"id": "t1", "name": "test_checks.py schreiben", "action": "create"}]

    with patch("werkstatt.builder.audit") as mock_audit:
        result = run_builder(st)

    assert result is True
    assert st.patches == []
    assert any(
        c[0][0] == "builder_nichts_zu_tun" for c in mock_audit.call_args_list
    )


def test_builder_update_inkorrekte_datei_nutzt_patch_pfad(tmp_path):
    """M-318: Bei action=update + INKORREKTER Datei -> Patch-Pfad.

    Der Idempotenz-Check greift nur, wenn die Datei syntaktisch
    korrekt ist. Bei inkorrekter Datei muss der Builder durch den
    Patch-Pfad (kein builder_nichts_zu_tun, sondern echte Arbeit).
    """
    from werkstatt.builder import run_builder

    st = _state(tmp_path)
    # Datei existiert, aber ist syntaktisch FALSCH
    (tmp_path / "test_checks.py").write_text(
        "def test_foo(:\n    assert True\n", encoding="utf-8"
    )

    st.tasks = [{"id": "t1", "name": "test_checks.py reparieren", "action": "update"}]

    with patch("werkstatt.builder.ask_llm") as mock_llm, \
         patch("werkstatt.builder.audit") as mock_audit:
        mock_llm.return_value = type("R", (), {
            "ok": True, "content": '{"patches": []}', "error": ""
        })()
        result = run_builder(st)

    # Datei ist inkorrekt -> py_compile schlaegt fehl -> _all_ok=False
    # -> normaler Patch-Pfad -> LLM liefert leere Patches -> False
    assert result is False

    # KEIN "nichts zu tun" (weil Datei inkorrekt)
    assert not any(
        c[0][0] == "builder_nichts_zu_tun" for c in mock_audit.call_args_list
    )


def test_builder_idempotent_bei_update_mit_korrekter_datei(tmp_path):
    """M-318: action=update + Datei existiert + korrekt -> idempotent."""
    from werkstatt.builder import run_builder

    st = _state(tmp_path)
    st.tasks = [{"id": "t1", "name": "test_checks.py erweitern", "action": "update"}]

    # Datei existiert und ist syntaktisch korrekt
    (tmp_path / "test_checks.py").write_text(
        "def test_foo():\n    assert True\n", encoding="utf-8"
    )

    with patch("werkstatt.builder.audit") as mock_audit:
        result = run_builder(st)

    assert result is True
    assert st.patches == []
    assert any(
        c[0][0] == "builder_nichts_zu_tun" for c in mock_audit.call_args_list
    )
