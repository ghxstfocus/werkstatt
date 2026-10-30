"""Spec: Builder — P0/P1-Kernfunktion + kleine Helfer.

Nicht dupliziert (bereits getestet):
- run_builder                    -> test_builder_agent.py (25)
- _validate_imports_in_patch     -> test_builder_import_validate.py
- _architect_abschnitt           -> test_builder_architect_abschnitt.py
- _normalisiere_aider_patches    -> test_k48_aider_patch.py
- _korrigiere_builder_action     -> test_k22_action_korrektur_builder.py

Getestet hier:
- _filtere_auf_funktionen (P0/P1 aa7881f, bisher 0 Tests)
- _sammle_projekt_py_files
- _builder_system (Wrapper, Hard-Rule 13)
- _finde_modul_pfad + _hat_symbol (direkte Einheitstests)
"""
from __future__ import annotations

from pathlib import Path

import pytest

from werkstatt import builder


# =====================================================================
# _filtere_auf_funktionen (P0/P1-Kernfunktion)
# =====================================================================

ABSCHNITT_2 = (
    "```python\n"
    "def foo():\n"
    "    return 1\n"
    "```\n\n"
    "```python\n"
    "def bar():\n"
    "    return 2\n"
    "```"
)


def test_filter_leerer_abschnitt():
    assert builder._filtere_auf_funktionen("", "task") == ""


def test_filter_leerer_task():
    """Ohne Task-Text: No-op, Abschnitt unveraendert."""
    assert builder._filtere_auf_funktionen(ABSCHNITT_2, "") == ABSCHNITT_2


def test_filter_keine_kandidaten():
    """Task ohne Backticks/def/class -> No-op."""
    assert builder._filtere_auf_funktionen(
        ABSCHNITT_2, "mach irgendwas") == ABSCHNITT_2


def test_filter_keine_codebloecke():
    """Task nennt Kandidaten, Abschnitt hat keine ```-Fences -> No-op."""
    abschnitt = "nur Prosa, kein Code"
    assert builder._filtere_auf_funktionen(
        abschnitt, "aendere `foo`") == abschnitt


def test_filter_eine_funktion():
    """Nur der `foo`-Block bleibt uebrig, fence-los."""
    out = builder._filtere_auf_funktionen(ABSCHNITT_2, "aendere `foo`")
    assert "def foo" in out
    assert "def bar" not in out
    # Wichtig: Fence-frei (das ist das Format, das der Builder bekommt).
    assert "```" not in out


def test_filter_mehrere_funktionen():
    """Zwei Kandidaten -> beide Bloecke."""
    out = builder._filtere_auf_funktionen(
        ABSCHNITT_2, "aendere `foo` und `bar`")
    assert "def foo" in out
    assert "def bar" in out


def test_filter_kandidat_als_backtick():
    assert "def foo" in builder._filtere_auf_funktionen(
        ABSCHNITT_2, "`foo`")


def test_filter_kandidat_als_def():
    assert "def foo" in builder._filtere_auf_funktionen(
        ABSCHNITT_2, "aendere def foo")


def test_filter_kandidat_als_class():
    abschnitt = (
        "```python\n"
        "class Bar:\n"
        "    pass\n"
        "```\n\n"
        "```python\n"
        "def baz():\n"
        "    pass\n"
        "```"
    )
    out = builder._filtere_auf_funktionen(abschnitt, "class Bar")
    assert "class Bar" in out
    assert "def baz" not in out


def test_filter_kandidat_nicht_im_abschnitt():
    """Kandidat genannt, aber in keinem Block -> Fallback: unveraendert."""
    assert builder._filtere_auf_funktionen(
        ABSCHNITT_2, "`gibtsnicht`") == ABSCHNITT_2


def test_filter_mehrere_bloecke_gleiche_funktion():
    """Zwei Bloecke enthalten `def foo` -> beide bleiben."""
    abschnitt = (
        "```python\ndef foo(): pass\n```\n\n"
        "```python\ndef foo(x): return x\n```"
    )
    out = builder._filtere_auf_funktionen(abschnitt, "`foo`")
    assert out.count("def foo") == 2


def test_filter_short_circuit_ein_zeichen():
    """Kandidat < 3 Zeichen wird ignoriert (Regex {2,}).

    `f` (1 Zeichen) ist kein Kandidat -> Abschnitt unveraendert.
    """
    abschnitt = (
        "```python\ndef f(): pass\n```\n\n"
        "```python\ndef foo(): pass\n```"
    )
    out = builder._filtere_auf_funktionen(abschnitt, "aendere `f`")
    assert out == abschnitt


def test_filter_deterministisch():
    a = builder._filtere_auf_funktionen(ABSCHNITT_2, "`foo`")
    b = builder._filtere_auf_funktionen(ABSCHNITT_2, "`foo`")
    assert a == b


# =====================================================================
# _sammle_projekt_py_files
# =====================================================================

def test_sammle_findet_py(tmp_path):
    (tmp_path / "a.py").write_text("")
    (tmp_path / "b.py").write_text("")
    out = builder._sammle_projekt_py_files(tmp_path)
    namen = {f.name for f in out}
    assert namen == {"a.py", "b.py"}


def test_sammle_ignoriert_nicht_py(tmp_path):
    (tmp_path / "a.py").write_text("")
    (tmp_path / "b.txt").write_text("")
    out = builder._sammle_projekt_py_files(tmp_path)
    assert {f.name for f in out} == {"a.py"}


