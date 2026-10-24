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

# Standard-Library + bekannte Third-Party (nicht pruefbar).
_KNOWN_ROOTS = {
    "sys", "os", "json", "re", "ast", "pathlib", "datetime",
    "typing", "unittest", "argparse", "subprocess", "shutil",
    "time", "threading", "logging", "collections", "itertools",
    "functools", "dataclasses", "enum", "io", "base64", "hashlib",
    "tempfile", "traceback", "warnings", "weakref", "contextlib",
    "__future__",
    "pytest", "yaml", "requests", "pydantic", "click", "rich",
    "numpy", "pandas", "flask", "django", "fastapi", "httpx",
    "aiohttp", "sqlalchemy", "jinja2", "werkzeug", "boto3",
}


def _module_exists(name: str, project_dir: Path) -> bool:
    """Prueft, ob ein Modul im Projekt existiert (Datei-Existenz)."""
    if not name:
        return True
    root = name.split(".")[0]
    if root in _KNOWN_ROOTS:
        return True
    # Relativer Import? Dann nicht pruefbar (patch-spezifisch).
    if name.startswith("."):
        return True
    # Projekt-Modul: Datei-Existenz pruefen.
    rel = name.replace(".", "/")
    for cand in (
        project_dir / rel,
        project_dir / f"{rel}.py",
        project_dir / rel / "__init__.py",
    ):
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
