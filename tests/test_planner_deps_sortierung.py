"""OP-175 Bug A: Topo-Sort der Tasks nach dependencies.

Spec: der Planner darf Tasks nicht in einer Reihenfolge in den
Loop geben, in der eine Task auf eine spaetere Task wartet. Live-
Beleg Loop-Test-6 (18:27): t1 deps=[t2], aber t1 steht vor t2.
Der Loop blockt dann t1 stumm, t3/t4 ebenfalls -> 0/4 Tasks done.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, "/opt/werkstatt")

from werkstatt.planner import (
    _leite_deps_deterministisch,
    _topo_sort_tasks,
)

# ============ Basis-Faelle ============

def test_leere_liste_bleibt_leer() -> None:
    assert _topo_sort_tasks([]) == []


def test_ohne_deps_reihenfolge_bleibt() -> None:
    """Stabilitaet: keine deps -> Originalreihenfolge."""
    tasks = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
    out = _topo_sort_tasks(tasks)
    assert [t["id"] for t in out] == ["a", "b", "c"]


def test_rueckwaerts_dep_wird_sortiert() -> None:
    """Spec: Loop-Test-6-Muster — t1 haengt von t2 ab, steht aber
    vor t2. Nach Topo-Sort steht t2 vor t1."""
    tasks = [
        {"id": "t1", "dependencies": ["t2"]},
        {"id": "t2", "dependencies": []},
        {"id": "t3", "dependencies": ["t1", "t2"]},
    ]
    out = _topo_sort_tasks(tasks)
    assert [t["id"] for t in out] == ["t2", "t1", "t3"]


def test_diamond_reihenfolge() -> None:
    """t1 -> {t2, t3} -> t4. Stabile Auswahl: t2 vor t3 (Original)."""
    tasks = [
        {"id": "t4", "dependencies": ["t2", "t3"]},
        {"id": "t2", "dependencies": ["t1"]},
        {"id": "t3", "dependencies": ["t1"]},
        {"id": "t1", "dependencies": []},
    ]
    out = _topo_sort_tasks(tasks)
    ids = [t["id"] for t in out]
    assert ids[0] == "t1"
    assert ids[-1] == "t4"
    assert ids.index("t2") < ids.index("t3")


# ============ Fehler-Faelle ============

def test_zyklus_wird_vor_planfreigabe_abgelehnt_und_auditiert() -> None:
    tasks = [
        {"id": "t1", "dependencies": ["t2"]},
        {"id": "t2", "dependencies": ["t1"]},
    ]
    with (
        patch("werkstatt.planner.audit") as mock_audit,
        pytest.raises(ValueError, match="Abhaengigkeitszyklus"),
    ):
        _topo_sort_tasks(tasks, pd=Path("/tmp/x"), pn="test")
    kinds = [call.args[0] for call in mock_audit.call_args_list]
    assert "planner_deps_zyklus" in kinds


def test_unbekannte_abhaengigkeit_wird_abgelehnt() -> None:
    tasks = [
        {"id": "t1", "dependencies": ["gibt_es_nicht"]},
        {"id": "t2", "dependencies": []},
    ]
    with pytest.raises(ValueError, match="unbekannte Abhaengigkeit"):
        _topo_sort_tasks(tasks)


def test_selbstabhaengigkeit_wird_abgelehnt() -> None:
    with pytest.raises(ValueError, match="sich selbst"):
        _topo_sort_tasks([{"id": "t1", "dependencies": ["t1"]}])


def test_doppelte_task_id_wird_abgelehnt() -> None:
    with pytest.raises(ValueError, match="doppelt"):
        _topo_sort_tasks([{"id": "t1"}, {"id": "t1"}])


def test_malformed_dependencies_are_rejected() -> None:
    with pytest.raises(ValueError, match="muessen eine Liste"):
        _topo_sort_tasks([{"id": "t1", "dependencies": "t2"}])


# ============ Integration: Ableitung + Sort ============

def test_loop_test_6_ableitung_und_sort() -> None:
    """Spec: Prosa aus Loop-Test-6 (18:27) -> _leite_deps_deterministisch
    erzeugt t1.deps=[t2] (korrekt). Erst _topo_sort_tasks behebt
    die Reihenfolge. Ohne Sort blockt der Loop t1 stumm."""
    prosa = (
        "## 5. Welche Dateien haengen voneinander ab?\n"
        "- werkstatt/reflection.py: werkstatt/phases/review.py\n"
        "- werkstatt/phases/review.py: (keine)\n"
        "- tests/test_phase_review_gate.py: "
        "werkstatt/reflection.py, werkstatt/phases/review.py\n"
        "\n"
        "DEINE ROLLE IM LOOP\n"
    )
    tasks = [
        {"id": "t1", "task_files": ["werkstatt/reflection.py"]},
        {"id": "t2", "task_files": ["werkstatt/phases/review.py"]},
        {"id": "t3", "task_files": ["tests/test_phase_review_gate.py"]},
    ]
    # 1. Ableitung: t1 haengt korrekt an t2 (Richtung stimmt).
    out = _leite_deps_deterministisch(tasks, prosa)
    by_id = {t["id"]: t for t in out}
    assert "t2" in (by_id["t1"].get("dependencies") or [])
    # 2. Ohne Sort steht t1 vor t2 -> der Bug.
    assert [t["id"] for t in out].index("t1") < \
           [t["id"] for t in out].index("t2")
    # 3. Nach Sort steht t2 vor t1, t3 danach.
    out = _topo_sort_tasks(out)
    ids = [t["id"] for t in out]
    assert ids.index("t2") < ids.index("t1") < ids.index("t3")
