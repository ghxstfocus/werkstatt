"""Phase-State fuer Multi-Projekt-Resume (Phase 13, 2026-10-23).

State-of-the-Art-Prinzipien (AICTX, GitHub Copilot Upgrade, universal-dev-standards):
- Repo-lokaler State (YAML unter projects/<name>.phase.yaml).
- Resume: Finde den naechsten pending-Task, ueberspringe done.
- Decision-Log: Warum eine Entscheidung getroffen wurde.
- Failure-Log: Welche Fehler aufgetreten sind (damit sie nicht wiederholt werden).
- Status-Update: Nach jedem Task (pending -> running -> done/failed).

Das ist KEIN Monolith. Nur State-Management.
"""
from __future__ import annotations

import datetime
from pathlib import Path
from typing import Any

import yaml

from werkstatt.paths import projects_dir as _pd

PHASE_DIR = _pd()


class PhaseState:
    """Verwaltet den Phase-State eines Projekts (YAML)."""

    def __init__(self, project_name: str, base_dir: Path | None = None):
        self.project_name = project_name
        self.base_dir = base_dir or PHASE_DIR
        self.path = self.base_dir / f"{project_name}.phase.yaml"
        self.data: dict[str, Any] = {}
        self.run_id: str | None = None

    # --- Laden / Speichern ---

    def exists(self) -> bool:
        return self.path.exists()

    def load(self) -> bool:
        """Lädt den State aus YAML. Gibt False zurück, wenn nicht vorhanden."""
        if not self.path.exists():
            return False
        try:
            with self.path.open(encoding="utf-8") as fh:
                data = yaml.safe_load(fh)
        except (yaml.YAMLError, OSError):
            self.data = {}
            return False

        if data is None:
            data = {}
        if not isinstance(data, dict):
            self.data = {}
            return False

        if "project" in data and data["project"] != self.project_name:
            self.data = {}
            return False
        run_id = data.get("run_id")
        if run_id is not None and (
            not isinstance(run_id, str) or not run_id.strip()
        ):
            self.data = {}
            return False

        criteria_tracking = data.get("criteria_tracking")
        if criteria_tracking is not None and not isinstance(criteria_tracking, bool):
            self.data = {}
            return False

        if "tasks" in data:
            tasks = data["tasks"]
            if tasks is None:
                data["tasks"] = []
            elif not isinstance(tasks, list) or any(
                not isinstance(task, dict) for task in tasks
            ):
                self.data = {}
                return False

        task_ids: set[str] = set()
        has_criterion_refs = False
        for task in data.get("tasks", []):
            task_id = task.get("id")
            dependencies = task.get("dependencies") or []
            criterion_refs = task.get("criterion_refs") or []
            if (
                not isinstance(task_id, str)
                or not task_id.strip()
                or task_id in task_ids
                or not isinstance(dependencies, list)
                or any(not isinstance(dependency, str) for dependency in dependencies)
                or not isinstance(criterion_refs, list)
                or any(
                    not isinstance(ref, str) or not ref.strip()
                    for ref in criterion_refs
                )
            ):
                self.data = {}
                return False
            has_criterion_refs = has_criterion_refs or bool(criterion_refs)
            task_ids.add(task_id)

        if data.get("criteria_tracking") is False and has_criterion_refs:
            self.data = {}
            return False

        self.data = data
        self.run_id = run_id
        return True

    def save(self) -> None:
        """Speichert den State atomar (temp + rename)."""
        if self.run_id:
            self.data["run_id"] = self.run_id
        self.base_dir.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            yaml.safe_dump(self.data, fh, allow_unicode=True, sort_keys=False)
        tmp.replace(self.path)

    def init_new(
        self,
        aufgabe: str,
        tasks: list[dict],
        *,
        tests: list | None = None,
        akzeptanzkriterien: list | None = None,
        phasen: list[dict] | None = None,
    ) -> None:
        """Initialisiert einen neuen Phase-State.

        Vollstaendiger Plan-Checkpoint: tasks + tests + akzeptanz-
        kriterien. Ohne tests+akz wuerde _plan_gate beim Resume
        scheitern und der Planner doch laufen.

        M-323d: phasen optional. Wenn uebergeben, wird die
        Phasen-Struktur (M-323c) persistiert. Resume laedt sie
        ueber .data["phasen"].
        """
        task_ids = [t.get("id", f"t{i}") for i, t in enumerate(tasks, 1)]
        if any(
            not isinstance(task_id, str) or not task_id.strip()
            for task_id in task_ids
        ) or len(set(task_ids)) != len(task_ids):
            raise ValueError("Phase-State braucht eindeutige, nichtleere Task-IDs")
        for task in tasks:
            refs = task.get("criterion_refs") or []
            if not isinstance(refs, list) or any(
                not isinstance(ref, str) or not ref.strip() for ref in refs
            ):
                raise ValueError(
                    "criterion_refs muessen eine Liste nichtleerer IDs sein"
                )

        criteria_tracking = any(
            "criterion_refs" in task for task in tasks
        )
        now = datetime.datetime.now(datetime.UTC).isoformat()
        self.data = {
            "criteria_tracking": criteria_tracking,
            "project": self.project_name,
            "aufgabe": aufgabe,
            "phase_id": f"phase-{now[:10]}",
            "status": "in_progress",
            "created": now,
            "updated": now,
            "tasks": [
                {
                    "id": t.get("id", f"t{i}"),
                    "name": t.get("name", ""),
                    "description": t.get("description", ""),
                    "action": t.get("action"),  # M-323a
                    "phase_id": t.get("phase_id"),  # M-323a
                    "parent_id": t.get("parent_id"),  # M-323a
                    "task_files": t.get("task_files", []),  # M-323a
                    # OP-163b-Bridge: deps aus Planner in PhaseState.
                    # Ohne dieses Feld filtert init_new dependencies
                    # weg, get_next_task sieht keine Deps, Tasks
                    # laufen unabhaengig (Loop-Test-5, 2026-11-05).
                    "dependencies": t.get("dependencies") or [],
                    # OP-398: Kriterienzuordnung muss Resume ueberleben,
                    # damit Zielabgleich dieselben Planbelege verwendet.
                    "criterion_refs": list(t.get("criterion_refs") or []),
                    "status": "pending",
                    "decision": None,
                    "failure": None,
                    # OP-064f: verdict strukturiert (pending|verified|vetoed).
                    # Default pending — verified bei mark_done, vetoed bei
                    # deterministischem Guard-Veto.
                    "verdict": "pending",
                }
                for i, t in enumerate(tasks, 1)
            ],
            "tests": list(tests or []),
            "akzeptanzkriterien": list(akzeptanzkriterien or []),
            "phasen": list(phasen or []),  # M-323d
        }
        self.save()

    # --- Resume ---

    def get_next_task(self) -> dict | None:
        """Findet den naechsten ausfuehrbaren Task (K1).

        Nur 'pending' und 'running' sind ausfuehrbar. 'done', 'failed'
        und 'split' werden uebersprungen — sonst liefert der Loop
        fehlgeschlagene oder zerlegte Tasks erneut (Cursor-Mismatch
        und Re-Split, siehe OFFENE-BLOECKE.md K1).

        OP-163: Tasks mit unerfuellten `dependencies` werden
        uebersprungen. Der Loop-End-Check markiert sie als `blocked`.
        """
        _by_id: dict = {
            t.get("id"): t for t in self.data.get("tasks", [])
            if isinstance(t, dict) and t.get("id")
        }
        for task in self.data.get("tasks", []):
            if task.get("status") not in ("pending", "running"):
                continue
            _deps = task.get("dependencies") or []
            if _deps:
                _unmet = [
                    d for d in _deps
                    if d not in _by_id
                    or _by_id[d].get("status") != "done"
                ]
                if _unmet:
                    continue
            return task
        return None

    def mark_blocked(
        self, task_id: str, *, grund: str = "unknown",
    ) -> None:
        """OP-163: Markiert Task als blockiert (unerfuellte deps)."""
        for task in self.data.get("tasks", []):
            if task.get("id") == task_id:
                task["status"] = "blocked"
                task["failure"] = f"blocked: {grund}"
                return

    def _unmet_dependencies(self, task: dict) -> list[str]:
        """OP-163: Liste der unerfuellten dependency-IDs."""
        _by_id = {
            t.get("id"): t for t in self.data.get("tasks", [])
            if isinstance(t, dict) and t.get("id")
        }
        _deps = task.get("dependencies") or []
        return [
            d for d in _deps
            if d not in _by_id or _by_id[d].get("status") != "done"
        ]

    def resume_failed(self) -> int:
        """Setzt failed-, running- und blockierte Tasks beim Resume zurueck.

        Returns: Anzahl reaktivierter Tasks.
        """
        n = 0
        for task in self.data.get("tasks", []):
            # K1: running-Tasks sind Reste eines abgebrochenen Laufs.
            # OP-163: Blocked-Tasks muessen ebenfalls reaktiviert werden,
            # damit sie nach erfolgreichem Resume ihrer Abhaengigkeit laufen.
            if task.get("status") in ("failed", "running", "blocked"):
                task["status"] = "pending"
                task["failure"] = None
                n += 1
        if n > 0:
            self.save()
        return n

    def get_task(self, task_id: str) -> dict | None:
        for task in self.data.get("tasks", []):
            if task.get("id") == task_id:
                return task
        return None

    # --- Status-Updates ---

    def update_task(
        self,
        task_id: str,
        status: str,
        *,
        decision: str | None = None,
        failure: str | None = None,
    ) -> None:
        """Aktualisiert den Status eines Tasks."""
        task = self.get_task(task_id)
        if task is None:
            return
        task["status"] = status
        if decision is not None:
            task["decision"] = decision
        if failure is not None:
            task["failure"] = failure
        self.data["updated"] = datetime.datetime.now(datetime.UTC).isoformat()
        self.save()

    def mark_vetoed(self, task_id: str, *, grund: str = "unknown") -> None:
        """OP-064a: Sticky-Veto. Einmal vetoed, nur Mensch setzt zurueck.

        Setzt verdict='vetoed' UND status='failed' (damit die ueblichen
        Pfade es als nicht-erledigt sehen). mark_done/mark_human_review
        setzen verdict zurueck auf None/pending (Mensch-Entscheidung).
        """
        task = self.get_task(task_id)
        if task is None:
            return
        task["verdict"] = "vetoed"
        # OP-064a: status NICHT auf failed setzen — sonst greift der
        # Idempotenz-Guard in _task_ende vor dem Veto-Check. verdict
        # ist orthogonal zum status.
        task["failure"] = grund
        self.data["updated"] = datetime.datetime.now(datetime.UTC).isoformat()
        self.save()

    def ist_vetoed(self, task_id: str) -> bool:
        """OP-064a: True, wenn task_id ein sticky-veto hat."""
        task = self.get_task(task_id)
        if task is None:
            return False
        return task.get("verdict") == "vetoed"

    def mark_human_review(
        self, task_id: str, *, grund: str = "unknown",
    ) -> None:
        """OP-060b: Setzt Status human_review (Mensch muss entscheiden)."""
        self.update_task(
            task_id, "human_review", failure=grund,
        )
        self.save()

    def mark_done(self, task_id: str, *, decision: str | None = None) -> None:
        self.update_task(task_id, "done", decision=decision)
        # OP-064f: verdict="verified" bei JEDEM mark_done.
        # Vorher: nur bei Veto-Override. Das fuehrte dazu, dass
        # normal-done Tasks verdict=None hatten — Semantik invertiert.
        # Jetzt: pending -> verified bei Erfolg, pending -> vetoed
        # bei deterministischem Guard-Veto. Mensch-Override (mark_done
        # auf vetoed) wechselt vetoed -> verified.
        _t = self.get_task(task_id)
        if _t is not None:
            _t["verdict"] = "verified"
            self.save()

    def _propagate_failed_to_parents(self, task_id: str) -> None:
        """K38: Wenn alle Kinder eines Parents failed sind, Parent failed.

        Rekursiv bis root. Verhindert inkonsistenten Zustand:
        Parent bleibt 'split', obwohl alle Kinder failed sind.
        """
        # Finde Task und Parent.
        task = None
        for t in self.data.get("tasks", []):
            if t.get("id") == task_id:
                task = t
                break
        if not task:
            return
        parent_id = task.get("parent_id")
        # Wenn kein parent_id, versuche Prefix-Ableitung (t2_a -> t2).
        # Aber: _llm_split_einzel_task setzt parent_id nicht immer.
        # Praktisch: wir muessen den Parent aus ID-Prefix oder aus
        # anderen Tasks finden. Wir suchen Tasks, deren ID Prefix
        # von task_id ist (z.B. t2 fuer t2_a).
        if not parent_id:
            # Prefix-Suche: task_id "t2_a_c" -> Kandidaten t2_a, t2
            # Wir pruefen alle Tasks: ist task_id ein Kind von X?
            for t in self.data.get("tasks", []):
                tid = t.get("id", "")
                # SIM102: Bedingung zusammengezogen.
                if (
                    tid
                    and task_id.startswith(tid + "_")
                    and tid != task_id
                    and (not parent_id or len(tid) > len(parent_id))
                ):
                    parent_id = tid
        if not parent_id:
            return
        # Sammle Kinder dieses Parents.
        children = [
            t for t in self.data.get("tasks", [])
            if t.get("id", "").startswith(parent_id + "_")
            and t.get("id") != parent_id
            and len(t.get("id", "").split("_")) == len(parent_id.split("_")) + 1
        ]
        if not children:
            return
        # Wenn alle direkten Kinder failed -> Parent failed.
        # OP-060b: human_review-Kinder verhindern Parent-failed.
        _all_failed = all(
            c.get("status") == "failed" for c in children
        )
        _has_review = any(
            c.get("status") == "human_review" for c in children
        )
        if _all_failed and not _has_review:
            for t in self.data.get("tasks", []):
                if t.get("id") == parent_id:
                    if t.get("status") != "failed":
                        t["status"] = "failed"
                        t["failure"] = "kinder_failed"
                        # Rekursiv weiter.
                        self._propagate_failed_to_parents(parent_id)
                    break

    def mark_failed(self, task_id: str, *, failure: str) -> None:
        """K38: mark_failed + propagation an Parents."""
        self.update_task(task_id, "failed", failure=failure)
        # K38: Wenn alle Kinder failed sind, Parent failed.
        self._propagate_failed_to_parents(task_id)
        self.save()

    def mark_running(self, task_id: str) -> None:
        self.update_task(task_id, "running")

    # --- Fortschritt ---

    def criteria_progress(self) -> dict[str, Any]:
        """Projektfortschritt ueber explizit zugeordnete Akzeptanzkriterien.

        Ein Kriterium gilt erst als abgedeckt, wenn mindestens ein Task mit
        diesem AC-Verweis den gespeicherten Status done hat. Legacy-Plaene
        ohne Referenzen werden als ungetrackt ausgewiesen.
        """
        criteria = self.data.get("akzeptanzkriterien")
        tasks = self.data.get("tasks")
        tracking_marker = self.data.get("criteria_tracking")
        tracked = (
            tracking_marker
            if isinstance(tracking_marker, bool)
            else isinstance(tasks, list) and any(
                isinstance(task, dict) and task.get("criterion_refs")
                for task in tasks
            )
        )
        if not tracked:
            return {
                "tracked": False,
                "valid": True,
                "covered": [],
                "uncovered": [],
                "error": None,
            }

        if (
            not isinstance(criteria, list)
            or not criteria
            or any(not isinstance(item, str) or not item.strip() for item in criteria)
            or not isinstance(tasks, list)
        ):
            return {
                "tracked": True,
                "valid": False,
                "covered": [],
                "uncovered": [],
                "error": "invalid_acceptance_criteria",
            }

        expected = {f"AC{index}" for index in range(1, len(criteria) + 1)}
        assigned: set[str] = set()
        covered: set[str] = set()
        for task in tasks:
            if not isinstance(task, dict):
                return {
                    "tracked": True,
                    "valid": False,
                    "covered": sorted(covered),
                    "uncovered": sorted(expected - covered),
                    "error": "invalid_task_record",
                }
            refs = task.get("criterion_refs")
            if (
                not isinstance(refs, list)
                or not refs
                or any(not isinstance(ref, str) or not ref.strip() for ref in refs)
                or len(set(refs)) != len(refs)
                or set(refs) - expected
            ):
                return {
                    "tracked": True,
                    "valid": False,
                    "covered": sorted(covered),
                    "uncovered": sorted(expected - covered),
                    "error": f"invalid_criterion_refs:{task.get('id', '?')}",
                }
            assigned.update(refs)
            if task.get("status") == "done":
                covered.update(refs)

        return {
            "tracked": True,
            "valid": assigned == expected,
            "covered": sorted(covered, key=lambda item: int(item[2:])),
            "uncovered": sorted(expected - covered, key=lambda item: int(item[2:])),
            "error": None if assigned == expected else "criteria_not_assigned",
        }

    def progress(self) -> dict[str, int]:
        """Gibt den Fortschritt zurueck (done/total)."""
        tasks = self.data.get("tasks", [])
        total = len(tasks)
        done = sum(1 for t in tasks if t.get("status") == "done")
        failed = sum(1 for t in tasks if t.get("status") == "failed")
        return {"total": total, "done": done, "failed": failed, "pending": total - done - failed}

    def is_complete(self) -> bool:
        return self.progress()["done"] == self.progress()["total"]
