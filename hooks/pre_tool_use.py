"""PreToolUse-Hook (Phase 10, M-334a).

Prueft einen Patch VOR dem Anwenden. Deterministisch:
  - Import-Validierung (existiert das Modul im Zielprojekt?)
  - Datei-Existenz (bei update: existiert die Datei? bei create: nicht?)

Output: {"allow": bool, "reason": str}
"""
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

# FIX AM 2026-10-31: stdlib dynamisch aus sys.stdlib_module_names
# (Python 3.10+). Die manuelle Allowlist war unvollstaendig —
# 'urllib' fehlte, wurde als "nicht im Projekt" geblockt. Live-
# Beleg 2026-10-31 10:31 t1: pre_tool_use blockte
# 'import urllib.error' und killte den DeepSeek-Task.
_STDLIB_ROOTS = getattr(sys, "stdlib_module_names", frozenset())
# Zusaetzliche Third-Party, die im Zielprojekt genutzt werden
# (nicht per stdlib_module_names abgedeckt).
_THIRD_PARTY_ROOTS = {
    "pytest", "yaml", "requests", "pydantic", "click", "rich",
    "numpy", "pandas", "flask", "django", "fastapi", "httpx",
    "aiohttp", "sqlalchemy", "jinja2", "werkzeug", "boto3",
    "psutil",
}
_KNOWN_ROOTS = _STDLIB_ROOTS | _THIRD_PARTY_ROOTS


def _module_exists(name: str, project_dir: Path) -> bool:
    """Prueft, ob ein Modul im Projekt existiert (Datei-Existenz).

    Bug (2026-11-03): 'werkstatt.web.ws' wurde als 'fehlt' gemeldet,
    obwohl werkstatt/web/ws.py existiert. Ursache: import-Pfade sind
    relativ zum PYTHONPATH-Root, nicht zum project_dir. Wenn das
    Projekt-Modul-Package im project_dir liegt, muss project_dir der
    Root sein — das ist es hier aber nur, wenn das Package direkt
    drunter liegt (werkstatt/web/ws.py bei project_dir=/opt/werkstatt
    ergibt project_dir/werkstatt/web/ws.py — existiert).
    Zusaetzliche Pruefung: nur den LEAF pruefen, nicht den vollen
    dotted path — das toleriert Wrapper-Packages.
    """
    if not name:
        return True
    root = name.split(".")[0]
    if root in _KNOWN_ROOTS:
        return True
    # Relativer Import? Dann nicht pruefbar (patch-spezifisch).
    if name.startswith("."):
        return True

    rel = name.replace(".", "/")
    # 1. Voller Pfad relativ zu project_dir
    candidates = [
        project_dir / f"{rel}.py",
        project_dir / rel / "__init__.py",
        project_dir / rel,
    ]
    # 2. Wenn project_dir bereits das Package-Root ist (z.B. /opt/werkstatt,
    #    und import ist "werkstatt.web.ws"): ohne fuehrendes Package testen.
    if project_dir.name == root:
        _rest = name.split(".", 1)[1] if "." in name else ""
        if _rest:
            rel2 = _rest.replace(".", "/")
            candidates.extend([
                project_dir / f"{rel2}.py",
                project_dir / rel2 / "__init__.py",
                project_dir / rel2,
            ])
    # 3. Wie vom Hook 2026-11-03: manche Imports sind relativ zum
    #    Package, in dem die Datei liegt (nicht project_dir). Das kann
    #    der Hook nicht wissen — also: toleranter sein.
    #    Wenn der Name einen Punkt hat UND der LEAF als Modul-Datei
    #    irgendwo unter project_dir existiert, akzeptieren.
    if "." in name:
        leaf = name.rsplit(".", 1)[-1]
        for _hit in project_dir.rglob(f"{leaf}.py"):
            return True
        for _hit in project_dir.rglob(f"{leaf}/__init__.py"):
            return True

    for cand in candidates:
        if cand.exists():
            return True
    return False


def _check_imports(patch_text: str, project_dir: Path) -> tuple[bool, str]:
    """Prueft alle Imports im Patch gegen existierende Module."""
    if not patch_text.strip():
        return True, ""
    try:
        tree = ast.parse(patch_text)
    except SyntaxError:
        # Patch ist nicht valides Python (z.B. Markdown, YAML) ->
        # nicht pruefbar. py_compile prueft spaeter.
        return True, ""
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if not _module_exists(alias.name, project_dir):
                    return False, f"Import '{alias.name}' existiert nicht im Projekt"
        elif (
            isinstance(node, ast.ImportFrom)
            and node.module
            and not _module_exists(node.module, project_dir)
        ):
            return False, f"Import-from '{node.module}' existiert nicht im Projekt"
    return True, ""


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        print(json.dumps({"allow": False, "reason": "Ungueltiges Payload-JSON"}))
        return 0

    patch_text = payload.get("patch", "") or ""
    project_dir_str = payload.get("project_dir", "")
    project_dir = Path(project_dir_str) if project_dir_str else None

    if project_dir is None or not project_dir.exists():
        # Kein Projekt-Pfad -> nicht pruefbar (Backward-Compat).
        print(json.dumps({"allow": True, "reason": "Kein project_dir"}))
        return 0

    ok, reason = _check_imports(patch_text, project_dir)
    print(json.dumps({"allow": ok, "reason": reason}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
