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

import yaml  # type: ignore[import-untyped]

PHASE_DIR = Path("/opt/werkstatt/projects")


class PhaseState:
    """Verwaltet den Phase-State eines Projekts (YAML)."""

    def __init__(self, project_name: str, base_dir: Path | None = None):
        self.project_name = project_name
        self.base_dir = base_dir or PHASE_DIR
        self.path = self.base_dir / f"{project_name}.phase.yaml"
        self.data: dict[str, Any] = {}

    # --- Laden / Speichern ---

    def exists(self) -> bool:
        return self.path.exists()

    def load(self) -> bool:
        """Lädt den State aus YAML. Gibt False zurück, wenn nicht vorhanden."""
        if not self.path.exists():
            return False
        try:
            with self.path.open(encoding="utf-8") as fh:
                self.data = yaml.safe_load(fh) or {}
            return True
        except (yaml.YAMLError, OSError):
            return False

    def save(self) -> None:
        """Speichert den State atomar (temp + rename)."""
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
        now = datetime.datetime.now(datetime.UTC).isoformat()
        self.data = {
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
                    "status": "pending",
                    "decision": None,
                    "failure": None,
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
        """
        for task in self.data.get("tasks", []):
            if task.get("status") in ("pending", "running"):
                return task
        return None

    def resume_failed(self) -> int:
        """M-310c: Setzt failed-Tasks auf pending (Resume nach Abbruch).

        Returns: Anzahl reaktivierter Tasks.
        """
        n = 0
        for task in self.data.get("tasks", []):
            # K1: failed UND running zuruecksetzen. running-Tasks
            # sind Reste eines abgebrochenen Laufs.
            if task.get("status") in ("failed", "running"):
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

    def mark_done(self, task_id: str, *, decision: str | None = None) -> None:
        self.update_task(task_id, "done", decision=decision)

    def mark_failed(self, task_id: str, *, failure: str) -> None:
        self.update_task(task_id, "failed", failure=failure)

    def mark_running(self, task_id: str) -> None:
        self.update_task(task_id, "running")

    # --- Fortschritt ---

    def split_task(
        self, task_id: str, sub_tasks: list[dict],
    ) -> None:
        """M-472: Ersetzt eine Task durch Sub-Tasks (ADaPT).

        Die Original-Task wird 'split'. Die Sub-Tasks werden an
        ihrer Position eingefuegt und sind 'pending'.
        """
        tasks = self.data.get("tasks", [])
        # Position der Original-Task finden.
        idx = -1
        for i, t in enumerate(tasks):
            if t.get("id") == task_id:
                idx = i
                break
        if idx < 0:
            return
        # Original-Task: status=split.
        tasks[idx]["status"] = "split"
        # Sub-Tasks: status=pending, eingefuegt nach idx.
        for j, st in enumerate(sub_tasks):
            st["status"] = "pending"
            st["split_tiefe"] = tasks[idx].get("split_tiefe", 0) + 1
            tasks.insert(idx + 1 + j, st)
        self.data["tasks"] = tasks
        self.data["updated"] = __import__("datetime").datetime.now(
            __import__("datetime").UTC
        ).isoformat()
        self.save()

    def progress(self) -> dict[str, int]:
        """Gibt den Fortschritt zurueck (done/total)."""
        tasks = self.data.get("tasks", [])
        total = len(tasks)
        done = sum(1 for t in tasks if t.get("status") == "done")
        failed = sum(1 for t in tasks if t.get("status") == "failed")
        return {"total": total, "done": done, "failed": failed, "pending": total - done - failed}

    def is_complete(self) -> bool:
        return self.progress()["done"] == self.progress()["total"]
