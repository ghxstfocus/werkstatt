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
    if base.endswith(".mk"):
        return True
    return False


def _ist_test_datei(file: str) -> bool:
    f = file.replace("\\", "/")
    base = f.rsplit("/", 1)[-1]
    if not base.endswith(".py"):
        return False
    if base.startswith("test_") or base.endswith("_test.py"):
        return True
    if "/tests/" in f or f.startswith("tests/"):
        return True
    return False


def _hat_vergleich(zeile: str) -> bool:
    s = zeile.strip()
    if not s.startswith("assert"):
        return False
    return any(op in s for op in _VERGLEICHS_OPS)


def _zaehle_assert_mit_vergleich(text: str) -> int:
    return sum(1 for z in text.splitlines() if _hat_vergleich(z))


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
