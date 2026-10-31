"""Manifest/Schema enthalten DOC_CONVENTIONS.md §6-Pflichtfelder.

Plus Schutz: DOC_CONVENTIONS.md §3 darf nicht durch Cross-Reference-Sed
korrumpiert werden (Regression-Fall 2026-10-31).
"""
from __future__ import annotations
from pathlib import Path

import yaml

PFLICHT = [
    "entry", "status", "roadmap", "architecture",
    "conventions", "adr_index", "glossary",
]
BASE = Path("/opt/werkstatt")

# Was §3 als verboten listet, unveraendert — diese Strings MUESSEN im Text stehen.
VERBOTEN_ORIGINAL = [
    "docs/README.md",
    "docs/INDEX.md",
    "docs/DECISIONS.md",
    "docs/ERLEDIGT.md",
    "docs/OFFENE-BLOECKE.md",
    "docs/PROGRESS.md",
    "projects/<name>.phase.yaml",
    "docs/glossary/",
    "Bau-Handoff-Archiv.md",
]


def _load(rel: str) -> dict:
    return yaml.safe_load((BASE / rel).read_text(encoding="utf-8"))


def test_security_ai_manifest():
    cfg = _load("projects/security-ai.yaml")
    for feld in PFLICHT:
        assert feld in cfg.get("docs", {}), f"docs.{feld} fehlt"


def test_template():
    cfg = _load("projects/_template.yaml")
    for feld in PFLICHT:
        assert feld in cfg.get("docs", {}), f"docs.{feld} fehlt"


def test_schema():
    schema = _load("schemas/projekt.yaml")
    schluessel = schema["felder"]["docs"]["schluessel"]
    for feld in PFLICHT:
        assert feld in schluessel, f"schemas/projekt.yaml: docs.{feld}"


def test_manifest_hat_root_doku():
    """Root-Dateien im Manifest: verhindert docs/PROGRESS.md-Duplikat."""
    for rel in ("projects/security-ai.yaml", "projects/_template.yaml"):
        docs = _load(rel).get("docs", {})
        assert "progress" in docs, f"{rel}: docs.progress fehlt"
        assert "changelog" in docs, f"{rel}: docs.changelog fehlt"


def test_schema_hat_progress_und_changelog():
    schluessel = _load("schemas/projekt.yaml")["felder"]["docs"]["schluessel"]
    assert "progress" in schluessel
    assert "changelog" in schluessel


def test_doc_conventions_verbietet_docs_progress():
    """docs/PROGRESS.md ist explizit in §3 gelistet."""
    text = (BASE / "docs/DOC_CONVENTIONS.md").read_text(encoding="utf-8")
    assert "`docs/PROGRESS.md`" in text
    assert "Duplikat zur Root-PROGRESS" in text


def test_doc_conventions_verbotene_namen_unveraendert():
    """Regression: Cross-Reference-Sed darf §3-Verbotsnamen NICHT ersetzen."""
    text = (BASE / "docs/DOC_CONVENTIONS.md").read_text(encoding="utf-8")
    # Nur in §3 nachsehen
    start = text.find("## 3. Verbotene Dateien")
    end = text.find("## 4. Sprach-Regel")
    assert start > 0 and end > start
    section = text[start:end]
    for name in VERBOTEN_ORIGINAL:
        assert name in section, (
            f"§3-Verbotsname fehlt: {name!r} — Tabelle wurde korrumpiert"
        )
