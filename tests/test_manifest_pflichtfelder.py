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
