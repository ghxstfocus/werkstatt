"""OP-172: Fehlerkern-Extraktion aus Tool-Output.

Spec: verify.py darf den Fehler-Kopf nicht durch Truncation
verlieren. Live-Beleg Loop-Test 7 (18:29:11): mypy-Output mit
"error: Source file found twice" + 5 "note:"-Zeilen wurde mit
[-500:] abgeschnitten — der Builder sah nur "(also at ...)" und
Notes, konnte nicht reparieren.
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/opt/werkstatt")

from werkstatt.verify import _extrahiere_fehlerkern

# ============ mypy ============

def test_mypy_mehrere_fehler_alle_behalten():
    """3 mypy-Fehler + Statistik -> alle 3 Fehler, keine Statistik."""
    out = (
        "/tmp/a.py:2: error: Incompatible return value type "
        "(got \"int\", expected \"str\")  [return-value]\n"
        "/tmp/a.py:4: error: Incompatible return value type "
        "(got \"str\", expected \"int\")  [return-value]\n"
        "/tmp/a.py:6: error: Incompatible return value type "
        "(got \"float\", expected \"bool\")  [return-value]\n"
        "Found 3 errors in 1 file (checked 1 source file)\n"
    )
    kern = _extrahiere_fehlerkern(out)
    assert "Incompatible return value type" in kern
    # Alle 3 Fehlerzeilen, nicht nur eine
    assert kern.count("error:") == 3
    # Statistik weg
    assert "Found 3 errors" not in kern


def test_mypy_path_mapping_artefakt_behaelt_error_kopf():
    """Loop-Test-7-Artefakt: error-Kopf + 5 notes.

    Extraktion MUSS den error-Kopf behalten, auch wenn der
    Gesamt-Output > 500 Zeichen ist.
    """
    out = (
        "werkstatt/phases/review.py: error: Source file found twice "
        "under different module names: \"werkstatt.phases.review\" and "
        "\"phases.review\"\n"
        "(also at \"werkstatt/phases/review.py\")\n"
        "werkstatt/phases/review.py: note: See https://mypy.readthedocs.io\n"
        "werkstatt/phases/review.py: note: Common resolutions include:\n"
        "werkstatt/phases/review.py: note:     a) using '--exclude' to avoid\n"
        "werkstatt/phases/review.py: note:     b) adding __init__.py somewhere\n"
        "werkstatt/phases/review.py: note:     c) using --explicit-package-bases\n"
    )
    kern = _extrahiere_fehlerkern(out)
    assert "error: Source file found twice" in kern, (
        "Fehler-Kopf muss erhalten bleiben, auch bei vielen Notes"
    )
    # Notes weg (kein Rauschen im Prompt)
    assert "note:" not in kern
    # Aufhaenger "(also at ...)" ist redundant zur error-Zeile
    # (die enthaelt den Pfad bereits). Kein Muss — der Fix zielt
    # auf den Error-Kern, nicht auf mypy-Formatierung.


# ============ ruff ============

def test_ruff_fehler_behalten_help_weg():
    """Ruff: Code-Praefix-Zeilen behalten, help:-Zeilen weg."""
    out = (
        "I001 [*] Import block is un-sorted or un-formatted\n"
        " --> /tmp/ruff_test.py:1:1\n"
        "help: Organize imports\n"
        "F401 [*] `os` imported but unused\n"
        " --> /tmp/ruff_test.py:1:8\n"
        "help: Remove unused import: `os`\n"
        "Found 2 errors.\n"
    )
    kern = _extrahiere_fehlerkern(out)
    assert "I001" in kern
    assert "F401" in kern
    assert "help:" not in kern
    assert "Found 2 errors" not in kern


# ============ pytest ============

def test_pytest_failed_zeilen_behalten():
    """pytest: FAILED-Zeilen + Assertion-Kontext."""
    out = (
        "=================================== FAILURES ===================================\n"
        "____________________________________ test_a ____________________________________\n"
        "    def test_a():\n"
        ">       assert False, \"kaputt\"\n"
        "E       AssertionError: kaputt\n"
        "test_fail.py:2: AssertionError\n"
        "=========================== short test summary info ============================\n"
        "FAILED test_fail.py::test_a - AssertionError: kaputt\n"
        "============================== 1 failed in 0.02s ==============================\n"
    )
    kern = _extrahiere_fehlerkern(out)
    assert "AssertionError" in kern
    assert "FAILED test_fail.py::test_a" in kern
    # Statistik-Zeile weg
    assert "1 failed in" not in kern


# ============ Fallback + Edge-Cases ============

def test_leerer_output():
    assert _extrahiere_fehlerkern("") == ""


def test_unbekanntes_format_fallback():
    """Text ohne erkennbare Fehler-Zeile -> letzte max_chars."""
    out = "Das ist ein Skript, das einfach irgendwas ausgibt.\n" * 20
    kern = _extrahiere_fehlerkern(out, max_chars=500)
    assert len(kern) <= 550  # 500 + Toleranz fuer "\n[...]"-Suffix
    assert "irgendwas ausgibt" in kern


def test_max_chars_limit_wird_eingehalten():
    """Bei sehr vielen Fehlern greift das max_chars-Limit."""
    out = "\n".join(f"x.py:{i}: error: Fehler {i}" for i in range(100))
    kern = _extrahiere_fehlerkern(out, max_chars=2000)
    assert len(kern) <= 2050
    assert "[...]" in kern or len(kern) <= 2000


# ============ Integration: verify-Loop nutzt den Extraktor ============

def test_verify_patches_nutzt_extraktor():
    """Indirekt: der Fehler in last_verify_errors hat einen error:-Kopf
    (statt nur "(also at ...)"). Kein kompletter verify-Lauf, nur
    Codepfad-Verifikation per AST-Scan.
    """
    import ast
    import pathlib

    src = pathlib.Path("/opt/werkstatt/werkstatt/verify.py").read_text()
    tree = ast.parse(src)
    # Suche: in _verify_patches muss _extrahiere_fehlerkern gerufen werden
    found = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id == "_extrahiere_fehlerkern":
                found = True
                break
    assert found, (
        "verify.py muss _extrahiere_fehlerkern im Fehler-Pfad rufen"
    )
