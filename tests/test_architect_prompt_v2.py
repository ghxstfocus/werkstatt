"""Prototyp v2: Strukturierter Architect-User-Prompt (Env-Schalter)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, "/opt/werkstatt")

from werkstatt.architect import (
    _build_selbst_check_block,
    _reduce_entry,
    _reduce_roadmap,
    _reduce_status,
    build_architect_docs_section_v2,
)


# --- Reducer isoliert ---

def test_reduce_entry_behaelt_zweck_und_struktur():
    text = (
        "# AGENTS.md\n\n## Zweck\nEin Test-Projekt.\n\n"
        "## Struktur\n- apps/\n- core/\n\n"
        "## Hard-Rules\nLange Regeln...\n"
    )
    result = _reduce_entry(text)
    assert "## Zweck" in result
    assert "## Struktur" in result
    assert "Hard-Rules" not in result


def test_reduce_status_behaelt_offene_punkte():
    text = (
        "# Status\n\n## Kennzahlen\nZeug...\n\n"
        "## Offene Punkte\n### OP-001: Test\n- open\n\n"
        "## Delete-Zone\nTabelle...\n"
    )
    result = _reduce_status(text)
    assert "## Offene Punkte" in result
    assert "OP-001" in result
    assert "## Delete-Zone" not in result
    assert "## Kennzahlen" not in result


def test_reduce_roadmap_nur_phasen_header():
    text = (
        "# Roadmap\n\nEinleitung\n\n"
        "## Phase 1: Foo\nLanger Text...\n\n"
        "### Phase 22: Bar 🟡\nNoch mehr Text...\n\n"
        "## Verweise\n- link\n"
    )
    result = _reduce_roadmap(text)
    assert "## Phase 1" in result
    assert "### Phase 22" in result
    assert "Langer Text" not in result
    assert "## Verweise" not in result


def test_reduce_roadmap_max_800():
    # Viele Phasen-Header -> bleibt unter 800 Z.
    text = "\n".join(f"## Phase {i}: Titel" for i in range(100))
    result = _reduce_roadmap(text, max_chars=800)
    assert len(result) <= 800


# --- Gesamt-Builder ---

def test_build_architect_docs_section_v2_leer():
    assert build_architect_docs_section_v2({}) == ""
    assert build_architect_docs_section_v2(None) == ""


def test_build_v2_enthaelt_drei_sektionen():
    docs = {
        "entry": "# A\n\n## Zweck\nX\n\n## Struktur\nY\n\n## Hard-Rules\nZ\n",
        "status": "# S\n\n## Offene Punkte\nOP-001: foo\n",
        "roadmap": "# R\n\n## Phase 1: A\n\n## Phase 2: B\n",
    }
    result = build_architect_docs_section_v2(docs)
    assert "### PROJEKT-ENTRY" in result
    assert "### PROJEKT-STATUS" in result
    assert "### PROJEKT-ROADMAP" in result
    # Keine alten Marker
    assert "--- entry ---" not in result
    assert "--- status ---" not in result
    assert "--- roadmap ---" not in result


def test_build_v2_roadmap_unter_1000():
    # 200 Phasen -> Roadmap-Sektion bleibt trotzdem klein.
    roadmap = "\n".join(f"## Phase {i}: Titel" for i in range(200))
    docs = {"roadmap": roadmap}
    result = build_architect_docs_section_v2(docs)
    assert len(result) < 1500


# --- Selbst-Check ---

def test_selbst_check_block_format():
    result = _build_selbst_check_block()
    assert "## SELBST-CHECK" in result
    # 5 Check-Punkte (Bindestrich-Zeilen)
    assert result.count("\n- ") == 5
    assert "API steht" in result
    assert "Migrationsnummer" in result


# --- Env-Schalter in planner.py (statischer Check) ---

def test_planner_hat_env_schalter():
    src = Path("/opt/werkstatt/werkstatt/planner.py").read_text(encoding="utf-8")
    assert "WERKSTATT_ARCHITECT_PROMPT" in src
    assert '"v2"' in src
    assert "build_architect_docs_section_v2" in src
    assert "_build_selbst_check_block" in src


def test_alte_user_content_form_noch_da():
    """Der alte Pfad bleibt als else-Zweig erhalten (kein Zwang zu v2)."""
    src = Path("/opt/werkstatt/werkstatt/planner.py").read_text(encoding="utf-8")
    assert 'f"Aufgabe: {aufgabe}' in src
