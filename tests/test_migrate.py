"""tests fuer werkstatt/migrate.py — DOC_CONVENTIONS.md §2/§3/§5/§6."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, "/opt/werkstatt")

from werkstatt.migrate import (
    MANIFEST_PFLICHT,
    VERBOTEN,
    check_manifest,
    check_pflicht,
    check_status,
    check_verbote,
    migriere,
)
from werkstatt.scaffold import PFLICHTDATEIEN, scaffold


# ---------- §2 Pflicht ----------

def test_pflicht_leer(tmp_path):
    bericht = check_pflicht(tmp_path)
    assert len(bericht) == 13
    assert all(s == "fehlt" for s in bericht.values())


def test_pflicht_vollstaendig(tmp_path):
    scaffold("demo", tmp_path)
    bericht = check_pflicht(tmp_path)
    # ADR-0001-Slug wird als ok (slug: ...) gefuehrt, sonst ok
    fehlend = [r for r, s in bericht.items() if s == "fehlt"]
    assert fehlend == []


def test_pflicht_adr_slug_akzeptiert(tmp_path):
    scaffold("demo", tmp_path)
    # ADR-0001.md durch slug-Variante ersetzen
    (tmp_path / "docs/adr/ADR-0001.md").unlink()
    (tmp_path / "docs/adr/ADR-0001-mein-slug.md").write_text("# x\n", encoding="utf-8")
    bericht = check_pflicht(tmp_path)
    assert bericht["docs/adr/ADR-0001.md"].startswith("ok (slug:")


# ---------- §3 Verbote ----------

def test_verbote_leer(tmp_path):
    assert check_verbote(tmp_path) == {}


def test_verbote_erkennt_docs_readme(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/README.md").write_text("# x\n", encoding="utf-8")
    funde = check_verbote(tmp_path)
    assert "docs/README.md" in funde
    assert "docs/index.md" in funde["docs/README.md"]


def test_verbote_glossary_ordner(tmp_path):
    (tmp_path / "docs/glossary").mkdir(parents=True)
    (tmp_path / "docs/glossary/index.md").write_text("# x\n", encoding="utf-8")
    (tmp_path / "docs/glossary.md").write_text("# x\n", encoding="utf-8")
    funde = check_verbote(tmp_path)
    assert "docs/glossary/" in funde


# ---------- §5 STATUS ----------

def test_status_kein_file(tmp_path):
    info, n = check_status(tmp_path)
    assert info == "kein STATUS.md"
    assert n == 0


def test_status_leer_marker(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/STATUS.md").write_text(
        "# Status\n\n## Offene Punkte\n\n(Noch keine Punkte.)\n",
        encoding="utf-8",
    )
    info, n = check_status(tmp_path)
    assert info == "ok"
    assert n == 0


def test_status_mit_op(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/STATUS.md").write_text(
        "# Status\n\n### OP-001: Test\n",
        encoding="utf-8",
    )
    info, n = check_status(tmp_path)
    assert info == "ok"
    assert n == 1


def test_status_format_fehler(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/STATUS.md").write_text(
        "# Status\n\nFreier Text ohne OP-NNN und ohne Leer-Marker.\n",
        encoding="utf-8",
    )
    info, _ = check_status(tmp_path)
    assert info.startswith("FORMAT")


# ---------- §6 Manifest ----------

def test_manifest_kein_manifest(tmp_path):
    bericht = check_manifest(tmp_path)
    assert all(s.startswith("n/a") for s in bericht.values())


def test_manifest_im_zielprojekt(tmp_path):
    proj = tmp_path / "projects"
    proj.mkdir()
    (proj / "demo.yaml").write_text(
        "project: demo\ndocs:\n  entry: AGENTS.md\n  status: docs/STATUS.md\n",
        encoding="utf-8",
    )
    bericht = check_manifest(tmp_path)
    assert bericht["entry"] == "ok"
    assert bericht["status"] == "ok"
    assert bericht["roadmap"] == "fehlt"


def test_manifest_fallback_nicht_auf_werkstatt(tmp_path):
    """Kritisch: leeres Projekt darf NICHT das security-ai-Manifest sehen."""
    bericht = check_manifest(tmp_path)
    # Wenn Fallback existierte, waeren hier 7/7 ok.
    assert all(s.startswith("n/a") for s in bericht.values())


# ---------- Gesamt-migriere ----------

def test_migriere_leeres_projekt_dry_run(tmp_path):
    bericht = migriere("demo", tmp_path, apply=False)
    assert bericht["project"] == "demo"
    assert len(bericht["verbote"]) == 0
    assert any(s == "fehlt" for s in bericht["pflicht"].values())
    assert "scaffold_bericht" not in bericht


def test_migriere_apply_legt_pflicht_an(tmp_path):
    bericht = migriere("demo", tmp_path, apply=True)
    assert "scaffold_bericht" in bericht
    fehlend = [r for r, s in bericht["pflicht"].items() if s == "fehlt"]
    assert fehlend == []


def test_migriere_verbotene_datei_wird_nur_gemeldet(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/README.md").write_text("# x\n", encoding="utf-8")
    bericht = migriere("demo", tmp_path, apply=True)
    # Datei bleibt bestehen (keine stillen Loeschungen)
    assert (tmp_path / "docs/README.md").is_file()
    assert "docs/README.md" in bericht["verbote"]
    assert "warnung" in bericht
