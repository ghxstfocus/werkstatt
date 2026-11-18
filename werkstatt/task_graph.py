"""Deterministic task-graph compilation and validation.

This module validates the structured Planner-Split result before the plan
can reach the human approval gate or task executor.
"""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path, PureWindowsPath

from werkstatt.audit import audit


class TaskGraphError(ValueError):
    """A generated task graph is structurally unsafe to execute."""


def remap_dependencies_to_split_leaves(tasks: list[dict]) -> list[dict]:
    """Remap edges from removed recursive-split parents to surviving leaves."""
    surviving = {
        str(task.get("id")) for task in tasks
        if isinstance(task, dict) and task.get("id")
    }
    for task in tasks:
        if not isinstance(task, dict):
            continue
        remapped: list[str] = []
        for dependency in task.get("dependencies") or []:
            dep = str(dependency)
            descendants = {
                item for item in surviving if item.startswith(dep + "_")
            } if dep not in surviving else set()
            referenced = {
                str(parent_dep)
                for candidate in tasks
                if isinstance(candidate, dict)
                and str(candidate.get("id")) in descendants
                for parent_dep in candidate.get("dependencies") or []
            }
            leaves = sorted(descendants - referenced)
            remapped.extend(leaves or [dep])
        task["dependencies"] = remapped
    return tasks

def _validate_read_task_scopes(tasks: list[dict], project_dir) -> None:
    """Require every planned read task to name current, project-local files."""
    root = Path(project_dir).resolve(strict=True)
    for task in tasks:
        if task.get("action") != "read":
            continue
        task_id = str(task.get("id") or "?")
        files = task.get("task_files")
        if not isinstance(files, list) or not files:
            raise TaskGraphError(
                f"Read-Task {task_id} hat keinen konkreten task_files-Scope."
            )
        if len(files) > 50:
            raise TaskGraphError(f"Read-Task {task_id} hat mehr als 50 Quelldateien.")
        seen: set[str] = set()
        for raw_path in files:
            if not isinstance(raw_path, str) or not raw_path.strip() or len(raw_path) > 500:
                raise TaskGraphError(f"Read-Task {task_id} hat einen ungueltigen Dateipfad.")
            relative = Path(raw_path)
            if (
                relative.is_absolute()
                or PureWindowsPath(raw_path).is_absolute()
                or ".." in relative.parts
                or "\\" in raw_path
            ):
                raise TaskGraphError(
                    f"Read-Task {task_id} verweist ausserhalb des Projekt-Scopes: {raw_path}"
                )
            try:
                target = (root / relative).resolve(strict=True)
                target.relative_to(root)
            except (OSError, RuntimeError, ValueError) as exc:
                raise TaskGraphError(
                    f"Read-Task {task_id} hat keine gueltige Projektdatei: {raw_path}"
                ) from exc
            if not target.is_file():
                raise TaskGraphError(
                    f"Read-Task {task_id} Quelle ist keine Datei: {raw_path}"
                )
            normalized = target.relative_to(root).as_posix()
            if normalized in seen:
                raise TaskGraphError(
                    f"Read-Task {task_id} nennt eine Quelldatei doppelt: {raw_path}"
                )
            seen.add(normalized)

def _validate_criteria_coverage(
    tasks: list[dict], criteria: list[str], *, infer_single_task: bool = True,
) -> None:
    """Fail closed unless every plan criterion is assigned to a task."""
    if not criteria or any(not isinstance(item, str) or not item.strip()
                           for item in criteria):
        raise TaskGraphError("Plan enthaelt keine gueltigen Akzeptanzkriterien.")
    if not tasks:
        raise TaskGraphError("Plan enthaelt keine Tasks fuer die Akzeptanzkriterien.")

    expected = {f"AC{index}" for index in range(1, len(criteria) + 1)}
    if infer_single_task and len(tasks) == 1:
        task = tasks[0]
        if isinstance(task, dict) and not task.get("criterion_refs"):
            task["criterion_refs"] = sorted(
                expected, key=lambda item: int(item[2:]),
            )

    covered: set[str] = set()
    for index, task in enumerate(tasks, 1):
        if not isinstance(task, dict):
            raise TaskGraphError(f"Task {index} ist kein Objekt.")
        refs = task.get("criterion_refs")
        if not isinstance(refs, list) or not refs:
            raise TaskGraphError(
                f"Task {task.get('id', index)!r} hat keine criterion_refs.",
            )
        if any(not isinstance(ref, str) or not ref.strip() for ref in refs):
            raise TaskGraphError(
                f"Task {task.get('id', index)!r} enthaelt ungueltige criterion_refs.",
            )
        if len(set(refs)) != len(refs):
            raise TaskGraphError(
                f"Task {task.get('id', index)!r} wiederholt criterion_refs.",
            )
        unknown = sorted(set(refs) - expected)
        if unknown:
            raise TaskGraphError(
                f"Task {task.get('id', index)!r} referenziert unbekannte "
                f"Akzeptanzkriterien: {', '.join(unknown)}.",
            )
        covered.update(refs)

    missing = sorted(expected - covered, key=lambda item: int(item[2:]))
    if missing:
        raise TaskGraphError(
            "Nicht alle Akzeptanzkriterien sind Tasks zugeordnet: "
            + ", ".join(missing),
        )

