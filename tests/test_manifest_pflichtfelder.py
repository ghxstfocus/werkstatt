"""Phase 5f — Manifest/Schema enthalten DOC_CONVENTIONS.md §6-Pflichtfelder."""
from __future__ import annotations
from pathlib import Path

import yaml

PFLICHT = [
    "entry", "status", "roadmap", "architecture",
    "conventions", "adr_index", "glossary",
]
BASE = Path("/opt/werkstatt")


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
    """Haertung gegen docs/PROGRESS.md-Duplikat: Root-Dateien im Manifest."""
    for rel in ("projects/security-ai.yaml", "projects/_template.yaml"):
        docs = _load(rel).get("docs", {})
        assert "progress" in docs, f"{rel}: docs.progress fehlt"
        assert "changelog" in docs, f"{rel}: docs.changelog fehlt"


def test_doc_conventions_verbietet_docs_progress():
    text = (BASE / "docs/DOC_CONVENTIONS.md").read_text(encoding="utf-8")
    assert "docs/PROGRESS.md" in text
    assert "Duplikat zur Root-PROGRESS.md" in text or "Root-PROGRESS" in text


def test_schema_hat_progress_und_changelog():
    schluessel = _load("schemas/projekt.yaml")["felder"]["docs"]["schluessel"]
    assert "progress" in schluessel
    assert "changelog" in schluessel
