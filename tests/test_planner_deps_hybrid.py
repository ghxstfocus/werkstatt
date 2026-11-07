"""OP-187: Planner-Dependency-Hybrid — Architect + Heuristik.

Bisher: _leite_deps_deterministisch hatte einen Exklusiv-Pfad
(architect ODER heuristik). Wenn der Architect Block 5 explizit
lieferte, wurde die Heuristik komplett uebersprungen — auch fuer
Tasks, die im Architect-Block gar nicht vorkamen. Umgekehrt: wenn
der Architect den Block ausliess (`found=True, arch_deps={}`),
gab es einen frühen `return tasks` ohne jede Dep-Ableitung.

Neu: Architect-Aussage hat Vorrang fuer die Tasks, die sie abdeckt;
Heuristik ergaenzt Tasks OHNE Architect-Aussage. Explizite
`- (keine)`-Aussage im Architect-Block 5 stoppt die Heuristik
komplett.
"""
from __future__ import annotations

from werkstatt import planner

# ============ Unit: _check_explicit_keine_in_prosa ============

def test_explicit_keine_true_bei_keine_zeile() -> None:
    prosa = """## 5. Welche Dateien haengen voneinander ab?

- (keine)
"""
    assert planner._check_explicit_keine_in_prosa(prosa) is True


def test_explicit_keine_false_bei_konkreter_datei() -> None:
    prosa = """## 5. Welche Dateien haengen voneinander ab?

- a.py: (keine)
- b.py: a.py
"""
    assert planner._check_explicit_keine_in_prosa(prosa) is False


def test_explicit_keine_false_ohne_block() -> None:
    assert planner._check_explicit_keine_in_prosa("kein block") is False


def test_explicit_keine_false_bei_leerem_block() -> None:
    """Block 5 da, aber kein Inhalt -> keine explizite Aussage."""
    prosa = """## 5. Welche Dateien haengen voneinander ab?

"""
    assert planner._check_explicit_keine_in_prosa(prosa) is False


# ============ Unit: _leite_deps_deterministisch (Hybrid) ============

_PROSA_MIT_ARCH = """## 5. Welche Dateien haengen voneinander ab?

- werkstatt/state.py: (keine)
- werkstatt/gates.py: werkstatt/state.py
- tests/test_gates.py: werkstatt/gates.py
"""


def test_arch_liefert_alle_deps() -> None:
    """Architect deckt alle Tasks ab -> Deps aus Architect, Heuristik
    ueberschreibt sie nicht."""
    tasks = [
        {"id": "t1", "task_files": ["werkstatt/state.py"]},
        {"id": "t2", "task_files": ["werkstatt/gates.py"]},
        {"id": "t3", "task_files": ["tests/test_gates.py"]},
    ]
    result = planner._leite_deps_deterministisch(tasks, _PROSA_MIT_ARCH)
    assert result[0]["dependencies"] == []
    assert result[1]["dependencies"] == ["t1"]
    assert result[2]["dependencies"] == ["t2"]


def test_arch_teilweise_heuristik_ergaenzt() -> None:
    """Architect deckt nur t1+t2 ab -> t3 bekommt Heuristik (test-Task
    wartet auf alle code-Tasks)."""
    prosa = """## 5. Welche Dateien haengen voneinander ab?

- werkstatt/state.py: (keine)
- werkstatt/gates.py: werkstatt/state.py
"""
    tasks = [
        {"id": "t1", "task_files": ["werkstatt/state.py"]},
        {"id": "t2", "task_files": ["werkstatt/gates.py"]},
        {"id": "t3", "task_files": ["tests/test_gates.py"]},
    ]
    result = planner._leite_deps_deterministisch(tasks, prosa)
    # t3 (test) bekommt Heuristik-Deps auf alle code-Tasks
    assert set(result[2]["dependencies"]) == {"t1", "t2"}


def test_arch_block_leer_heuristik_laeuft() -> None:
    """Architect-Block da, aber ohne Inhalt -> Heuristik laeuft."""
    prosa = """## 5. Welche Dateien haengen voneinander ab?

"""
    tasks = [
        {"id": "t1", "task_files": ["werkstatt/a.py"]},
        {"id": "t2", "task_files": ["tests/test_a.py"]},
    ]
    result = planner._leite_deps_deterministisch(tasks, prosa)
    assert result[1]["dependencies"] == ["t1"]


def test_arch_explicit_keine_keine_heuristik() -> None:
    """Architect sagt explizit 'keine' -> keine Heuristik."""
    prosa = """## 5. Welche Dateien haengen voneinander ab?

- (keine)
"""
    tasks = [
        {"id": "t1", "task_files": ["werkstatt/a.py"]},
        {"id": "t2", "task_files": ["tests/test_a.py"]},
    ]
    result = planner._leite_deps_deterministisch(tasks, prosa)
    # Keine Deps, weil Architect bewusst 'keine' gesagt hat.
    # (Feld darf fehlen — Reader nutzt ueberall .get("dependencies") or [].)
    assert (result[1].get("dependencies") or []) == []


def test_multi_file_task_deps_werden_gemappt() -> None:
    """OP-187: task_files[1] muss auch als Dep-Ziel erkannt werden."""
    prosa = """## 5. Welche Dateien haengen voneinander ab?

- b.py: (keine)
"""
    tasks = [
        {"id": "t1", "task_files": ["a.py", "b.py"]},
    ]
    # _datei_to_id soll beide Files auf t1 mappen.
    # (Der Test prueft implizit, dass kein KeyError bei dep-Mapping
    # entsteht und dass der Multi-File-Pfad keinen Crash provoziert.)
    result = planner._leite_deps_deterministisch(tasks, prosa)
    assert isinstance(result, list)
    assert len(result) == 1