def _parse_architect_deps_block(prosa: str) -> tuple[bool, dict[str, list[str]]]:
    """OP-163b: Architect-Block 5 parsen.

    Liefert (found, datei_zu_dep_dateien). `found=True` auch wenn
    Block leer (dann explizit 'keine Abhaengigkeiten').
    """
    import re as _re
    m = _re.search(
        r"(?:^|\n)(?:##\s*)?5\.\s*Welche Dateien h(?:ä|ae)ngen[^\n]*\n(.*?)(?=\n##\s|\nDEINE ROLLE|\Z)",
        prosa or "", _re.DOTALL,
    )
    if not m:
        return False, {}
    block = m.group(1)
    out: dict[str, list[str]] = {}
    for line in block.splitlines():
        lm = _re.match(r"^\s*-\s*(\S+\.\w+):\s*(.+)$", line)
        if not lm:
            continue
        datei = lm.group(1).strip("`")
        deps_raw = lm.group(2).strip()
        if deps_raw.lower() in ("(keine)", "keine", "-"):
            out[datei] = []
            continue
        deps = [
            _re.sub(r"`", "", d).strip()
            for d in deps_raw.split(",")
        ]
        out[datei] = [d for d in deps if d]
    return True, out

def _check_explicit_keine_in_prosa(prosa: str) -> bool:
    """OP-187: prueft, ob Architect-Block 5 explizit 'keine' sagt.

    Wenn der Architect im Block-5-Bereich `- (keine)` schreibt,
    ist das eine bewusste Aussage: keine Abhaengigkeiten zwischen
    Dateien. Die Heuristik darf dann NICHT laufen (sonst wuerde
    sie der Architect-Aussage widersprechen).

    Abgrenzung zu `_parse_architect_deps_block`:
    - `found=False` = Block 5 fehlt komplett (LLM hat ausgelassen).
    - `found=True, arch_deps={}, _explicit_keine=True` = Block 5
      da, explizit 'keine'.
    - `found=True, arch_deps={}, _explicit_keine=False` = Block 5
      da, aber Inhalt leer/Muell.
    """
    import re as _re
    m = _re.search(
        r"(?:^|\n)(?:##\s*)?5\.\s*Welche Dateien h[^\n]*\n"
        r"(.*?)(?=\n##\s|\nDEINE ROLLE|\Z)",
        prosa or "", _re.DOTALL,
    )
    if not m:
        return False
    block = m.group(1)
    for line in block.splitlines():
        if _re.match(r"^\s*-\s*\(keine\)\s*$", line):
            return True
    return False

