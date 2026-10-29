"""K61a: task_files-Normalisierung (Dateiname -> voller Pfad).

Problem (Live 2026-10-29 14:16): Architect plante task_files=
["routes_state.py"], Builder fand die Datei nicht (sie liegt unter
apps/dashboard/routes_state.py). _normalisiere_task_files korrigiert
anhand explorer_ctx["key_files"].

Regeln:
- task_files mit "/" -> unveraendert.
- Basisname eindeutig in key_files -> auf vollen Pfad korrigiert.
- Basisname mehrdeutig -> unveraendert + audit "planner_task_files_mehrdeutig".
- Basisname nicht in key_files -> unveraendert.
"""

from unittest.mock import patch

from werkstatt.planner import _normalisiere_task_files


def test_k61a_eindeutig_korrigiert():
    """routes_state.py -> apps/dashboard/routes_state.py (eindeutig)."""
    tasks = [{"id": "t5", "task_files": ["routes_state.py"]}]
    ctx = {
        "key_files": [
            {"file": "apps/dashboard/routes_state.py"},
            {"file": "core/config.py"},
        ]
    }
    with patch("werkstatt.planner.audit") as mock_audit:
        result = _normalisiere_task_files(tasks, ctx, "/tmp", "p")
    assert result[0]["task_files"] == ["apps/dashboard/routes_state.py"]
    audit_kinds = [c[0][0] for c in mock_audit.call_args_list]
    assert "planner_task_files_korrigiert" in audit_kinds


def test_k61a_mehrdeutig_unveraendert():
    """audit_reader.py existiert 3x -> fail-closed, unveraendert."""
    tasks = [{"id": "t1", "task_files": ["audit_reader.py"]}]
    ctx = {
        "key_files": [
            {"file": "audit_reader.py"},
            {"file": "core/audit_reader.py"},
            {"file": "core/reporting/audit_reader.py"},
        ]
    }
    with patch("werkstatt.planner.audit") as mock_audit:
        result = _normalisiere_task_files(tasks, ctx, "/tmp", "p")
    assert result[0]["task_files"] == ["audit_reader.py"]  # unveraendert
    audit_kinds = [c[0][0] for c in mock_audit.call_args_list]
    assert "planner_task_files_mehrdeutig" in audit_kinds


def test_k61a_pfad_schon_da_unveraendert():
    """Voller Pfad -> unveraendert, kein Audit."""
    tasks = [{"id": "t1", "task_files": ["apps/dashboard/routes_state.py"]}]
    ctx = {"key_files": [{"file": "apps/dashboard/routes_state.py"}]}
    with patch("werkstatt.planner.audit") as mock_audit:
        result = _normalisiere_task_files(tasks, ctx, "/tmp", "p")
    assert result[0]["task_files"] == ["apps/dashboard/routes_state.py"]
    audit_kinds = [c[0][0] for c in mock_audit.call_args_list]
    assert "planner_task_files_korrigiert" not in audit_kinds


def test_k61a_nicht_in_key_files_unveraendert():
    """Basisname nicht in key_files -> unveraendert, kein Audit."""
    tasks = [{"id": "t1", "task_files": ["unbekannt.py"]}]
    ctx = {"key_files": [{"file": "core/config.py"}]}
    with patch("werkstatt.planner.audit") as mock_audit:
        result = _normalisiere_task_files(tasks, ctx, "/tmp", "p")
    assert result[0]["task_files"] == ["unbekannt.py"]
    audit_kinds = [c[0][0] for c in mock_audit.call_args_list]
    assert "planner_task_files_korrigiert" not in audit_kinds
    assert "planner_task_files_mehrdeutig" not in audit_kinds
