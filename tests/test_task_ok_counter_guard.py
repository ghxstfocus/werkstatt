"""OP-167: Jeder `_task_ende(ok=True)` MUSS tasks_ok hochzaehlen.

Loop-Test-8 (2026-11-05): t3/t4 wurden ueber den Reflection-OK-Pfad
als `_task_ende(ok=True)` markiert, aber der Counter blieb auf 0.
Footer zeigte "0/8 · 8 failed", obwohl PhaseState 2 done, 1 failed,
1 human_review, 4 blocked zeigte.

Dieser Guard-Test prueft per AST, dass in den 10 Zeilen vor jedem
`_task_ende(ok=True)` ein `tasks_ok += 1` steht. Wenn ein neuer
Erfolgs-Pfad hinzukommt, ohne den Counter zu inkrementieren,
schlaegt der Test fehl.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

sys.path.insert(0, "/opt/werkstatt")

_PP_DIR = Path("/opt/werkstatt/werkstatt/phases")


def test_jeder_task_ende_ok_hat_counter_inkrement():
    src = "\n".join(
        p.read_text(encoding="utf-8")
        for p in sorted(_PP_DIR.glob("*.py"))
        if p.name != "__init__.py"
    )
    tree = ast.parse(src)
    lines = src.splitlines()

    verstoesse: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (isinstance(func, ast.Name) and func.id == "_task_ende"):
            continue
        ok_true = any(
            isinstance(kw.value, ast.Constant) and kw.value.value is True
            for kw in node.keywords
            if kw.arg == "ok"
        )
        if not ok_true:
            continue
        start = max(0, node.lineno - 10)
        context = "\n".join(lines[start:node.lineno])
        # Akzeptiere: `tasks_ok += 1` (Inkrement) ODER
        # `tasks_ok_counter` (Sonderfall skip_plan_gate mit
        # `tasks_ok = 1` + explizitem Counter-Setzen).
        if ("tasks_ok += 1" not in context
                and "tasks_ok_counter" not in context):
            verstoesse.append(node.lineno)

    assert not verstoesse, (
        f"_task_ende(ok=True) ohne tasks_ok += 1 in "
        f"{_PP_DIR.name}/: Zeilen {verstoesse}. "
        f"Footer zeigt falsche Zahlen."
    )
