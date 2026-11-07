"""OP-181: Reviewer-Dead-Code-Erkennung bei neuen Modulen.

Loop-Test 8 (2026-11-07 11:50-11:58): der Loop baute
`tools/contract_check.py` + Tests, aber der Architect plante
keinen Aufrufer — der Pre-Check wurde nie ausgefuehrt. Loop-Test 9
(12:14-12:16) hat denselben Fehler wiederholt: t1-Funktion
`_pruefe_neue_module_genutzt` war gebaut, aber nicht verdrahtet.

Diese Tests sichern drei Dinge:
1. Der Pre-Check erkennt neue Module, die nur von Tests referenziert
   werden (HIGH-Bug).
2. Er triggert NICHT bei bestehenden Modulen (kein False-Positive).
3. Er triggert NICHT, wenn das Modul aus dem Produktivpfad
   referenziert wird.
4. AST-Wiring-Test: `run_reviewer` muss den Pre-Check aufrufen —
   sonst ist er toter Code (genau das ist Loop-Test 9 passiert).
"""
from __future__ import annotations

import ast
from pathlib import Path

from werkstatt import reviewer

_DIFF_NEUES_MODUL = (
    "diff --git a/mymod.py b/mymod.py\n"
    "new file mode 100644\n"
    "--- /dev/null\n"
    "+++ b/mymod.py\n"
    "@@ -0,0 +1,2 @@\n"
    "+def f():\n"
    "+    return 1\n"
)


def test_neues_modul_nur_test_import(tmp_path: Path) -> None:
    """AK (c)(a): neues Modul + nur Test-Import -> HIGH-Bug."""
    (tmp_path / "mymod.py").write_text("def f():\n    return 1\n",
                                       encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_mymod.py").write_text(
        "from mymod import f\n", encoding="utf-8")

    bugs = reviewer._pruefe_neue_module_genutzt(
        tmp_path, _DIFF_NEUES_MODUL)

    assert len(bugs) == 1, f"erwartet 1 Bug, bekommen: {bugs}"
    assert bugs[0]["severity"] == "high"
    assert "Dead-Code-Verdacht" in bugs[0]["description"]
    assert bugs[0]["file"] == "mymod.py"
    assert bugs[0].get("quelle") == "deterministic_dead_code"


def test_neues_modul_mit_werkstatt_import(tmp_path: Path) -> None:
    """AK (c)(b): neues Modul + werkstatt-Import -> kein Bug."""
    (tmp_path / "mymod.py").write_text("def f():\n    return 1\n",
                                       encoding="utf-8")
    (tmp_path / "werkstatt").mkdir()
    (tmp_path / "werkstatt" / "user.py").write_text(
        "import mymod\n", encoding="utf-8")

    bugs = reviewer._pruefe_neue_module_genutzt(
        tmp_path, _DIFF_NEUES_MODUL)

    assert bugs == [], f"erwartet [], bekommen: {bugs}"


def test_bestehendes_modul_geaendert(tmp_path: Path) -> None:
    """AK (c)(c): bestehendes Modul geaendert -> skip.

    Kein `new file mode`, keine `--- /dev/null`-Zeile -> der
    Pre-Check darf gar nicht erst nach dem Stem suchen."""
    (tmp_path / "existing.py").write_text("def f():\n    return 2\n",
                                          encoding="utf-8")
    diff = (
        "diff --git a/existing.py b/existing.py\n"
        "--- a/existing.py\n"
        "+++ b/existing.py\n"
        "@@ -1,2 +1,2 @@\n"
        "-def f():\n"
        "-    return 1\n"
        "+def f():\n"
        "+    return 2\n"
    )

    bugs = reviewer._pruefe_neue_module_genutzt(tmp_path, diff)

    assert bugs == [], f"erwartet [], bekommen: {bugs}"


# ============ AST-Wiring-Test (OP-181-Loop-Test-9-Lehre) ============

def test_run_reviewer_ruft_pre_check_auf() -> None:
    """OP-181 (a)-Wiring: run_reviewer muss den Pre-Check aufrufen.

    Loop-Test 9: `_pruefe_neue_module_genutzt` war gebaut (t1), aber
    `run_reviewer` rief sie nicht. Ohne diesen Test kann die
    Verdrahtung bei einem Refactor wieder verloren gehen — genau das
    ist der tote-Code-Bug, den OP-181 verhindern soll.

    Analog zu test_rollen_registry_migration.py (AST-Scan).
    """
    _src_pfad = Path(__file__).resolve().parent.parent / "werkstatt" / "reviewer.py"
    assert _src_pfad.is_file(), f"reviewer.py nicht gefunden: {_src_pfad}"
    _tree = ast.parse(_src_pfad.read_text(encoding="utf-8"))

    _call_gefunden = False
    for _node in ast.walk(_tree):
        if (isinstance(_node, ast.FunctionDef)
                and _node.name == "run_reviewer"):
            for _child in ast.walk(_node):
                if isinstance(_child, ast.Call):
                    _fn = _child.func
                    if (isinstance(_fn, ast.Name)
                            and _fn.id == "_pruefe_neue_module_genutzt"):
                        _call_gefunden = True
                        break
            break

    assert _call_gefunden, (
        "OP-181 (a): run_reviewer muss _pruefe_neue_module_genutzt "
        "aufrufen — sonst ist der Dead-Code-Pre-Check toter Code. "
        "Loop-Test 9 (2026-11-07 12:14-12:16) hat genau diesen "
        "Zustand gezeigt: Funktion vorhanden, Aufrufer fehlt."
    )
