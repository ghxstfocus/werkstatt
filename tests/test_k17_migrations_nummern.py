"""K17: Architect bekommt Migrationsstand deterministisch im Kontext."""
from pathlib import Path

from werkstatt.planner import ARCHITECT_SYSTEM, _migrations_stand


def test_prompt_enthaelt_migrations_regel():
    assert "MIGRATIONS-NUMMERN" in ARCHITECT_SYSTEM
    assert "hoechste vorhandene Nummer +1" in ARCHITECT_SYSTEM
    assert "Nummern-Kollision" in ARCHITECT_SYSTEM


def test_prompt_bewahrt_bestehende_k15b_regeln():
    # Regression: K15b-Test darf nicht brechen.
    assert "PRO DATEI EIN BLOCK" in ARCHITECT_SYSTEM
    assert "50-150 Zeilen" in ARCHITECT_SYSTEM


def test_migrations_stand_leer_ohne_ordner(tmp_path: Path):
    assert _migrations_stand(tmp_path) == ""


def test_migrations_stand_leer_ohne_sql(tmp_path: Path):
    (tmp_path / "data" / "migrations").mkdir(parents=True)
    assert _migrations_stand(tmp_path) == ""


def test_migrations_stand_listet_und_empfiehlt(tmp_path: Path):
    mdir = tmp_path / "data" / "migrations"
    mdir.mkdir(parents=True)
    for n in ("0015_tool_permissions.sql", "0016_guardrails.sql",
              "0017_guardrail_permissions.sql", "0018_guardrail_permissions.sql"):
        (mdir / n).write_text("-- noop\n")
    out = _migrations_stand(tmp_path)
    assert "<migrationsstand>" in out
    assert "Hoechste vorhandene Nummer: 0018" in out
    assert "Fuer neue Migration: 0019" in out
    assert "NICHT 0018 wiederverwenden" in out


def test_migrations_stand_ignoriert_nicht_numerische(tmp_path: Path):
    mdir = tmp_path / "data" / "migrations"
    mdir.mkdir(parents=True)
    (mdir / "README.sql").write_text("-- keine nr\n")
    (mdir / "0010_a.sql").write_text("-- noop\n")
    out = _migrations_stand(tmp_path)
    assert "Hoechste vorhandene Nummer: 0010" in out
