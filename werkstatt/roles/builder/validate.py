"""_validate_imports_in_patch (OP-140 Phase 2b)."""
from __future__ import annotations

from pathlib import Path

from .ast import _finde_modul_pfad, _hat_symbol


def _validate_imports_in_patch(
    new_string: str, project_dir: Path,
    task_files: list[str] | None = None,
) -> list[str]:
    """M-444b: Findet unaufloesbare Imports (Modul UND Symbol).

    Prueft `import X`, `from X import Y` und `from X.Y import Z` gegen:
    - stdlib
    - Projekt-Module
    - venv-Pakete
    - Symbol-Existenz (via AST), wenn Modul im Projekt liegt und
      Symbol NICHT im selben Patch definiert wird.
    """
    import re as _re
    import sys as _sys

    fehlend: list[str] = []

    # Sammle Symbole, die im Patch selbst definiert werden (class X, def X).
    _im_patch_definiert: set[str] = set()
    for m in _re.finditer(r"^(?:class|def)\s+(\w+)", new_string, _re.MULTILINE):
        _im_patch_definiert.add(m.group(1))
    for m in _re.finditer(r"^async\s+def\s+(\w+)", new_string, _re.MULTILINE):
        _im_patch_definiert.add(m.group(1))
    for m in _re.finditer(r"^([A-Z][A-Z0-9_]*)\s*=", new_string, _re.MULTILINE):
        _im_patch_definiert.add(m.group(1))

    # Pattern 1: from X import Y, Z
    from_re = _re.compile(
        r"^\s*from\s+([\w.]+)\s+import\s+([^\n]+)", _re.MULTILINE,
    )
    from_imports: list[tuple[str, list[str]]] = []
    for m in from_re.finditer(new_string):
        modul = m.group(1)
        # Symbole: "Y, Z" oder "Y as Z, ..."
        roh = m.group(2).strip().rstrip("()")
        syms = []
        for teil in roh.split(","):
            teil = teil.strip()
            if not teil:
                continue
            # "X as Y" -> X
            if " as " in teil:
                teil = teil.split(" as ")[0].strip()
            if teil and teil != "*":
                syms.append(teil)
        from_imports.append((modul, syms))

    # Pattern 2: import X.Y
    imp_re = _re.compile(r"^\s*import\s+([\w.]+)", _re.MULTILINE)
    imp_mods: set[str] = set()
    for m in imp_re.finditer(new_string):
        imp_mods.add(m.group(1))

    # M-451: stdlib-Check auf Top-Level. sys.stdlib_module_names
    # enthaelt nur Top-Level (collections), nicht submodule
    # (collections.abc). Submodule sind aber Teil der stdlib.
    stdlib: set[str] = set(getattr(_sys, "stdlib_module_names", set()))
    venv_site_dirs: list[Path] = []
    venv_lib = project_dir / ".venv" / "lib"
    if venv_lib.is_dir():
        for site in venv_lib.iterdir():
            sp = site / "site-packages"
            if sp.is_dir():
                venv_site_dirs.append(sp)

    def _modul_existiert(modul: str) -> bool:
        # M-451: Top-Level-Check. collections.abc -> collections.
        top = modul.split(".")[0]
        if top in stdlib:
            return True
        if _finde_modul_pfad(top, project_dir):
            # Fuer submodule auch den vollen Pfad pruefen.
            if modul != top:
                sub_path = project_dir / modul.replace(".", "/")
                return bool(sub_path.with_suffix(".py").is_file() or (sub_path / "__init__.py").is_file())
            return True
        for sp in venv_site_dirs:
            if (sp / top).is_dir() or (sp / f"{top}.py").is_file():
                return True
        return False

    # Modulpruefung
    for mod in imp_mods:
        if not _modul_existiert(mod):
            fehlend.append(mod)
    for modul, _syms in from_imports:
        if not _modul_existiert(modul):
            fehlend.append(modul)

    # Symbolpruefung (nur fuer Projekt-Module; stdlib/venv ignorieren).
    for modul, syms in from_imports:
        if not _modul_existiert(modul):
            continue  # Modul-Fehler schon gemeldet
        if modul in stdlib:
            continue
        mod_pfad = _finde_modul_pfad(modul, project_dir)
        if mod_pfad is None:
            continue  # venv-Paket; Symbol nicht pruefbar
        # M-451: Symbole, die in anderen task_files definiert werden,
        # sind gueltig (Cross-File-Importe).
        _andere_defs: set[str] = set()
        if task_files:
            for _tf in task_files:
                _tf_path = project_dir / _tf
                if _tf_path.is_file() and _tf_path != mod_pfad:
                    for _sym in syms:
                        if _hat_symbol(_tf_path, _sym):
                            _andere_defs.add(_sym)
        for sym in syms:
            if sym in _im_patch_definiert:
                continue  # wird im selben Patch definiert
            if sym in _andere_defs:
                continue  # wird in anderer Datei definiert
            if not _hat_symbol(mod_pfad, sym):
                fehlend.append(f"{modul}.{sym}")

    return fehlend