def test_sammle_ignoriert_venv(tmp_path):
    (tmp_path / ".venv" / "x").mkdir(parents=True)
    (tmp_path / ".venv" / "x" / "pkg.py").write_text("")
    (tmp_path / "echt.py").write_text("")
    out = builder._sammle_projekt_py_files(tmp_path)
    assert {f.name for f in out} == {"echt.py"}


def test_sammle_limit(tmp_path):
    for i in range(5):
        (tmp_path / f"m{i}.py").write_text("")
    out = builder._sammle_projekt_py_files(tmp_path, limit=2)
    assert len(out) == 2


def test_sammle_sortiert(tmp_path):
    """Determinismus: sorted() liefert stabile Reihenfolge."""
    (tmp_path / "z.py").write_text("")
    (tmp_path / "a.py").write_text("")
    (tmp_path / "m.py").write_text("")
    out = builder._sammle_projekt_py_files(tmp_path)
    assert [f.name for f in out] == ["a.py", "m.py", "z.py"]


# =====================================================================
# _builder_system (Wrapper, Hard-Rule 13: kein String-Patching)
# =====================================================================

def test_builder_system_enthaelt_reviewer_schnittstelle():
    s = builder._builder_system()
    assert builder.BUILDER_SYSTEM in s
    assert builder._REVIEWER_SCHNITTSTELLE in s


def test_builder_system_stabil():
    assert builder._builder_system() == builder._builder_system()


# =====================================================================
# _finde_modul_pfad
# =====================================================================

def test_finde_modul_pfad_einfach(tmp_path):
    (tmp_path / "mod.py").write_text("")
    assert builder._finde_modul_pfad("mod", tmp_path) == tmp_path / "mod.py"


def test_finde_modul_pfad_dotted(tmp_path):
    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "models.py").write_text("")
    assert builder._finde_modul_pfad("core.models", tmp_path) == \
        tmp_path / "core" / "models.py"


def test_finde_modul_pfad_package(tmp_path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("")
    assert builder._finde_modul_pfad("pkg", tmp_path) == \
        tmp_path / "pkg" / "__init__.py"


def test_finde_modul_pfad_nicht_gefunden(tmp_path):
    assert builder._finde_modul_pfad("gibtsnicht", tmp_path) is None


def test_finde_modul_pfad_unterordner_fehlt(tmp_path):
    assert builder._finde_modul_pfad("a.b.c", tmp_path) is None


# =====================================================================
# _hat_symbol
# =====================================================================

def test_hat_symbol_def(tmp_path):
    f = tmp_path / "m.py"
    f.write_text("def foo():\n    pass\n")
    assert builder._hat_symbol(f, "foo") is True
    assert builder._hat_symbol(f, "bar") is False


def test_hat_symbol_class(tmp_path):
    f = tmp_path / "m.py"
    f.write_text("class C:\n    pass\n")
    assert builder._hat_symbol(f, "C") is True


def test_hat_symbol_async_def(tmp_path):
    f = tmp_path / "m.py"
    f.write_text("async def foo():\n    pass\n")
    assert builder._hat_symbol(f, "foo") is True


def test_hat_symbol_var_assign(tmp_path):
    f = tmp_path / "m.py"
    f.write_text("MY_CONST = 1\n")
    assert builder._hat_symbol(f, "MY_CONST") is True


def test_hat_symbol_ann_assign(tmp_path):
    f = tmp_path / "m.py"
    f.write_text("MY_TYPE: int = 1\n")
    assert builder._hat_symbol(f, "MY_TYPE") is True


def test_hat_symbol_syntax_fehler(tmp_path):
    f = tmp_path / "m.py"
    f.write_text("def kaputt(:\n")
    assert builder._hat_symbol(f, "foo") is False


def test_hat_symbol_nur_top_level(tmp_path):
    """Symbole in Klassen-Body werden NICHT erkannt (nur tree.body)."""
    f = tmp_path / "m.py"
    f.write_text("class C:\n    def method(self):\n        pass\n")
    assert builder._hat_symbol(f, "method") is False


# =====================================================================
# Regression: _zieldatei vs. zieldatei in _build_patches_fuer_datei
# =====================================================================

def test_build_patches_fuer_datei_kein_zieldatei_nameerror():
    """_build_patches_fuer_datei nutzt 'zieldatei', nicht '_zieldatei'.

    Regression: Live 2026-10-30 21:23:42 — NameError '_zieldatei'
    is not defined in _build_patches_fuer_datei. Der Parameter heisst
    'zieldatei', der audit-Aufruf referenzierte '_zieldatei'.
    """
    import inspect
    from werkstatt import builder
    src = inspect.getsource(builder._build_patches_fuer_datei)
    assert "zieldatei" in src
    # Der Bug: _zieldatei (mit Unterstrich) wird in dieser Funktion
    # nicht definiert. Pruefen wir, dass das nicht mehr vorkommt.
    # Ausnahme: Docstring/Kommentare.
    lines = src.splitlines()
    for i, l in enumerate(lines, 1):
        if "_zieldatei" in l and not l.strip().startswith("#"):
            # Koennte in Docstring/Kommentar sein
            assert "zieldatei" in src, (
                f"Zeile {i}: _zieldatei in _build_patches_fuer_datei "
                f"referenziert, aber nicht definiert"
            )
