"""Deterministische Diagnose fuer Reflection-Fehler (OP-081).

Erkennt bekannte Fehlerklassen deterministisch und liefert einen
Patch-Vorschlag. Kein LLM. Einhängung in
reflection._reflection_loop vor run_builder.

Unterstuetzte Klassen (Stand 2026-11-02):
- NameError: name 'X' is not defined -> fehlender Import
- RuntimeError: Directory '...' does not exist -> falscher Pfad
"""
from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any

__all__ = ["_deterministische_diagnose"]

_NAMEERROR_RE = re.compile(
    r"NameError:\s*name\s+'([A-Za-z_][A-Za-z0-9_]*)'\s+is not defined"
)
_DIRNOTFOUND_RE = re.compile(r"Directory\s+'([^']+)'\s+does not exist")
_PFAD_IN_TRACEBACK_RE = re.compile(r"([\w./\-]+\.py):\d+")

_IGNORE_PARTS = {
    ".venv", "venv", "__pycache__", "site-packages",
    "node_modules", ".git", ".tox", ".mypy_cache",
    ".pytest_cache", ".ruff_cache",
}


def _extrahiere_nameerror(fehler: str) -> str | None:
    m = _NAMEERROR_RE.search(fehler)
    return m.group(1) if m else None


def _extrahiere_dirnotfound(fehler: str) -> str | None:
    m = _DIRNOTFOUND_RE.search(fehler)
    return m.group(1) if m else None


def _kandidaten_dateien(state: Any) -> list[Path]:
    pd = Path(str(getattr(state, "project_dir", ".") or "."))
    dateien: list[Path] = []
    for p in (getattr(state, "patches", None) or []):
        if not isinstance(p, dict):
            continue
        f = p.get("file")
        if not f:
            continue
        full = Path(f) if Path(f).is_absolute() else (pd / f)
        if full.exists() and full not in dateien:
            dateien.append(full)
    for err in (getattr(state, "last_verify_errors", None) or []):
        for m in _PFAD_IN_TRACEBACK_RE.finditer(str(err)):
            cand = pd / m.group(1)
            if cand.exists() and cand not in dateien:
                dateien.append(cand)
    return dateien


def _benutzte_namen(datei: Path) -> set[str]:
    try:
        tree = ast.parse(datei.read_text(encoding="utf-8", errors="replace"))
    except (OSError, SyntaxError):
        return set()
    return {
        n.id for n in ast.walk(tree)
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)
    }


