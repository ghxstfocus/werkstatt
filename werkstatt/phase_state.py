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


def phase_end_verify_evidence(
    results: object,
) -> tuple[str | None, list[str]]:
    """Return a stable digest and stages only for complete successful results."""
    if not isinstance(results, list) or not results:
        return None, []
    if any(
        not isinstance(item, dict)
        or item.get("ok") is not True
        or item.get("exit_code") != 0
        or not isinstance(item.get("stage_id"), str)
        or not item.get("stage_id")
        for item in results
    ):
        return None, []
    try:
        encoded = json.dumps(
            results,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError):
        return None, []
    return hashlib.sha256(encoded).hexdigest(), list(dict.fromkeys(
        str(item["stage_id"]) for item in results
    ))


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
        # Preserve fingerprints for active pre-Spec-First runs. Only plans
        # that actually bind an immutable test manifest include this field.
        spec_checkpoint = self.data.get("spec_test_checkpoint")
        if spec_checkpoint is not None:
            payload["spec_test_checkpoint"] = spec_checkpoint
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

    def record_preflight_checkpoint(
        self, *, goal: str, run_id: str, findings: list[dict[str, Any]],
    ) -> str:
        """Persist bounded preflight evidence for the current goal and run."""
        if (
            not isinstance(goal, str) or not goal
            or not isinstance(run_id, str) or not run_id
            or not isinstance(findings, list) or len(findings) > 500
            or any(not isinstance(item, dict) for item in findings)
        ):
            raise ValueError("Preflight-Checkpoint hat ungueltige Pflichtfelder")
        payload = {
            "schema_version": 1,
            "run_id": run_id,
            "project": self.project_name,
            "goal_sha256": hashlib.sha256(goal.encode("utf-8")).hexdigest(),
            "findings": findings,
        }
        try:
            encoded = json.dumps(
                payload, ensure_ascii=False, sort_keys=True,
                separators=(",", ":"), allow_nan=False,
            ).encode("utf-8")
        except (TypeError, ValueError, UnicodeEncodeError) as exc:
            raise ValueError("Preflight-Checkpoint ist nicht serialisierbar") from exc
        if len(encoded) > 200_000:
            raise ValueError("Preflight-Checkpoint ueberschreitet das Groessenlimit")
        digest = hashlib.sha256(encoded).hexdigest()
        goal_digest = payload["goal_sha256"]
        current_run_id = self.run_id or self.data.get("run_id")
        role_goal_digest = self.data.get("planner_role_goal_sha256")
        if (
            (current_run_id is not None and current_run_id != run_id)
            or (
                role_goal_digest is not None
                and role_goal_digest != goal_digest
            )
        ):
            self.data.pop("planner_role_stage", None)
            self.data.pop("planner_role_goal_sha256", None)
        self.data["preflight_checkpoint"] = {
            "schema_version": 1,
            "run_id": run_id,
            "project": self.project_name,
            "goal_sha256": goal_digest,
            "findings_sha256": digest,
            "payload_chars": len(encoded),
            "payload": payload,
        }
        self.run_id = run_id
        self.save()
        return digest

    def load_preflight_checkpoint(
        self, *, goal: str, run_id: str,
    ) -> list[dict[str, Any]] | None:
        """Return preflight findings only when identity and digest are current."""
        record = self.data.get("preflight_checkpoint")
        if (
            not isinstance(record, dict)
            or record.get("schema_version") != 1
            or record.get("run_id") != run_id
            or record.get("project") != self.project_name
            or record.get("goal_sha256") != hashlib.sha256(
                goal.encode("utf-8"),
            ).hexdigest()
        ):
            return None
        payload = record.get("payload")
        if not isinstance(payload, dict):
            return None
        try:
            encoded = json.dumps(
                payload, ensure_ascii=False, sort_keys=True,
                separators=(",", ":"), allow_nan=False,
            ).encode("utf-8")
        except (TypeError, ValueError, UnicodeEncodeError):
            return None
        findings = payload.get("findings")
        if (
            len(encoded) > 200_000
            or len(encoded) != record.get("payload_chars")
            or hashlib.sha256(encoded).hexdigest() != record.get("findings_sha256")
            or payload.get("schema_version") != 1
            or payload.get("run_id") != run_id
            or payload.get("project") != self.project_name
            or payload.get("goal_sha256") != record.get("goal_sha256")
            or not isinstance(findings, list)
            or len(findings) > 500
            or any(not isinstance(item, dict) for item in findings)
        ):
            return None
        return findings

    def record_plan_candidate(
        self,
        *,
        goal: str,
        run_id: str,
        tasks: list[dict[str, Any]],
        tests: list[Any],
        criteria: list[Any],
        phases: list[dict[str, Any]],
        architect_prose: str,
        preflight_findings: list[dict[str, Any]] | None = None,
        spec_test_checkpoint: dict[str, Any] | None = None,
    ) -> str:
        """Persist a bounded, run-bound plan proposal before human approval."""
        if (
            not isinstance(goal, str) or not goal
            or not isinstance(run_id, str) or not run_id
            or not isinstance(tasks, list) or not tasks
            or any(not isinstance(item, dict) for item in tasks)
            or not isinstance(tests, list)
            or not isinstance(criteria, list)
            or not isinstance(phases, list)
            or any(not isinstance(item, dict) for item in phases)
            or not isinstance(architect_prose, str)
            or (
                spec_test_checkpoint is not None
                and not isinstance(spec_test_checkpoint, dict)
            )
            or (
                preflight_findings is not None
                and (
                    not isinstance(preflight_findings, list)
                    or len(preflight_findings) > 500
                    or any(not isinstance(item, dict) for item in preflight_findings)
                )
            )
        ):
            raise ValueError("Plan-Kandidat hat ungueltige Pflichtfelder")
        payload: dict[str, Any] = {
            "schema_version": 1,
            "run_id": run_id,
            "project": self.project_name,
            "goal_sha256": hashlib.sha256(goal.encode("utf-8")).hexdigest(),
            "tasks": tasks,
            "tests": tests,
            "akzeptanzkriterien": criteria,
            "phasen": phases,
            "architect_prosa": architect_prose,
            "preflight_findings": preflight_findings or [],
            "spec_test_checkpoint": spec_test_checkpoint,
        }
        try:
            encoded = json.dumps(
                payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        except (TypeError, ValueError, UnicodeEncodeError) as exc:
            raise ValueError("Plan-Kandidat ist nicht serialisierbar") from exc
        if len(encoded) > 200_000:
            raise ValueError("Plan-Kandidat ueberschreitet das Groessenlimit")
        digest = hashlib.sha256(encoded).hexdigest()
        self.data["plan_candidate_checkpoint"] = {
            "schema_version": 1,
            "run_id": run_id,
            "project": self.project_name,
            "goal_sha256": payload["goal_sha256"],
            "candidate_sha256": digest,
            "payload": payload,
            "payload_chars": len(encoded),
        }
        self.save()
        return digest

    def load_plan_candidate(
        self, *, goal: str, run_id: str,
    ) -> dict[str, Any] | None:
        """Return a candidate only if its identity, size, and digest match."""
        record = self.data.get("plan_candidate_checkpoint")
        if (
            not isinstance(record, dict)
            or record.get("schema_version") != 1
            or record.get("run_id") != run_id
            or record.get("project") != self.project_name
            or record.get("goal_sha256") != hashlib.sha256(
                goal.encode("utf-8"),
            ).hexdigest()
        ):
            return None
        payload = record.get("payload")
        if not isinstance(payload, dict):
            return None
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
        digest = hashlib.sha256(encoded).hexdigest()
        if (
            len(encoded) > 200_000
            or len(encoded) != record.get("payload_chars")
            or digest != record.get("candidate_sha256")
            or payload.get("schema_version") != 1
            or payload.get("run_id") != run_id
            or payload.get("project") != self.project_name
            or payload.get("goal_sha256") != record.get("goal_sha256")
            or not isinstance(payload.get("tasks"), list)
            or not payload["tasks"]
            or any(not isinstance(item, dict) for item in payload["tasks"])
            or not isinstance(payload.get("tests"), list)
            or not isinstance(payload.get("akzeptanzkriterien"), list)
            or not isinstance(payload.get("phasen"), list)
            or any(not isinstance(item, dict) for item in payload["phasen"])
            or not isinstance(payload.get("architect_prosa"), str)
            or (
                payload.get("spec_test_checkpoint") is not None
                and not isinstance(payload.get("spec_test_checkpoint"), dict)
            )
            or not isinstance(payload.get("preflight_findings", []), list)
            or len(payload.get("preflight_findings", [])) > 500
            or any(
                not isinstance(item, dict)
                for item in payload.get("preflight_findings", [])
            )
        ):
            return None
        return payload

    def approve_plan_candidate(
        self, *, goal: str, run_id: str, candidate_sha256: str,
    ) -> bool:
        """Bind an explicit human approval to this exact current proposal."""
        payload = self.load_plan_candidate(goal=goal, run_id=run_id)
        record = self.data.get("plan_candidate_checkpoint")
        if (
            payload is None
            or not isinstance(record, dict)
            or record.get("candidate_sha256") != candidate_sha256
        ):
            return False
        record["approval_status"] = "approved"
        record["approved_candidate_sha256"] = candidate_sha256
        self.save()
        return True

    def plan_candidate_is_approved(
        self, *, goal: str, run_id: str,
    ) -> bool:
        """Return true only for a current proposal with a matching gate proof."""
        if self.load_plan_candidate(goal=goal, run_id=run_id) is None:
            return False
        record = self.data.get("plan_candidate_checkpoint")
        return bool(
            isinstance(record, dict)
            and record.get("approval_status") == "approved"
            and record.get("approved_candidate_sha256")
            == record.get("candidate_sha256")
        )

    def clear_plan_candidate(self) -> None:
        """Remove the unapproved proposal after approval or rejection."""
        if self.data.pop("plan_candidate_checkpoint", None) is not None:
            self.save()

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

    def record_human_gate(
        self, *, worktree_fingerprint: str, commit_requested: bool,
    ) -> None:
        """Persist an approval bound to the active run, plan, and worktree."""
        plan_fingerprint = self.approved_plan_fingerprint()
        if (
            not self.run_id
            or plan_fingerprint is None
            or not self.approved_plan_is_current()
            or len(worktree_fingerprint) != 64
            or any(char not in "0123456789abcdef" for char in worktree_fingerprint)
            or not isinstance(commit_requested, bool)
        ):
            raise ValueError("Human-Gate kann nicht sicher gebunden werden")
        self.data["human_gate_checkpoint"] = {
            "schema_version": 1,
            "run_id": self.run_id,
            "plan_sha256": plan_fingerprint,
            "worktree_sha256": worktree_fingerprint,
            "status": "approved",
            "commit_requested": commit_requested,
        }
        self.save()

    def human_gate_is_current(
        self, *, worktree_fingerprint: str | None,
    ) -> bool:
        """Check that approval still applies to this run and exact worktree."""
        gate = self.data.get("human_gate_checkpoint")
        plan_fingerprint = self.approved_plan_fingerprint()
        return bool(
            isinstance(gate, dict)
            and gate.get("schema_version") == 1
            and gate.get("status") == "approved"
            and gate.get("run_id") == self.run_id
            and gate.get("plan_sha256") == plan_fingerprint
            and gate.get("worktree_sha256") == worktree_fingerprint
            and isinstance(worktree_fingerprint, str)
            and isinstance(gate.get("commit_requested"), bool)
            and self.approved_plan_is_current()
        )

    def record_phase_end_verify(
        self,
        *,
        worktree_fingerprint: str,
        evidence_sha256: str,
        stage_ids: list[str],
    ) -> None:
        """Persist successful full-verify evidence for this approved tree."""
        plan_fingerprint = self.approved_plan_fingerprint()
        valid_hashes = (worktree_fingerprint, evidence_sha256)
        if (
            not self.run_id
            or plan_fingerprint is None
            or not self.approved_plan_is_current()
            or any(
                len(value) != 64
                or any(char not in "0123456789abcdef" for char in value)
                for value in valid_hashes
            )
            or not isinstance(stage_ids, list)
            or not stage_ids
            or any(not isinstance(stage_id, str) or not stage_id for stage_id in stage_ids)
        ):
            raise ValueError("Phase-End-Verify kann nicht sicher gebunden werden")
        self.data["phase_end_verify_checkpoint"] = {
            "schema_version": 1,
            "run_id": self.run_id,
            "plan_sha256": plan_fingerprint,
            "worktree_sha256": worktree_fingerprint,
            "evidence_sha256": evidence_sha256,
            "stage_ids": list(dict.fromkeys(stage_ids)),
            "status": "passed",
        }
        self.save()

    def phase_end_verify_is_current(
        self,
        *,
        worktree_fingerprint: str | None,
        evidence_sha256: str | None,
    ) -> bool:
        """Check successful verify evidence against the current plan and tree."""
        checkpoint = self.data.get("phase_end_verify_checkpoint")
        plan_fingerprint = self.approved_plan_fingerprint()
        stage_ids = checkpoint.get("stage_ids") if isinstance(checkpoint, dict) else None
        return bool(
            isinstance(checkpoint, dict)
            and checkpoint.get("schema_version") == 1
            and checkpoint.get("status") == "passed"
            and checkpoint.get("run_id") == self.run_id
            and checkpoint.get("plan_sha256") == plan_fingerprint
            and checkpoint.get("worktree_sha256") == worktree_fingerprint
            and checkpoint.get("evidence_sha256") == evidence_sha256
            and isinstance(worktree_fingerprint, str)
            and isinstance(evidence_sha256, str)
            and isinstance(stage_ids, list)
            and bool(stage_ids)
            and self.approved_plan_is_current()
        )

    def record_phase_end_verify_failure(
        self, failure_record: dict[str, Any], *, project_dir: Path,
    ) -> bool:
        """Persist bounded failure evidence for a coordinator recovery step."""
        from werkstatt.failure_record import _worktree_fingerprint

        plan_fingerprint = self.approved_plan_fingerprint()
        worktree_fingerprint = _worktree_fingerprint(project_dir)
        failed_stages = failure_record.get("failed_stages")
        artifact_ref = failure_record.get("artifact_ref")
        failure_id = failure_record.get("failure_id")
        work_sha = failure_record.get("work_sha")
        recorded_fingerprint = failure_record.get("worktree_fingerprint")
        if (
            not self.run_id
            or plan_fingerprint is None
            or not self.approved_plan_is_current()
            or not isinstance(worktree_fingerprint, str)
            or not isinstance(artifact_ref, str)
            or not artifact_ref
            or not isinstance(failure_id, str)
            or not isinstance(work_sha, str)
            or len(work_sha) not in {40, 64}
            or any(char not in "0123456789abcdef" for char in work_sha)
            or recorded_fingerprint != worktree_fingerprint
            or not isinstance(failed_stages, list)
            or not failed_stages
            or any(not isinstance(item, dict) for item in failed_stages)
        ):
            return False
        previous = self.data.get("phase_end_verify_failure_checkpoint")
        attempted = (
            previous.get("attempted_worktree_sha256", [])
            if isinstance(previous, dict) else []
        )
        attempted = [
            value for value in attempted
            if isinstance(value, str) and len(value) == 64
        ][:20]
        if worktree_fingerprint in attempted:
            return False
        self.data["phase_end_verify_failure_checkpoint"] = {
            "schema_version": 1,
            "run_id": self.run_id,
            "plan_sha256": plan_fingerprint,
            "worktree_sha256": worktree_fingerprint,
            "failure_id": failure_id[:64],
            "artifact_ref": artifact_ref[:500],
            "failed_stages": [
                {
                    "stage_id": str(item.get("stage_id") or "?")[:120],
                    "exit_code": item.get("exit_code"),
                    "error_excerpt": str(item.get("error_excerpt") or "")[:1200],
                }
                for item in failed_stages[:12]
            ],
            "attempted_worktree_sha256": attempted,
            "status": "pending",
        }
        self.save()
        return True

    def phase_end_verify_failure_is_current(
        self, *, project_dir: Path,
    ) -> bool:
        """Validate a pending final-verify failure against the current tree."""
        from werkstatt.failure_record import _worktree_fingerprint

        checkpoint = self.data.get("phase_end_verify_failure_checkpoint")
        plan_fingerprint = self.approved_plan_fingerprint()
        current_fingerprint = _worktree_fingerprint(project_dir)
        return bool(
            isinstance(checkpoint, dict)
            and checkpoint.get("schema_version") == 1
            and checkpoint.get("status") == "pending"
            and checkpoint.get("run_id") == self.run_id
            and checkpoint.get("plan_sha256") == plan_fingerprint
            and checkpoint.get("worktree_sha256") == current_fingerprint
            and isinstance(current_fingerprint, str)
            and isinstance(checkpoint.get("artifact_ref"), str)
            and isinstance(checkpoint.get("failed_stages"), list)
            and checkpoint.get("failed_stages")
            and self.approved_plan_is_current()
        )

    def claim_phase_end_verify_recovery(
        self, *, project_dir: Path,
    ) -> dict[str, Any] | None:
        """Claim one recovery action for the exact pending failure checkpoint."""
        if not self.phase_end_verify_failure_is_current(
            project_dir=project_dir,
        ):
            return None
        checkpoint = self.data.get("phase_end_verify_failure_checkpoint")
        if not isinstance(checkpoint, dict):
            return None
        attempted = checkpoint.get("attempted_worktree_sha256")
        attempted = attempted if isinstance(attempted, list) else []
        fingerprint = checkpoint.get("worktree_sha256")
        if not isinstance(fingerprint, str) or fingerprint in attempted:
            return None
        checkpoint["attempted_worktree_sha256"] = [
            *attempted[-19:], fingerprint,
        ]
        checkpoint["status"] = "attempted"
        self.save()
        return dict(checkpoint)

    def record_commit_checkpoint(
        self, *, commit_sha: str, verify_evidence_sha256: str,
        post_commit_evidence_sha256: str,
    ) -> None:
        """Bind an approved commit to the run's successful full verification."""
        plan_fingerprint = self.approved_plan_fingerprint()
        gate = self.data.get("human_gate_checkpoint")
        verify = self.data.get("phase_end_verify_checkpoint")
        if (
            not self.run_id
            or plan_fingerprint is None
            or not self.approved_plan_is_current()
            or not isinstance(gate, dict)
            or gate.get("run_id") != self.run_id
            or gate.get("plan_sha256") != plan_fingerprint
            or gate.get("status") != "approved"
            or gate.get("commit_requested") is not True
            or not isinstance(verify, dict)
            or verify.get("run_id") != self.run_id
            or verify.get("plan_sha256") != plan_fingerprint
            or verify.get("status") != "passed"
            or verify.get("evidence_sha256") != verify_evidence_sha256
            or not isinstance(commit_sha, str)
            or len(commit_sha) not in {40, 64}
            or any(char not in "0123456789abcdef" for char in commit_sha)
            or not isinstance(verify_evidence_sha256, str)
            or len(verify_evidence_sha256) != 64
            or any(char not in "0123456789abcdef" for char in verify_evidence_sha256)
            or not isinstance(post_commit_evidence_sha256, str)
            or len(post_commit_evidence_sha256) != 64
            or any(char not in "0123456789abcdef" for char in post_commit_evidence_sha256)
        ):
            raise ValueError("Commit kann nicht sicher an Verify gebunden werden")
        self.data["commit_checkpoint"] = {
            "schema_version": 1,
            "run_id": self.run_id,
            "plan_sha256": plan_fingerprint,
            "verify_evidence_sha256": verify_evidence_sha256,
            "post_commit_evidence_sha256": post_commit_evidence_sha256,
            "commit_sha": commit_sha,
            "status": "committed",
        }
        pending = self.data.get("commit_pending_post_verify_checkpoint")
        if (
            isinstance(pending, dict)
            and pending.get("commit_sha") == commit_sha
            and pending.get("verify_evidence_sha256") == verify_evidence_sha256
        ):
            pending["status"] = "post_commit_verify_passed"
        self.save()

    def record_commit_pending_post_verify(
        self, *, commit_sha: str, verify_evidence_sha256: str,
    ) -> None:
        """Persist the commit boundary before selecting post-commit Verify."""
        plan_fingerprint = self.approved_plan_fingerprint()
        gate = self.data.get("human_gate_checkpoint")
        verify = self.data.get("phase_end_verify_checkpoint")
        if (
            not self.run_id
            or plan_fingerprint is None
            or not self.approved_plan_is_current()
            or not isinstance(gate, dict)
            or gate.get("run_id") != self.run_id
            or gate.get("plan_sha256") != plan_fingerprint
            or gate.get("status") != "approved"
            or gate.get("commit_requested") is not True
            or not isinstance(verify, dict)
            or verify.get("status") != "passed"
            or verify.get("evidence_sha256") != verify_evidence_sha256
            or not isinstance(commit_sha, str)
            or len(commit_sha) not in {40, 64}
            or any(char not in "0123456789abcdef" for char in commit_sha)
            or not isinstance(verify_evidence_sha256, str)
            or len(verify_evidence_sha256) != 64
            or any(char not in "0123456789abcdef" for char in verify_evidence_sha256)
        ):
            raise ValueError("Commit-Pending kann nicht sicher gebunden werden")
        self.data["commit_pending_post_verify_checkpoint"] = {
            "schema_version": 1,
            "run_id": self.run_id,
            "plan_sha256": plan_fingerprint,
            "commit_sha": commit_sha,
            "verify_evidence_sha256": verify_evidence_sha256,
            "status": "pending_post_commit_verify",
        }
        self.save()

    def commit_pending_post_verify_is_current(
        self, *, commit_sha: str | None,
    ) -> bool:
        """Check whether the exact new HEAD still awaits post-commit Verify."""
        checkpoint = self.data.get("commit_pending_post_verify_checkpoint")
        plan_fingerprint = self.approved_plan_fingerprint()
        gate = self.data.get("human_gate_checkpoint")
        verify = self.data.get("phase_end_verify_checkpoint")
        return bool(
            isinstance(checkpoint, dict)
            and checkpoint.get("schema_version") == 1
            and checkpoint.get("status") == "pending_post_commit_verify"
            and checkpoint.get("run_id") == self.run_id
            and checkpoint.get("plan_sha256") == plan_fingerprint
            and checkpoint.get("commit_sha") == commit_sha
            and isinstance(commit_sha, str)
            and isinstance(verify, dict)
            and verify.get("status") == "passed"
            and checkpoint.get("verify_evidence_sha256")
            == verify.get("evidence_sha256")
            and isinstance(gate, dict)
            and gate.get("status") == "approved"
            and gate.get("commit_requested") is True
            and self.approved_plan_is_current()
        )

    def commit_checkpoint_is_current(
        self, *, commit_sha: str | None,
    ) -> bool:
        """Check commit evidence against current run, plan, gate, and HEAD."""
        checkpoint = self.data.get("commit_checkpoint")
        plan_fingerprint = self.approved_plan_fingerprint()
        gate = self.data.get("human_gate_checkpoint")
        verify = self.data.get("phase_end_verify_checkpoint")
        return bool(
            isinstance(checkpoint, dict)
            and checkpoint.get("schema_version") == 1
            and checkpoint.get("status") == "committed"
            and checkpoint.get("run_id") == self.run_id
            and checkpoint.get("plan_sha256") == plan_fingerprint
            and checkpoint.get("commit_sha") == commit_sha
            and isinstance(checkpoint.get("verify_evidence_sha256"), str)
            and isinstance(checkpoint.get("post_commit_evidence_sha256"), str)
            and len(checkpoint["post_commit_evidence_sha256"]) == 64
            and isinstance(gate, dict)
            and gate.get("run_id") == self.run_id
            and gate.get("plan_sha256") == plan_fingerprint
            and gate.get("status") == "approved"
            and gate.get("commit_requested") is True
            and isinstance(verify, dict)
            and verify.get("run_id") == self.run_id
            and verify.get("plan_sha256") == plan_fingerprint
            and verify.get("status") == "passed"
            and checkpoint.get("verify_evidence_sha256") == verify.get("evidence_sha256")
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
        self.data.pop("human_gate_checkpoint", None)
        self.data.pop("phase_end_verify_checkpoint", None)
        self.data.pop("phase_end_verify_pending_run_id", None)
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
            failure_checkpoint = (
                task.get("verify_failure_checkpoint")
                if isinstance(task, dict) else None
            )
            if (
                isinstance(task, dict)
                and isinstance(failure_checkpoint, dict)
                and failure_checkpoint.get("status") == "pending"
                and task.get("status") == "running"
            ):
                recovery_task = dict(task)
                recovery_task["verify_recovery_only"] = True
                recovery_task["verify_recovery_checkpoint_current"] = (
                    self.task_verify_failure_checkpoint_is_current(
                        str(task.get("id", "")),
                    )
                )
                return recovery_task
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

    def record_task_review_checkpoint(
        self,
        task_id: str,
        *,
        verify_warnings: object = None,
    ) -> bool:
        """Persist a bounded review handoff bound to current Verify evidence."""
        task = self.get_task(task_id)
        evidence = task.get("verify_evidence") if isinstance(task, dict) else None
        if (
            not isinstance(task, dict)
            or task.get("status") != "running"
            or not self.task_verify_evidence_is_current(task_id, evidence)
        ):
            return False
        warnings = [
            str(item).replace("\x00", "")[:240]
            for item in verify_warnings[:12]
            if isinstance(item, str) and item.strip()
        ] if isinstance(verify_warnings, list) else []
        while warnings and len(json.dumps(
            warnings, ensure_ascii=False,
        )) > 2_400:
            warnings.pop()
        encoded_evidence = json.dumps(
            evidence, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        )
        task["review_checkpoint"] = {
            "schema_version": 1,
            "task_id": task_id,
            "run_id": self.run_id,
            "verify_evidence_sha256": hashlib.sha256(
                encoded_evidence.encode("utf-8"),
            ).hexdigest(),
            "verify_warnings": warnings,
            "status": "pending",
            "created_at": datetime.datetime.now(datetime.UTC).isoformat(),
        }
        self.data["updated"] = datetime.datetime.now(datetime.UTC).isoformat()
        self.save()
        return True

    def record_task_build_checkpoint(self, task_id: str) -> bool:
        """Persist the post-Builder file hashes before Verify is dispatched."""
        task = self.get_task(task_id)
        task_files = task.get("task_files") if isinstance(task, dict) else None
        hashes = self._task_file_hashes(task_files)
        if (
            not isinstance(task, dict)
            or task.get("status") != "running"
            or hashes is None
        ):
            return False
        task["build_checkpoint"] = {
            "schema_version": 1,
            "task_id": task_id,
            "run_id": self.run_id,
            "task_file_sha256": hashes,
            "created_at": datetime.datetime.now(datetime.UTC).isoformat(),
        }
        task["verification_pending"] = True
        self.data["updated"] = datetime.datetime.now(datetime.UTC).isoformat()
        self.save()
        return True

    def task_build_checkpoint_is_current(self, task_id: str) -> bool:
        """Check a Builder handoff against current task-scope file bytes."""
        task = self.get_task(task_id)
        checkpoint = task.get("build_checkpoint") if isinstance(task, dict) else None
        if (
            not isinstance(task, dict)
            or not isinstance(checkpoint, dict)
            or checkpoint.get("schema_version") != 1
            or checkpoint.get("task_id") != task_id
            or checkpoint.get("run_id") != self.run_id
            or task.get("status") != "running"
        ):
            return False
        current_hashes = self._task_file_hashes(task.get("task_files"))
        return (
            current_hashes is not None
            and checkpoint.get("task_file_sha256") == current_hashes
        )

    def record_task_verify_failure_checkpoint(
        self, task_id: str, errors: object, *, phase: str = "post_build",
    ) -> bool:
        """Persist bounded Verify failure evidence for one coordinator recovery."""
        task = self.get_task(task_id)
        if (
            not isinstance(task, dict)
            or task.get("status") != "running"
            or phase != "post_build"
            or not self.task_build_checkpoint_is_current(task_id)
        ):
            return False
        hashes = self._task_file_hashes(task.get("task_files"))
        if hashes is None:
            return False
        clean_errors = [
            str(item).replace("\x00", "")[:240]
            for item in errors[:8]
            if isinstance(item, str) and item.strip()
        ] if isinstance(errors, list) else []
        if not clean_errors:
            clean_errors = ["verify_failed: no structured stage detail"]
        payload = {
            "schema_version": 1,
            "task_id": task_id,
            "run_id": self.run_id,
            "phase": phase,
            "task_file_sha256": hashes,
            "verify_errors": clean_errors,
        }
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        if len(encoded) > 4_000:
            return False
        task["verify_failure_checkpoint"] = {
            **payload,
            "evidence_sha256": hashlib.sha256(encoded.encode("utf-8")).hexdigest(),
            "status": "pending",
            "created_at": datetime.datetime.now(datetime.UTC).isoformat(),
        }
        task["verification_pending"] = False
        self.data["updated"] = datetime.datetime.now(datetime.UTC).isoformat()
        self.save()
        return True

    def task_verify_failure_checkpoint_is_current(self, task_id: str) -> bool:
        """Validate Verify failure proof against the same task/run and file bytes."""
        task = self.get_task(task_id)
        checkpoint = task.get("verify_failure_checkpoint") if isinstance(task, dict) else None
        if (
            not isinstance(task, dict)
            or not isinstance(checkpoint, dict)
            or checkpoint.get("schema_version") != 1
            or checkpoint.get("task_id") != task_id
            or checkpoint.get("run_id") != self.run_id
            or checkpoint.get("phase") != "post_build"
            or checkpoint.get("status") != "pending"
            or task.get("status") != "running"
            or not isinstance(checkpoint.get("verify_errors"), list)
            or len(checkpoint.get("verify_errors", [])) > 8
            or not all(
                isinstance(error, str) and len(error) <= 240
                for error in checkpoint.get("verify_errors", [])
            )
            or not isinstance(checkpoint.get("task_file_sha256"), dict)
        ):
            return False
        payload = {
            key: checkpoint.get(key)
            for key in (
                "schema_version", "task_id", "run_id", "phase",
                "task_file_sha256", "verify_errors",
            )
        }
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return (
            checkpoint.get("evidence_sha256")
            == hashlib.sha256(encoded.encode("utf-8")).hexdigest()
            and checkpoint.get("task_file_sha256")
            == self._task_file_hashes(task.get("task_files"))
        )

    def task_review_checkpoint_is_current(self, task_id: str) -> bool:
        """Validate a pending review handoff against current source and verify proof."""
        task = self.get_task(task_id)
        checkpoint = task.get("review_checkpoint") if isinstance(task, dict) else None
        evidence = task.get("verify_evidence") if isinstance(task, dict) else None
        if (
            not isinstance(task, dict)
            or not isinstance(checkpoint, dict)
            or checkpoint.get("schema_version") != 1
            or checkpoint.get("task_id") != task_id
            or checkpoint.get("run_id") != self.run_id
            or checkpoint.get("status") != "pending"
            or not self.task_verify_evidence_is_current(task_id, evidence)
        ):
            return False
        encoded_evidence = json.dumps(
            evidence, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        )
        return checkpoint.get("verify_evidence_sha256") == hashlib.sha256(
            encoded_evidence.encode("utf-8"),
        ).hexdigest()

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
        if status != "running":
            task.pop("build_checkpoint", None)
            task.pop("verification_pending", None)
            task.pop("verify_failure_checkpoint", None)
            if status != "done":
                task.pop("review_checkpoint", None)
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
            _t.pop("review_checkpoint", None)
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