def _leite_deps_deterministisch(
    tasks: list[dict], prosa: str = "", pd=None, pn="?",
    *, audit_call: Callable[..., object] | None = None,
) -> list[dict]:
    """OP-163b: Deps aus Architect-Block 5, sonst aus task_files.

    Zwei Pfade:
    1. Architect-Block 5 vorhanden -> Datei-zu-Datei-Deps, gemappt
       auf Task-IDs via task_files[0]. Block hat Vorrang.
    2. Kein Block -> Heuristik ueber task_files:
       test/baseline/doku warten auf alle code-Tasks.

    Loop-Test-4-Bug (2026-11-05): alle 8 Tasks ohne deps.
    Nachfolger-Design: Architect schreibt Block 5 strukturiert.
    """
    if not tasks:
        return tasks
    found, arch_deps = _parse_architect_deps_block(prosa)

    _datei_to_id: dict[str, str] = {}
    for t in tasks:
        if not isinstance(t, dict):
            continue
        files = t.get("task_files") or []
        _tid = t.get("id", "")
        for f in files:
            if isinstance(f, str) and f not in _datei_to_id:
                _datei_to_id[f] = _tid

    # OP-187: Architect-Aussage anwenden (Multi-File-Support).
    # Jede Task kann mehrere task_files haben; fuer jede Datei im
    # Architect-Block wird die Dep auf die produzierende Task gemappt.
    _arch_tasks: set[str] = set()
    _quelle_parts: list[str] = []
    heuristic_cycle_edges_skipped = 0
    heuristic_edges_skipped: list[dict[str, str]] = []
    if found and arch_deps:
        _quelle_parts.append("architect")
        for t in tasks:
            if not isinstance(t, dict):
                continue
            _tid = t.get("id")
            files = t.get("task_files") or []
            _dep_ids: set[str] = set()
            _has_arch = False
            for f in files:
                if not isinstance(f, str):
                    continue
                if f in arch_deps:
                    _has_arch = True
                    for d in arch_deps[f]:
                        if d in _datei_to_id:
                            _dep_ids.add(_datei_to_id[d])
            if not _has_arch:
                continue
            if isinstance(_tid, str):
                _arch_tasks.add(_tid)
            _alt = set(t.get("dependencies") or [])
            _merged = sorted((_alt | _dep_ids) - {_tid})
            t["dependencies"] = _merged

    # OP-187: explizite "keine"-Aussage im Architect-Block 5 -> keine
    # Heuristik (Architect sagt bewusst "keine Abhaengigkeiten").
    _explicit_keine = _check_explicit_keine_in_prosa(prosa)

    if not _explicit_keine:
        _CODE = (".py", ".pyi")
        _DOKU = (".md", ".rst", ".txt")

        def _klass(t: dict) -> str:
            files = t.get("task_files") or []
            if not files:
                return "unbekannt"
            _fs = " ".join(str(f) for f in files)
            if "state_inventory" in _fs or "baseline" in _fs.lower():
                return "baseline"
            for f in files:
                if not isinstance(f, str):
                    continue
                fl = f.lower()
                if fl.endswith(_DOKU):
                    return "doku"
                if ("/tests/" in fl or fl.startswith(("tests/", "test_")) or "/test_" in fl or "_test.py" in fl):
                    return "test"
                if fl.endswith(_CODE):
                    return "code"
            return "unbekannt"

        _klassen: dict[str, str] = {}
        for _t_k in tasks:
            if not isinstance(_t_k, dict):
                continue
            _tid_k = _t_k.get("id")
            if isinstance(_tid_k, str):
                _klassen[_tid_k] = _klass(_t_k)
        _code_ids = sorted(i for i, k in _klassen.items() if k == "code")
        _test_ids = sorted(i for i, k in _klassen.items() if k == "test")
        _base_ids = sorted(i for i, k in _klassen.items() if k == "baseline")
        if _code_ids:
            for t in tasks:
                if not isinstance(t, dict):
                    continue
                _tid = t.get("id")
                if not isinstance(_tid, str):
                    continue
                if _tid in _arch_tasks:
                    # Architect-Aussage hat Vorrang — keine Heuristik.
                    continue
                _kl = _klassen.get(_tid, "unbekannt")
                _neue: list[str] = []
                if _kl in ("test", "baseline"):
                    _neue = [x for x in _code_ids if x != _tid]
                elif _kl == "doku":
                    _neue = [
                        x for x in (_code_ids + _test_ids + _base_ids)
                        if x != _tid
                    ]
                if _neue:
                    _alt = set(t.get("dependencies") or [])
                    for dependency_id in sorted(set(_neue) - _alt):
                        if _dependency_edge_would_cycle(
                            tasks, _tid, dependency_id,
                        ):
                            heuristic_cycle_edges_skipped += 1
                            if len(heuristic_edges_skipped) < 40:
                                heuristic_edges_skipped.append({
                                    "task_id": _tid,
                                    "dependency_id": dependency_id,
                                })
                            continue
                        _alt.add(dependency_id)
                    t["dependencies"] = sorted(_alt)
        if _arch_tasks:
            _quelle_parts.append("heuristik-ergaenzung")
        else:
            _quelle_parts.append("heuristik")
    else:
        _quelle_parts.append("architect-explicit-keine")

    if not _quelle_parts:
        _quelle_parts.append("fallback")
    _quelle = "+".join(_quelle_parts)

    if pd is not None:
        try:
            _mit = sum(
                1 for t in tasks
                if isinstance(t, dict) and t.get("dependencies"))
            payload = {
                "quelle": _quelle,
                "tasks_mit_deps": _mit,
                "heuristic_cycle_edges_skipped": heuristic_cycle_edges_skipped,
                "heuristic_edges_skipped": heuristic_edges_skipped,
            }
            if audit_call is None:
                audit("planner_deps_abgeleitet", payload, pd, pn)
            else:
                audit_call("planner_deps_abgeleitet", payload, pd, pn)
        except Exception:
            pass

    return tasks


