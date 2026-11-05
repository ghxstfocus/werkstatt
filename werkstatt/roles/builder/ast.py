"""_PY_IGNORE_PARTS _ast_block_fuer_zieldatei _finde_modul_pfad (OP-140 Phase 2b)."""
from __future__ import annotations

from pathlib import Path

_PY_IGNORE_PARTS = frozenset({
    ".venv", "venv", "__pycache__", "site-packages",
    "node_modules", ".git", ".tox", ".mypy_cache",
    ".pytest_cache", ".ruff_cache", ".eggs", "build", "dist",
})


def _ast_block_fuer_zieldatei(state, zieldatei: str) -> str:
    """Formatiert die AST-Info einer Zieldatei fuer den Builder-Prompt."""
    if state is None:
        return ""
    idx = getattr(state, "api_index_cache", None) or {}
    if not idx:
        return ""
    # relativen Pfad finden (Zieldatei kann absolut oder relativ sein)
    from pathlib import Path as _P
    pd = getattr(state, "project_dir", "") or ""
    rel = zieldatei
    try:
        if _P(zieldatei).is_absolute() and pd:
            rel = str(_P(zieldatei).relative_to(pd))
    except (ValueError, OSError):
        pass
    info = idx.get(rel)
    if not info:
        return ""
    lines = [f"## ZIELDATEI-STRUKTUR (AST): {rel}"]
    _alls = info.get("all") or []
    if _alls:
        lines.append(f"__all__: {', '.join(_alls)}")
    for _fn in info.get("functions", [])[:30]:
        _args = ", ".join(_fn.get("args", []))
        _ret = _fn.get("return") or ""
        lines.append(f"  def {_fn.get('name','?')}({_args}){(' -> ' + _ret) if _ret else ''}")
    for _cls in info.get("classes", [])[:15]:
        lines.append(f"  class {_cls.get('name','?')}")
        for _m in _cls.get("methods", [])[:15]:
            _margs = ", ".join(_m.get("args", []))
            lines.append(f"    def {_m.get('name','?')}({_margs})")
    if len(lines) <= 1:
        return ""
    return "\n".join(lines)


def _sammle_projekt_py_files(project_dir: Path, limit: int = 30) -> list[Path]:
    """K10: Sammelt max `limit` .py-Dateien im Projekt, ohne Ignorier-Pfade.

    Filtert .venv, site-packages, __pycache__, node_modules etc.
    Sonst landen bei einem Projekt mit .venv die ersten N Treffer
    ausschliesslich in den venv-Paketen.
    """
    out: list[Path] = []
    for f in sorted(Path(project_dir).rglob("*.py")):
        try:
            rel_parts = set(f.relative_to(project_dir).parts)
        except ValueError:
            continue
        if rel_parts & _PY_IGNORE_PARTS:
            continue
        out.append(f)
        if len(out) >= limit:
            break
    return out


def _finde_modul_pfad(modul: str, project_dir: Path) -> Path | None:
    """M-444b: Findet den Pfad zu einem Modul (Datei oder Package).

    Versteht dotted paths: 'core.models' -> core/models.py
    oder core/models/__init__.py.
    """
    teile = modul.split(".")
    base = project_dir
    for teil in teile[:-1]:
        base = base / teil
        if not base.is_dir():
            return None
    letzter = teile[-1]
    datei = base / f"{letzter}.py"
    if datei.is_file():
        return datei
    pkg = base / letzter / "__init__.py"
    if pkg.is_file():
        return pkg
    return None


def _hat_symbol(modul_pfad: Path, symbol: str) -> bool:
    """M-444b: Prueft, ob ein Modul ein Symbol (class/def/var) definiert."""
    import ast as _ast
    try:
        tree = _ast.parse(modul_pfad.read_text(encoding="utf-8", errors="replace"))
    except (SyntaxError, OSError):
        return False
    for node in tree.body:
        if isinstance(node, _ast.ClassDef) and node.name == symbol:
            return True
        if isinstance(node, _ast.FunctionDef) and node.name == symbol:
            return True
        if isinstance(node, _ast.AsyncFunctionDef) and node.name == symbol:
            return True
        if isinstance(node, _ast.Assign):
            for t in node.targets:
                if isinstance(t, _ast.Name) and t.id == symbol:
                    return True
        if isinstance(node, _ast.AnnAssign):
            if isinstance(node.target, _ast.Name) and node.target.id == symbol:
                return True
    return False