def _importierte_namen(datei: Path) -> set[str]:
    try:
        tree = ast.parse(datei.read_text(encoding="utf-8", errors="replace"))
    except (OSError, SyntaxError):
        return set()
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.ImportFrom):
            for a in node.names:
                names.add(a.asname or a.name)
        elif isinstance(node, ast.Import):
            for a in node.names:
                names.add((a.asname or a.name).split(".")[0])
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    names.add(t.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
    return names


def _finde_import_quelle(project_dir: Path, name: str) -> str | None:
    # 1. Modul namens `name`
    for f in project_dir.rglob(f"{name}.py"):
        if any(p in _IGNORE_PARTS for p in f.parts):
            continue
        try:
            rel = f.parent.relative_to(project_dir)
        except ValueError:
            continue
        parent_mod = ".".join(rel.parts) if rel.parts else ""
        if parent_mod:
            return f"from {parent_mod} import {name}"
    # 2. Top-Level-Name in einer Datei
    for f in project_dir.rglob("*.py"):
        if any(p in _IGNORE_PARTS for p in f.parts):
            continue
        try:
            tree = ast.parse(f.read_text(encoding="utf-8", errors="replace"))
        except (OSError, SyntaxError):
            continue
        for node in tree.body:
            hit = False
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                hit = node.name == name
            elif isinstance(node, ast.Assign):
                hit = any(
                    isinstance(t, ast.Name) and t.id == name
                    for t in node.targets
                )
            if hit:
                rel = f.relative_to(project_dir).with_suffix("")
                parts = list(rel.parts)
                if parts and parts[-1] == "__init__":
                    parts = parts[:-1]
                return f"from {'.'.join(parts)} import {name}"
    return None


def _letzte_import_zeile(datei: Path) -> str | None:
    try:
        lines = datei.read_text(encoding="utf-8").splitlines(keepends=True)
    except OSError:
        return None
    last_import = -1
    depth = 0
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if depth == 0 and (stripped.startswith("import ")
                           or stripped.startswith("from ")):
            last_import = i
            depth = line.count("(") - line.count(")")
        elif depth > 0:
            last_import = i
            depth += line.count("(") - line.count(")")
    if last_import < 0:
        return None
    ln = lines[last_import]
    return ln if ln.endswith("\n") else ln + "\n"


def _rel_str(datei: Path, pd: Path) -> str:
    try:
        return str(datei.relative_to(pd))
    except ValueError:
        return str(datei)


def _diagnose_import_fehlt(
    state: Any, datei: Path, fehler: str,
) -> dict | None:
    name = _extrahiere_nameerror(fehler)
    if not name:
        return None
    if name not in _benutzte_namen(datei):
        return None
    if name in _importierte_namen(datei):
        return None
    pd = Path(str(getattr(state, "project_dir", ".") or "."))
    import_zeile = _finde_import_quelle(pd, name)
    if not import_zeile:
        return None
    anchor = _letzte_import_zeile(datei)
    if not anchor:
        return None
    return {
        "file": _rel_str(datei, pd),
        "old_string": anchor,
        "new_string": anchor + import_zeile + "\n",
        "grund": f"NameError: '{name}' nicht importiert ({import_zeile})",
        "klasse": "import_fehlt",
    }


def _diagnose_pfad_not_found(
    state: Any, datei: Path, fehler: str,
) -> dict | None:
    fehlender = _extrahiere_dirnotfound(fehler)
    if not fehlender:
        return None
    fp = Path(fehlender)
    if fp.exists():
        return None
    pd = Path(str(getattr(state, "project_dir", ".") or "."))
    basename = fp.name
    kandidat = pd / basename
    if not kandidat.is_dir() or kandidat == fp:
        return None
    try:
        lines = datei.read_text(encoding="utf-8").splitlines(keepends=True)
    except OSError:
        return None
    for line in lines:
        if basename not in line or "__file__" not in line or "=" not in line:
            continue
        m = re.match(r"^(\s*)(\w+)\s*=\s*Path\(__file__\)(.+)$", line)
        if not m:
            continue
        indent, var, _ = m.groups()
        try:
            n_parents = len(datei.relative_to(pd).parts)
        except ValueError:
            return None
        new_line = (
            f"{indent}{var} = Path(__file__).resolve()"
            + ".parent" * n_parents
            + f' / "{basename}"\n'
        )
        old_line = line if line.endswith("\n") else line + "\n"
        return {
            "file": _rel_str(datei, pd),
            "old_string": old_line,
            "new_string": new_line,
            "grund": f"Directory '{fehlender}' fehlt, richtig: {kandidat}",
            "klasse": "pfad_falsch",
        }
    return None


def _scan_alle_dateien_fuer_name(state: Any, name: str) -> Path | None:
    pd = Path(str(getattr(state, "project_dir", ".") or "."))
    for f in pd.rglob("*.py"):
        if any(p in _IGNORE_PARTS for p in f.parts):
            continue
        if name in _importierte_namen(f):
            continue
        if name in _benutzte_namen(f):
            return f
    return None


def _deterministische_diagnose(state: Any) -> dict | None:
    """Erster Match aus bekannten Fehlerklassen (deterministisch)."""
    errors = getattr(state, "last_verify_errors", None) or []
    dateien = _kandidaten_dateien(state)
    diagnosen = (_diagnose_import_fehlt, _diagnose_pfad_not_found)
    for fehler in errors:
        s = str(fehler)
        for datei in dateien:
            for fn in diagnosen:
                try:
                    res = fn(state, datei, s)
                except Exception:  # noqa: BLE001
                    res = None
                if res is not None:
                    return res
    # Fallback: NameError-Scan ueber alle Projekt-.py
    for fehler in errors:
        s = str(fehler)
        name = _extrahiere_nameerror(s)
        if not name:
            continue
        fallback = _scan_alle_dateien_fuer_name(state, name)
        if fallback is not None:
            try:
                res = _diagnose_import_fehlt(state, fallback, s)
            except Exception:  # noqa: BLE001
                res = None
            if res is not None:
                return res
    return None
