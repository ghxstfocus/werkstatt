"""OP-064b: Deterministischer Antipattern-Scanner.

Kein LLM. Kein subprocess. Unter 100 ms. Scannt Patch-JSON
(``state.patches``) auf Muster, die dazu dienen, Verify-Gates zu
umgehen statt den Code zu reparieren.

Der Scanner liefert nur Treffer. Ob ein Treffer ein Veto ausloest,
entscheidet die Pipeline anhand der harten Verify-Zone
(verify.json-Stages mit ``hart: true``) — nicht der Scanner.

Design-Referenz: fakegreen (deterministischer Diff-Scanner).
"""
from __future__ import annotations

import ast
from dataclasses import dataclass


@dataclass(frozen=True)
class AntiPattern:
    """Ein einzelner Treffer. ``kind`` ist die Regel-ID, ``file`` die
    betroffene Datei, ``sample`` der getroffene Ausschnitt."""
    kind: str
    file: str
    sample: str


# --- Hilfsfunktionen ---

_SHELL_EXT = (".sh", ".bash", ".zsh")
_MAKEFILE_NAMES = ("Makefile", "makefile", "GNUmakefile")
_VERGLEICHS_OPS = ("==", "!=", "<=", ">=", " is ", " is not ",
                   " in ", " not in ", " < ", " > ")


def _ist_shell_kontext(file: str) -> bool:
    f = file.replace("\\", "/")
    if f.endswith(_SHELL_EXT):
        return True
    base = f.rsplit("/", 1)[-1]
    if base in _MAKEFILE_NAMES:
        return True
    return bool(base.endswith(".mk"))


def _ist_test_datei(file: str) -> bool:
    f = file.replace("\\", "/")
    base = f.rsplit("/", 1)[-1]
    if not base.endswith(".py"):
        return False
    if base.startswith("test_") or base.endswith("_test.py"):
        return True
    return bool("/tests/" in f or f.startswith("tests/"))


def _hat_vergleich(zeile: str) -> bool:
    s = zeile.strip()
    if not s.startswith("assert"):
        return False
    return any(op in s for op in _VERGLEICHS_OPS)


def _zaehle_assert_mit_vergleich(text: str) -> int:
    return sum(1 for z in text.splitlines() if _hat_vergleich(z))


def _fallback_audit_zaehlung(text: str) -> list[str]:
    """Grobe Klammer-Zaehlung fuer nicht-parsebaren Text.

    Sucht ALLE ``audit(``-Vorkommen. Ist ein Aufruf nicht geschlossen
    (unvollstaendige Klammer), wird er uebersprungen — ein
    unvollstaendiges Fragment ist kein belastbarer Befund.
    """
    samples: list[str] = []
    start = 0
    while True:
        idx = text.find("audit(", start)
        if idx < 0:
            break
        depth = 1
        commas = 0
        i = idx + len("audit(")
        in_string: str | None = None
        escaped = False
        geschlossen = False
        while i < len(text):
            ch = text[i]
            if in_string is not None:
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == in_string:
                    in_string = None
            elif ch in ("'", '"'):
                in_string = ch
            elif ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    geschlossen = True
                    i += 1
                    break
            elif ch == "," and depth == 1:
                commas += 1
            i += 1
        if geschlossen:
            arg_count = commas + 1
            if arg_count < 4:
                samples.append(f"audit(...) mit {arg_count} Args")
        start = idx + len("audit(")
    return samples


def _pruefe_audit_signatur(text: str) -> list[str]:
    """Findet ``audit(...)``-Aufrufe mit weniger als vier Positions-Args.

    Nutzt den AST, wenn ``text`` valides Python ist. Bei ``SyntaxError``
    (Fragment) faellt sie auf eine grobe Klammer-Zaehlung zurueck.
    Keyword-Argumente werden bewusst nicht mitgezaehlt.
    """
    samples: list[str] = []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return _fallback_audit_zaehlung(text)


    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Name) or func.id != "audit":
            continue
        if len(node.args) < 4:
            samples.append(f"audit(...) mit {len(node.args)} Args")
    return samples


# --- Scanner ---

def _scan_einzelnen_patch(patch: dict) -> list[AntiPattern]:
    treffer: list[AntiPattern] = []
    file = str(patch.get("file", ""))
    action = patch.get("action", "")
    old = patch.get("old_string", "") or ""
    new = patch.get("new_string", "") or ""

    # Regel: geloeschter Test (action=delete auf tests/test_*.py)
    if action == "delete" and _ist_test_datei(file):
        treffer.append(AntiPattern("deleted_test", file, file))
        return treffer

    # Regel: Text-Muster im new_string
    for zeile in new.splitlines():
        z = zeile.rstrip()
        if "type: ignore" in z:
            treffer.append(AntiPattern("type_ignore", file, z.strip()))
        if "# noqa" in z:
            treffer.append(AntiPattern("noqa", file, z.strip()))
        if "eslint-disable" in z:
            treffer.append(AntiPattern("eslint_disable", file, z.strip()))
        if "|| true" in z and _ist_shell_kontext(file):
            treffer.append(AntiPattern("shell_or_true", file, z.strip()))

    # Regel: audit(...) mit zu wenigen Positions-Argumenten
    for sample in _pruefe_audit_signatur(new):
        treffer.append(AntiPattern("audit_signature", file, sample))

    # Regel: geschwaechte Assertion (weniger asserts mit Vergleich)
    if action == "update" and _ist_test_datei(file):
        alt_mit = _zaehle_assert_mit_vergleich(old)
        neu_mit = _zaehle_assert_mit_vergleich(new)
        if neu_mit < alt_mit:
            treffer.append(AntiPattern(
                "weakened_assertion", file,
                f"{alt_mit} -> {neu_mit} asserts mit Vergleich",
            ))

    return treffer


def scan_patches(patches: list[dict]) -> list[AntiPattern]:
    """Scannt eine Liste von Patch-Dicts auf Antipattern.

    Erwartet dieselbe Struktur wie ``state.patches``:
    ``{"action": "update"|"delete"|"create", "file": str,
       "old_string": str, "new_string": str}``.

    Rueckgabe: Liste von ``AntiPattern``, leer wenn sauber.
    Deterministisch, idempotent, keine Seiteneffekte.
    """
    if not patches:
        return []
    alle: list[AntiPattern] = []
    for p in patches:
        if not isinstance(p, dict):
            continue
        alle.extend(_scan_einzelnen_patch(p))
    return alle
