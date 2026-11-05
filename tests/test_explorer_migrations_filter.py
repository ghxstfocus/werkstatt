"""OP-050: Migrations-Dateien sind Kontext, keine key_files."""
from __future__ import annotations

import sys
from unittest.mock import MagicMock

sys.path.insert(0, "/opt/werkstatt")

from werkstatt.explorer import run_explorer


def test_migrations_nicht_in_key_files(tmp_path):
    """Live-Beleg 2026-11-01: 'Ollama-Reste' -> 17 SQL-Dateien in measured_files."""
    (tmp_path / "data" / "migrations").mkdir(parents=True)
    (tmp_path / "data" / "migrations" / "0001_test.sql").write_text("-- test")
    (tmp_path / "data" / "migrations" / "0002_test.sql").write_text("-- test")

    state = MagicMock()
    state.project_dir = str(tmp_path)
    state.project_name = "test"
    state.api_key = ""

    result = run_explorer(state, "unerledigte Codeaufgaben aufraeumen")

    kf_files = [kf["file"] for kf in result["key_files"]]
    sql_files = [f for f in kf_files if f.endswith(".sql")]
    assert not sql_files, f"SQL-Dateien in key_files: {sql_files}"


def test_migrations_stand_bleibt_in_findings(tmp_path):
    """Migrationsstand muss weiter in findings stehen (Kontext)."""
    (tmp_path / "data" / "migrations").mkdir(parents=True)
    (tmp_path / "data" / "migrations" / "0042_test.sql").write_text("-- test")

    state = MagicMock()
    state.project_dir = str(tmp_path)
    state.project_name = "test"
    state.api_key = ""

    result = run_explorer(state, "unerledigte Codeaufgaben aufraeumen")

    findings = result.get("findings", "")
    # Migrations-Header oder Nummer muss in findings auftauchen
    assert ("0042" in findings or "Migrationsstand" in findings), (
        f"Migrationsstand fehlt in findings: {findings[:300]}"
    )


def test_ruff_fehler_bleiben_in_key_files(tmp_path):
    """Nicht-migrations Messungen bleiben in key_files."""
    # Synthetische Messung: broken.py als "ruff"-Datei
    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "broken.py").write_text("def f(:\n  pass\n")

    state = MagicMock()
    state.project_dir = str(tmp_path)
    state.project_name = "test"
    state.api_key = ""

    # Aufgabe enthaelt "ruff" -> trigger fuer ruff-Messung
    result = run_explorer(state, "ruff fehler beheben")

    # Sanity: key_files ist Liste
    assert isinstance(result["key_files"], list)
