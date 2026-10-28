"""K17b: Migrations-Kollision deterministisch (Gate + Prompt)."""
from pathlib import Path

from werkstatt.planner import (
    _migrations_stand,
    _pruefe_migrations_kollision,
)

# --- Ebene 1: Prompt (pflicht-Block, nur Fakten) ---

def test_migrationsstand_ist_pflicht_block(tmp_path: Path):
    mdir = tmp_path / "data" / "migrations"
    mdir.mkdir(parents=True)
    for n in ("0015_tool_permissions.sql", "0016_guardrails.sql",
              "0017_guardrail_permissions.sql", "0018_guardrail_permissions.sql"):
        (mdir / n).write_text("-- noop\n")
    out = _migrations_stand(tmp_path)
    assert '<migrationsstand pflicht="true">' in out
    assert "Hoechste vorhandene Nummer: 0018" in out
    assert "Naechste freie Nummer: 0019" in out
    assert "VERBOTEN (bereits belegt):" in out
    # Sperrliste enthaelt 0018_* und 0017_*
    assert "0018_*" in out
    assert "0017_*" in out


def test_migrationsstand_kein_langlisting(tmp_path: Path):
    """K17b: nur Fakten, keine vollstaendige Datei-Liste."""
    mdir = tmp_path / "data" / "migrations"
    mdir.mkdir(parents=True)
    for i in range(1, 20):
        (mdir / f"{i:04d}_x.sql").write_text("-- noop\n")
    out = _migrations_stand(tmp_path)
    # Nur letzte 5 gesperrt, nicht alle 19 aufgelistet.
    assert out.count("_x.sql") == 0, "Dateinamen sollen NICHT gelistet werden"


# --- Ebene 2: Gate ---

def _mk_migrations(tmp_path: Path) -> Path:
    mdir = tmp_path / "data" / "migrations"
    mdir.mkdir(parents=True)
    for n in ("0017_guardrail_permissions.sql",
              "0018_guardrail_permissions.sql"):
        (mdir / n).write_text("-- noop\n")
    return mdir


def test_gate_erkennt_kollision(tmp_path: Path):
    _mk_migrations(tmp_path)
    prosa = "## data/migrations/0017_sofortmassnahme.sql\nTabelle anlegen."
    k = _pruefe_migrations_kollision(prosa, tmp_path)
    assert len(k) == 1
    assert k[0]["nummer"] == "0017"
    assert k[0]["existiert"] is True


def test_gate_keine_kollision_naechste_frei(tmp_path: Path):
    _mk_migrations(tmp_path)
    prosa = "## data/migrations/0019_sofortmassnahme.sql\nTabelle anlegen."
    k = _pruefe_migrations_kollision(prosa, tmp_path)
    assert k == []


def test_gate_kein_migrations_ordner():
    """Ordner fehlt -> keine Kollision, keine Exception."""
    from tempfile import TemporaryDirectory
    with TemporaryDirectory() as td:
        prosa = "## data/migrations/0017_x.sql\n"
        assert _pruefe_migrations_kollision(prosa, td) == []


def test_gate_mehrfach_kollision(tmp_path: Path):
    _mk_migrations(tmp_path)
    prosa = (
        "Plan A: data/migrations/0017_a.sql\n"
        "Plan B: data/migrations/0018_b.sql\n"
        "Plan C: data/migrations/0019_c.sql\n"
    )
    k = _pruefe_migrations_kollision(prosa, tmp_path)
    assert {x["nummer"] for x in k} == {"0017", "0018"}


def test_gate_ignoriert_ohne_pfad_prefix(tmp_path: Path):
    _mk_migrations(tmp_path)
    # '0017_x.sql' ohne 'data/migrations/'-Prefix soll NICHT matchen.
    prosa = "Die Datei 0017_x.sql existiert nicht."
    assert _pruefe_migrations_kollision(prosa, tmp_path) == []


# --- Ebene 3 + 4: Gate + Feedback + Audit sind im Aufrufer ---
# Vollstaendige Integration mit Mock waere teuer; wir pruefen hier die
# Bausteine. Der Aufruf in _run_phase_and_plan wird durch die
# Kombination von _pruefe_migrations_kollision + vorhandenem
# last_planner_info-Feedback-Mechanismus abgedeckt (siehe M-349d).