def _dependency_edge_would_cycle(
    tasks: list[dict], task_id: str, dependency_id: str,
) -> bool:
    """Return whether adding task_id -> dependency_id closes a cycle.

    Dependencies point from a task to its prerequisites. The new edge is
    cyclic exactly when dependency_id already reaches task_id by following
    prerequisite edges. Only heuristic edges use this guard; explicit planner
    edges remain intact and are rejected by the task-graph validator if bad.
    """
    if task_id == dependency_id:
        return True
    by_id = {
        task.get("id"): task
        for task in tasks
        if isinstance(task, dict) and isinstance(task.get("id"), str)
    }
    pending = [dependency_id]
    visited: set[str] = set()
    while pending:
        current = pending.pop()
        if current == task_id:
            return True
        if current in visited:
            continue
        visited.add(current)
        current_task = by_id.get(current)
        if current_task is None:
            continue
        dependencies = current_task.get("dependencies") or []
        if isinstance(dependencies, list):
            pending.extend(
                dependency for dependency in dependencies
                if isinstance(dependency, str) and dependency not in visited
            )
    return False

def _topo_sort_tasks(
    tasks: list[dict], pd=None, pn="?",
    *, audit_call: Callable[..., object] | None = None,
) -> list[dict]:
    """Compile a task dependency graph or reject it before the plan gate.

    Keeps input order among simultaneously ready tasks. Invalid IDs,
    malformed/dangling/self dependencies and cycles never reach execution.
    """
    if not tasks:
        return tasks
    by_id: dict[str, dict] = {}
    original_index: dict[str, int] = {}
    for index, task in enumerate(tasks):
        if not isinstance(task, dict):
            raise TaskGraphError(f"Task {index + 1} ist kein Objekt.")
        task_id = task.get("id")
        if not isinstance(task_id, str) or not task_id.strip():
            raise TaskGraphError(f"Task {index + 1} hat keine gueltige ID.")
        if task_id in by_id:
            raise TaskGraphError(f"Task-ID doppelt vergeben: {task_id}.")
        by_id[task_id] = task
        original_index[task_id] = index

    indegree = {task_id: 0 for task_id in by_id}
    dependents: dict[str, list[str]] = {task_id: [] for task_id in by_id}
    for task_id, task in by_id.items():
        dependencies = task.get("dependencies") or []
        if not isinstance(dependencies, list):
            raise TaskGraphError(
                f"Abhaengigkeiten von {task_id} muessen eine Liste sein.",
            )
        if any(not isinstance(dep, str) or not dep.strip() for dep in dependencies):
            raise TaskGraphError(
                f"Task {task_id} enthaelt eine ungueltige Abhaengigkeits-ID.",
            )
        if len(set(dependencies)) != len(dependencies):
            raise TaskGraphError(
                f"Task {task_id} enthaelt doppelte Abhaengigkeiten.",
            )
        for dependency in dependencies:
            if dependency == task_id:
                raise TaskGraphError(
                    f"Task {task_id} haengt von sich selbst ab.",
                )
            if dependency not in by_id:
                raise TaskGraphError(
                    f"Task {task_id} verweist auf unbekannte Abhaengigkeit "
                    f"{dependency}.",
                )
            indegree[task_id] += 1
            dependents[dependency].append(task_id)

    ready = sorted(
        [task_id for task_id, degree in indegree.items() if degree == 0],
        key=original_index.__getitem__,
    )
    ordered_ids: list[str] = []
    while ready:
        task_id = ready.pop(0)
        ordered_ids.append(task_id)
        newly_ready: list[str] = []
        for dependent_id in dependents[task_id]:
            indegree[dependent_id] -= 1
            if indegree[dependent_id] == 0:
                newly_ready.append(dependent_id)
        if newly_ready:
            ready.extend(newly_ready)
            ready.sort(key=original_index.__getitem__)

    if len(ordered_ids) != len(by_id):
        cyclic_ids = sorted(
            [task_id for task_id, degree in indegree.items() if degree > 0],
            key=original_index.__getitem__,
        )
        if pd is not None:
            try:
                payload = {
                    "zyklische_ids": cyclic_ids,
                    "anzahl_tasks": len(tasks),
                    "zyklische_kanten": {
                        task_id: sorted(
                            dependency
                            for dependency in (
                                by_id[task_id].get("dependencies") or []
                            )
                            if isinstance(dependency, str)
                        )[:20]
                        for task_id in cyclic_ids[:20]
                    },
                }
                if audit_call is None:
                    audit("planner_deps_zyklus", payload, pd, pn)
                else:
                    audit_call("planner_deps_zyklus", payload, pd, pn)
            except Exception:
                pass
        raise TaskGraphError(
            "Abhaengigkeitszyklus zwischen Tasks: "
            + ", ".join(cyclic_ids),
        )

    return [by_id[task_id] for task_id in ordered_ids]
