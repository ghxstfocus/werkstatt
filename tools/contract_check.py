from __future__ import annotations

import ast
import sys
from pathlib import Path

from werkstatt.state import RunState


def _state_felder() -> set[str]:
    return set(RunState.__dataclass_fields__.keys())


def _pruefe_setattr_aufrufe(pfad: Path, state_felder: set[str]) -> list[str]:
    try:
        tree = ast.parse(pfad.read_text(encoding="utf-8"))
    except SyntaxError:
        return []

    fehler: list[str] = []
    for call in ast.walk(tree):
        if not isinstance(call, ast.Call):
            continue
        func = call.func
        ist_setattr = False
        if isinstance(func, ast.Name) and func.id == "setattr" or isinstance(func, ast.Attribute) and func.attr == "setattr":
            ist_setattr = True
        if not ist_setattr:
            continue
        if len(call.args) < 2:
            continue
        arg = call.args[1]
        if not isinstance(arg, ast.Constant):
            continue
        value = arg.value
        if not isinstance(value, str):
            continue
        if value not in state_felder:
            fehler.append(
                f"{pfad}:{call.lineno}: setattr auf unbekanntes RunState-Feld '{value}'"
            )
    return sorted(fehler)


def _werkstatt_dateien() -> list[Path]:
    basis = Path(__file__).resolve().parent.parent / "werkstatt"
    if not basis.is_dir():
        return []
    return sorted(basis.glob("*.py"))


def main() -> int:
    fehler: list[str] = []
    dateien = _werkstatt_dateien()
    state_felder = _state_felder()
    for pfad in dateien:
        fehler.extend(_pruefe_setattr_aufrufe(pfad, state_felder))
    for eintrag in fehler:
        print(eintrag)
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main())
