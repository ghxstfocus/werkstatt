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
import hashlib
import json
from pathlib import Path, PureWindowsPath
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

        if (
            "criteria_tracking" in data
            and not isinstance(data["criteria_tracking"], bool)
        ):
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

    def approved_plan_fingerprint(self) -> str | None:
        """Hash only immutable, human-approved plan content.

        Mutable task execution status and evidence are deliberately excluded
        so the same approved graph remains valid while the run advances.
        """
        tasks = self.data.get("tasks")
        if not isinstance(tasks, list) or not tasks:
            return None
        task_fields = (
            "id", "name", "description", "action", "phase_id", "parent_id",
            "task_files", "dependencies", "criterion_refs",
        )
        immutable_tasks: list[dict[str, Any]] = []
        for task in tasks:
            if not isinstance(task, dict):
                return None
            immutable_tasks.append({
                field: task.get(field)
                for field in task_fields if field in task
            })
        payload = {
            "version": 1,
            "project": self.data.get("project"),
            "goal": self.data.get("aufgabe"),
            "criteria_tracking": self.data.get("criteria_tracking"),
            "tasks": immutable_tasks,
            "tests": self.data.get("tests"),
            "akzeptanzkriterien": self.data.get("akzeptanzkriterien"),
            "phasen": self.data.get("phasen"),
        }
        try:
            encoded = json.dumps(
                payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        except (TypeError, ValueError, UnicodeEncodeError):
            return None
        return hashlib.sha256(encoded).hexdigest()

    def bind_approved_plan(self) -> str:
        """Persist the fingerprint after the plan human gate approves it."""
        fingerprint = self.approved_plan_fingerprint()
        if fingerprint is None:
            raise ValueError("Freigegebener Plan ist nicht kanonisierbar")
        self.data["plan_checkpoint_version"] = 1
        self.data["approved_plan_sha256"] = fingerprint
        return fingerprint

    def approved_plan_is_current(self) -> bool:
        """Check that mutable phase state still matches its approved plan."""
        if self.data.get("plan_checkpoint_version") != 1:
            return False
        fingerprint = self.approved_plan_fingerprint()
        return (
            fingerprint is not None
            and self.data.get("approved_plan_sha256") == fingerprint
        )

    def record_phase_end_review(
        self, *, worktree_fingerprint: str,
    ) -> None:
        """Bind completed phase review to this run, plan, and exact worktree."""
        plan_fingerprint = self.approved_plan_fingerprint()
        if (
            not self.run_id
            or plan_fingerprint is None
            or not self.approved_plan_is_current()
            or len(worktree_fingerprint) != 64
            or any(char not in "0123456789abcdef" for char in worktree_fingerprint)
        ):
            raise ValueError("Phase-Review kann nicht sicher gebunden werden")
        self.data["phase_end_review_checkpoint"] = {
            "schema_version": 1,
            "run_id": self.run_id,
            "plan_sha256": plan_fingerprint,
            "worktree_sha256": worktree_fingerprint,
            "status": "approved",
        }
        self.save()

    def phase_end_review_is_current(
        self, *, worktree_fingerprint: str | None,
    ) -> bool:
        """Check the phase-review checkpoint against current plan and bytes."""
        review = self.data.get("phase_end_review_checkpoint")
        plan_fingerprint = self.approved_plan_fingerprint()
        return bool(
            isinstance(review, dict)
            and review.get("schema_version") == 1
            and review.get("status") == "approved"
            and review.get("run_id") == self.run_id
            and review.get("plan_sha256") == plan_fingerprint
            and review.get("worktree_sha256") == worktree_fingerprint
            and isinstance(worktree_fingerprint, str)
            and self.approved_plan_is_current()
        )

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
            task.get("criterion_refs") for task in tasks
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
                    "failure_detail": None,
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

    def append_followup_tasks(
        self,
        tasks: list[dict[str, Any]],
        *,
        criteria: list[str],
        tests: list[Any],
        phases: list[dict[str, Any]],
        followup_id: str,
    ) -> list[str]:
        """Append an approved chat follow-up to the persisted task graph.

        The stable follow-up ID makes replay after a crash idempotent. The
        caller must validate the complete candidate graph and obtain its plan
        approval before calling this method.
        """
        if not isinstance(followup_id, str) or not followup_id.strip():
            raise ValueError("followup_id muss nichtleer sein")
        existing_tasks = self.data.get("tasks", [])
        if not isinstance(existing_tasks, list):
            raise TypeError("Phase-State hat keine gueltige Task-Liste")
        already_added = [
            task for task in existing_tasks
            if isinstance(task, dict)
            and task.get("source_followup_id") == followup_id
        ]
        if already_added:
            return [str(task["id"]) for task in already_added]

        if not isinstance(tasks, list) or any(
            not isinstance(task, dict) for task in tasks
        ):
            raise ValueError("Follow-up-Tasks muessen eine Liste von Objekten sein")
        if not isinstance(criteria, list) or any(
            not isinstance(criterion, str) or not criterion.strip()
            for criterion in criteria
        ):
            raise ValueError("Follow-up-Kriterien muessen nichtleere Texte sein")
        if not isinstance(tests, list):
            raise TypeError("Follow-up-Tests muessen eine Liste sein")
        if not isinstance(phases, list) or any(
            not isinstance(phase, dict) for phase in phases
        ):
            raise ValueError("Follow-up-Phasen muessen eine Liste von Objekten sein")

        existing_ids = {
            task.get("id") for task in existing_tasks
            if isinstance(task, dict) and isinstance(task.get("id"), str)
        }
        incoming_ids = [task.get("id") for task in tasks]
        if (
            any(not isinstance(task_id, str) or not task_id.strip()
                for task_id in incoming_ids)
            or len(set(incoming_ids)) != len(incoming_ids)
            or existing_ids.intersection(incoming_ids)
        ):
            raise ValueError("Follow-up-Tasks brauchen eindeutige IDs")

        all_ids = existing_ids | set(incoming_ids)
        current_phases = self.data.get("phasen", [])
        if not isinstance(current_phases, list):
            raise TypeError("Phase-State hat ungueltige Phasen")
        existing_phase_ids = {
            phase.get("id") for phase in current_phases
            if isinstance(phase, dict) and isinstance(phase.get("id"), str)
        }
        incoming_phase_ids = [phase.get("id") for phase in phases]
        if (
            any(not isinstance(phase_id, str) or not phase_id.strip()
                for phase_id in incoming_phase_ids)
            or len(set(incoming_phase_ids)) != len(incoming_phase_ids)
            or existing_phase_ids.intersection(incoming_phase_ids)
        ):
            raise ValueError("Follow-up-Phasen brauchen eindeutige IDs")
        all_phase_ids = existing_phase_ids | set(incoming_phase_ids)
        normalized: list[dict[str, Any]] = []
        for task in tasks:
            dependencies = task.get("dependencies") or []
            refs = task.get("criterion_refs") or []
            phase_id = task.get("phase_id")
            if (
                not isinstance(dependencies, list)
                or any(dep not in all_ids for dep in dependencies)
                or (phase_id is not None and phase_id not in all_phase_ids)
                or not isinstance(refs, list)
                or any(
                    not isinstance(ref, str)
                    or not ref.startswith("AC")
                    or not ref[2:].isdigit()
                    or int(ref[2:]) < 1
                    or int(ref[2:]) > len(criteria)
                    for ref in refs
                )
            ):
                raise ValueError("Follow-up-Task hat ungueltige Abhaengigkeiten/Kriterien")
            normalized.append({
                "id": task["id"],
                "name": task.get("name", ""),
                "description": task.get("description", ""),
                "action": task.get("action"),
                "phase_id": task.get("phase_id"),
                "parent_id": task.get("parent_id"),
                "task_files": task.get("task_files", []),
                "dependencies": dependencies,
                "criterion_refs": refs,
                "status": "pending",
                "decision": None,
                "failure": None,
                "verdict": "pending",
                "source_followup_id": followup_id,
            })

        current_criteria = self.data.get("akzeptanzkriterien", [])
        current_tests = self.data.get("tests", [])
        if not isinstance(current_criteria, list):
            raise TypeError("Phase-State hat ungueltige Akzeptanzkriterien")
        if not isinstance(current_tests, list):
            raise TypeError("Phase-State hat ungueltige Tests")
        for phase in phases:
            phase_tasks = phase.get("tasks") or []
            parent_id = phase.get("parent_id")
            if (
                not isinstance(phase_tasks, list)
                or any(task_id not in all_ids for task_id in phase_tasks)
                or (parent_id is not None and parent_id not in all_phase_ids)
            ):
                raise ValueError("Follow-up-Phase hat ungueltige Tasks/Elternphase")
        self.data["tasks"] = existing_tasks + normalized
        self.data["akzeptanzkriterien"] = list(criteria)
        self.data["tests"] = current_tests + list(tests)
        self.data["phasen"] = current_phases + phases
        self.data.pop("phase_end_review_checkpoint", None)
        self.data["criteria_tracking"] = bool(
            self.data.get("criteria_tracking")
            or any(task.get("criterion_refs") for task in normalized)
        )
        # The caller reaches this method only after the combined follow-up
        # plan passed validation and its human plan gate. Bind that approved
        # graph before saving so the run coordinator can resume it directly.
        self.bind_approved_plan()
        self.data["updated"] = datetime.datetime.now(datetime.UTC).isoformat()
        self.save()
        return [str(task["id"]) for task in normalized]

    def supersede_failed_tasks(
        self, task_ids: list[str], *, replan_id: str,
    ) -> None:
        """Retain failed task evidence while removing replaced nodes from work."""
        if (
            not task_ids
            or any(not isinstance(task_id, str) or not task_id for task_id in task_ids)
            or not isinstance(replan_id, str)
            or not replan_id
        ):
            raise ValueError("Ungueltige Task-/Replan-Identitaet")
        by_id = {
            task.get("id"): task
            for task in self.data.get("tasks", [])
            if isinstance(task, dict)
        }
        for task_id in task_ids:
            task = by_id.get(task_id)
            if not isinstance(task, dict) or task.get("status") not in {
                "failed", "superseded",
            }:
                raise ValueError("Zu ersetzender Task ist nicht fehlgeschlagen")
            if (
                task.get("status") == "superseded"
                and task.get("superseded_by_replan_id") != replan_id
            ):
                raise ValueError("Task wurde bereits durch einen anderen Plan ersetzt")
        changed = False
        for task_id in task_ids:
            task = by_id[task_id]
            if task.get("status") == "failed":
                task["superseded_failure"] = task.get("failure")
                task["superseded_by_replan_id"] = replan_id
                task["status"] = "superseded"
                changed = True
        if changed:
            self.data["updated"] = datetime.datetime.now(datetime.UTC).isoformat()
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
            if (
                isinstance(task, dict)
                and task.get("verification_pending") is True
                and task.get("status") in ("done", "pending", "running")
            ):
                verification_task = dict(task)
                if task.get("action") == "read":
                    verification_task["read_reverification"] = True
                else:
                    verification_task["action"] = "verify"
                    verification_task["verification_only"] = True
                return verification_task
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

    def queue_stale_task_reverification(self) -> list[str]:
        """Queue completed tasks whose persisted file evidence went stale."""
        queued: list[str] = []
        for task in self.data.get("tasks", []):
            if (
                not isinstance(task, dict)
                or task.get("status") != "done"
                or task.get("verification_pending") is True
            ):
                continue
            task_id = task.get("id")
            if task.get("action") == "read":
                if (
                    not isinstance(task_id, str)
                    or self.task_read_evidence_is_current(
                        task_id, task.get("read_evidence"),
                    )
                ):
                    continue
                task["verification_pending"] = True
                queued.append(task_id)
                continue
            if not task.get("criterion_refs"):
                continue
            evidence = task.get("verify_evidence")
            if (
                not isinstance(task_id, str)
                or self.task_verify_evidence_is_current(task_id, evidence)
                or self._task_file_hashes(task.get("task_files")) is None
            ):
                continue
            task["verification_pending"] = True
            queued.append(task_id)
        if queued:
            self.data["updated"] = datetime.datetime.now(datetime.UTC).isoformat()
            self.save()
        return queued

    def queue_stale_read_dependencies(self, task_id: str) -> list[str]:
        """Re-read stale read-task ancestors before dispatching a dependent."""
        target = self.get_task(task_id)
        if not isinstance(target, dict):
            return []
        by_id = {
            task.get("id"): task
            for task in self.data.get("tasks", [])
            if isinstance(task, dict) and isinstance(task.get("id"), str)
        }
        pending = list(target.get("dependencies") or [])
        seen: set[str] = set()
        read_dependencies: list[dict[str, Any]] = []
        while pending:
            dependency_id = pending.pop()
            if not isinstance(dependency_id, str) or dependency_id in seen:
                continue
            seen.add(dependency_id)
            dependency = by_id.get(dependency_id)
            if not isinstance(dependency, dict):
                continue
            pending.extend(dependency.get("dependencies") or [])
            if dependency.get("action") == "read":
                read_dependencies.append(dependency)

        queued: list[str] = []
        for dependency in read_dependencies:
            dependency_id = dependency.get("id")
            if (
                dependency.get("status") != "done"
                or dependency.get("verification_pending") is True
                or not isinstance(dependency_id, str)
                or self.task_read_evidence_is_current(
                    dependency_id, dependency.get("read_evidence"),
                )
            ):
                continue
            dependency["verification_pending"] = True
            queued.append(dependency_id)
        if queued:
            self.data["updated"] = datetime.datetime.now(datetime.UTC).isoformat()
            self.save()
        return queued

    def record_task_read_evidence(
        self,
        task_id: str,
        files: list[dict[str, Any]],
    ) -> bool:
        """Persist provenance for every file actually read by a read task."""
        task = self.get_task(task_id)
        if not isinstance(task, dict) or task.get("action") != "read":
            return False
        task_files = task.get("task_files")
        if not isinstance(task_files, list) or not task_files:
            return False
        normalized = [
            item.replace("\\", "/")
            for item in task_files
            if isinstance(item, str)
        ]
        if len(normalized) != len(task_files) or len(set(normalized)) != len(
            normalized
        ):
            return False
        evidence_files: dict[str, dict[str, Any]] = {}
        for item in files:
            path = item.get("file")
            digest = item.get("sha256")
            size = item.get("bytes")
            lines = item.get("lines")
            if (
                not isinstance(path, str)
                or path not in normalized
                or not isinstance(digest, str)
                or len(digest) != 64
                or not isinstance(size, int)
                or isinstance(size, bool)
                or size < 0
                or not isinstance(lines, int)
                or isinstance(lines, bool)
                or lines < 0
                or path in evidence_files
            ):
                return False
            evidence_files[path] = {
                "sha256": digest,
                "bytes": size,
                "lines": lines,
            }
        if set(evidence_files) != set(normalized):
            return False
        current_hashes = self._task_file_hashes(normalized)
        if current_hashes is None or current_hashes != {
            path: value["sha256"] for path, value in evidence_files.items()
        }:
            return False
        task["read_evidence"] = {
            "schema_version": 1,
            "task_id": task_id,
            "run_id": self.run_id,
            "task_files": sorted(normalized),
            "files": evidence_files,
            "read_at": datetime.datetime.now(datetime.UTC).isoformat(),
        }
        task.pop("verification_pending", None)
        self.data["updated"] = datetime.datetime.now(datetime.UTC).isoformat()
        self.save()
        return True

    def task_read_evidence_is_current(
        self,
        task_id: str,
        evidence: object,
    ) -> bool:
        """Validate read evidence against this task and current source bytes."""
        task = self.get_task(task_id)
        if not isinstance(task, dict) or not isinstance(evidence, dict):
            return False
        task_files = task.get("task_files")
        recorded_files = evidence.get("files")
        normalized = (
            [item.replace("\\", "/") for item in task_files]
            if isinstance(task_files, list)
            and all(isinstance(item, str) for item in task_files)
            else None
        )
        if (
            task.get("action") != "read"
            or evidence.get("schema_version") != 1
            or evidence.get("task_id") != task_id
            or evidence.get("run_id") != self.run_id
            or normalized is None
            or not normalized
            or evidence.get("task_files") != sorted(normalized)
            or not isinstance(recorded_files, dict)
            or set(recorded_files) != set(normalized)
        ):
            return False
        current_hashes = self._task_file_hashes(normalized)
        if current_hashes is None:
            return False
        return all(
            isinstance(recorded_files.get(path), dict)
            and recorded_files[path].get("sha256") == digest
            for path, digest in current_hashes.items()
        )

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

    def resume_failed(self, *, preserve_failed: bool = False) -> int:
        """Reaktiviert Tasks beim Resume.

        `preserve_failed` laesst terminal fehlgeschlagene Tasks unangetastet,
        wenn ein Checkpoint stattdessen eine gezielte Recovery-Neuplanung
        verlangt. Abgebrochene `running`-Tasks und `blocked`-Tasks bleiben
        unabhaengig davon reaktivierbar.

        Returns: Anzahl reaktivierter Tasks.
        """
        n = 0
        for task in self.data.get("tasks", []):
            # K1: running-Tasks sind Reste eines abgebrochenen Laufs.
            # OP-163: Blocked-Tasks muessen ebenfalls reaktiviert werden,
            # damit sie nach erfolgreichem Resume ihrer Abhaengigkeit laufen.
            retryable = {"running", "blocked"}
            if not preserve_failed:
                retryable.add("failed")
            if task.get("status") in retryable:
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

    def _task_file_hashes(self, task_files: object) -> dict[str, str] | None:
        """Hash current, project-local task files for verify provenance."""
        if (
            not isinstance(task_files, list)
            or not task_files
            or len(task_files) > 50
            or self.base_dir.name != ".werkstatt"
        ):
            return None
        try:
            project_root = self.base_dir.parent.resolve(strict=True)
        except (OSError, RuntimeError):
            return None
        hashes: dict[str, str] = {}
        for raw_path in task_files:
            if (
                not isinstance(raw_path, str)
                or not raw_path.strip()
                or len(raw_path) > 500
            ):
                return None
            relative = Path(raw_path)
            if (
                relative.is_absolute()
                or PureWindowsPath(raw_path).is_absolute()
                or ".." in relative.parts
            ):
                return None
            rel_path = relative.as_posix()
            try:
                target = (project_root / relative).resolve(strict=True)
                target.relative_to(project_root)
                if not target.is_file():
                    return None
                digest = hashlib.sha256()
                with target.open("rb") as source:
                    for chunk in iter(lambda: source.read(1024 * 1024), b""):
                        digest.update(chunk)
            except (OSError, RuntimeError, ValueError):
                return None
            hashes[rel_path] = digest.hexdigest()
        if len(hashes) != len(task_files):
            return None
        return hashes

    def task_verify_evidence_is_current(
        self,
        task_id: str,
        evidence: object,
    ) -> bool:
        """Check evidence still describes this task's current file content."""
        task = self.get_task(task_id)
        if not isinstance(task, dict) or not isinstance(evidence, dict):
            return False
        refs = task.get("criterion_refs")
        if (
            evidence.get("schema_version") != 1
            or evidence.get("task_id") != task_id
            or evidence.get("phase") != "post_build"
            or not isinstance(refs, list)
            or evidence.get("criterion_refs") != refs
            or not isinstance(self.run_id, str)
            or evidence.get("run_id") != self.run_id
        ):
            return False
        task_files = task.get("task_files")
        normalized_task_files = (
            sorted(path.replace("\\", "/") for path in task_files)
            if isinstance(task_files, list)
            and all(isinstance(path, str) for path in task_files)
            else None
        )
        if evidence.get("task_files") != normalized_task_files:
            return False
        recorded_hashes = evidence.get("task_file_sha256")
        if not isinstance(recorded_hashes, dict):
            return False
        current_hashes = self._task_file_hashes(task_files)
        if current_hashes is None or current_hashes != recorded_hashes:
            return False
        file_set = set(current_hashes)
        stages = evidence.get("stages")
        if not isinstance(stages, list):
            return False
        for stage in stages:
            if not isinstance(stage, dict):
                continue
            stage_id = stage.get("stage_id")
            scope_files = stage.get("scope_files")
            if (
                stage.get("ok") is True
                and stage.get("exit_code") == 0
                and isinstance(stage_id, str)
                and stage_id.strip()
                and isinstance(scope_files, list)
                and any(
                    isinstance(path, str)
                    and path.replace("\\", "/") in file_set
                    for path in scope_files
                )
            ):
                return True
        return False

    def record_task_verify_evidence(
        self,
        task_id: str,
        results: object,
        *,
        phase: str,
    ) -> bool:
        """Persist successful verify stages against the criterion-linked task."""
        task = self.get_task(task_id)
        refs = task.get("criterion_refs") if isinstance(task, dict) else None
        task_files = task.get("task_files") if isinstance(task, dict) else None
        if (
            not isinstance(task, dict)
            or not isinstance(refs, list)
            or not refs
            or phase != "post_build"
            or not isinstance(results, list)
            or not isinstance(self.run_id, str)
            or not self.run_id
        ):
            return False
        task_file_hashes = self._task_file_hashes(task_files)
        if task_file_hashes is None:
            return False
        task_file_set = set(task_file_hashes)

        stages: list[dict[str, Any]] = []
        for result in results:
            if not isinstance(result, dict):
                continue
            stage_id = result.get("stage_id")
            exit_code = result.get("exit_code")
            if (
                result.get("ok") is not True
                or not isinstance(stage_id, str)
                or not stage_id.strip()
                or not isinstance(exit_code, int)
                or isinstance(exit_code, bool)
                or exit_code != 0
            ):
                continue
            scope_files = result.get("scope_files")
            if (
                not isinstance(scope_files, list)
                or not any(
                    isinstance(path, str)
                    and path.replace("\\", "/") in task_file_set
                    for path in scope_files
                )
            ):
                continue
            stage: dict[str, Any] = {
                "stage_id": stage_id[:120],
                "exit_code": 0,
                "ok": True,
                "scope_files": sorted({
                    path.replace("\\", "/")
                    for path in scope_files
                    if isinstance(path, str)
                    and path.replace("\\", "/") in task_file_set
                }),
            }
            artifact_hash = result.get("artifact_sha256")
            if isinstance(artifact_hash, str) and artifact_hash:
                stage["artifact_sha256"] = artifact_hash[:128]
            stages.append(stage)
        if not stages:
            return False

        task["verify_evidence"] = {
            "schema_version": 1,
            "task_id": task_id,
            "phase": phase,
            "criterion_refs": list(refs),
            "task_files": sorted(task_file_set),
            "task_file_sha256": task_file_hashes,
            "run_id": self.run_id,
            "verified_at": datetime.datetime.now(datetime.UTC).isoformat(),
            "stages": stages,
        }
        self.data["updated"] = datetime.datetime.now(datetime.UTC).isoformat()
        self.save()
        return True

    # --- Status-Updates ---

    def update_task(
        self,
        task_id: str,
        status: str,
        *,
        decision: str | None = None,
        failure: str | None = None,
        failure_detail: str | None = None,
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
        if failure_detail is not None:
            task["failure_detail"] = failure_detail[:1200]
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
            _t.pop("verification_pending", None)
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

    def mark_failed(
        self, task_id: str, *, failure: str, detail: str | None = None,
    ) -> None:
        """K38: mark_failed + propagation an Parents."""
        self.update_task(
            task_id, "failed", failure=failure,
            failure_detail=detail[:1200] if detail else None,
        )
        task = self.get_task(task_id)
        if task is not None:
            task.pop("verification_pending", None)
        # K38: Wenn alle Kinder failed sind, Parent failed.
        self._propagate_failed_to_parents(task_id)
        self.save()

    def mark_running(self, task_id: str) -> None:
        self.update_task(task_id, "running")

    # --- Fortschritt ---

    def criteria_progress(self) -> dict[str, Any]:
        """Projektfortschritt ueber explizit zugeordnete Akzeptanzkriterien.

        Ein Kriterium gilt erst als abgedeckt, wenn alle Tasks mit diesem
        AC-Verweis den gespeicherten Status done haben. Das verhindert, dass
        ein erledigter Teil eines gesplitteten Tasks das Gesamtkriterium
        vorzeitig abdeckt. Legacy-Plaene ohne Referenzen bleiben ungetrackt.
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
        assigned_tasks: dict[str, list[dict[str, Any]]] = {}
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
            if task.get("status") == "superseded":
                continue
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
            for ref in refs:
                assigned_tasks.setdefault(ref, []).append(task)

        # A criterion may be shared by several tasks after ADaPT splits a
        # larger task. It is covered only when every active task assigned to
        # it is done; one successful child cannot stand in for its siblings.
        covered = {
            ref
            for ref, criterion_tasks in assigned_tasks.items()
            if criterion_tasks
            and all(task.get("status") == "done" for task in criterion_tasks)
        }

        return {
            "tracked": True,
            "valid": assigned == expected,
            "covered": sorted(covered, key=lambda item: int(item[2:])),
            "uncovered": sorted(expected - covered, key=lambda item: int(item[2:])),
            "error": None if assigned == expected else "criteria_not_assigned",
        }

    def progress(self) -> dict[str, int]:
        """Count executable work separately from terminal blockers.

        A blocked task is not pending work: counting it as pending makes the
        coordinator try to resolve an already-resolved graph forever.
        """
        tasks = self.data.get("tasks", [])
        active_tasks = [
            task for task in tasks
            if not isinstance(task, dict) or task.get("status") != "superseded"
        ]
        total = len(active_tasks)
        done = sum(1 for t in active_tasks if t.get("status") == "done")
        failed = sum(1 for t in active_tasks if t.get("status") == "failed")
        blocked = sum(1 for t in active_tasks if t.get("status") == "blocked")
        pending = sum(
            1 for t in active_tasks if t.get("status") in {"pending", "running"}
        )
        return {
            "total": total,
            "done": done,
            "failed": failed,
            "blocked": blocked,
            "pending": pending,
        }

    def is_complete(self) -> bool:
        return self.progress()["done"] == self.progress()["total"]
