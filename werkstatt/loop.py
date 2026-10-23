"""Strangler-Fig Loop (M-262 Option C, 2026-10-23).

Phase 7a: Happy Path.
Planner -> Builder -> Verify -> Reflection -> Human.
Kein Aufruf des alten Monolithen (pipeline.run_pipeline)
im Hauptpfad mehr.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pipeline  # nur fuer Fallback / Human-Gate
from werkstatt.agent import ask_llm
from werkstatt.audit import audit
from werkstatt.builder import run_builder
from werkstatt.explorer import run_explorer
from werkstatt.planner import run_planner
from werkstatt.reviewer import run_reviewer
from werkstatt.state import RunState


def _plan_gate(state: RunState) -> bool:
    """B1: Plan-Gate (deterministisch)."""
    return all((
        getattr(state, 'tasks', []),
        getattr(state, 'tests', []),
        getattr(state, 'akzeptanzkriterien', [])
    ))


def _verify_patches(state: RunState) -> bool:
    """B2: Verifier (multi-projekt-faehig via Projekt-Contract).

    Liest .werkstatt/verify.json aus dem Zielprojekt.
    Fallback: pytest + ruff im Zielprojekt, wenn keine Config.
    """
    import json
    project_dir = getattr(state, "project_dir", None)
    if project_dir is None or not Path(project_dir).exists():
        return False

    project_dir = Path(project_dir)
    errors = []

    # 1. Projekt-Contract lesen
    contract_file = project_dir / ".werkstatt" / "verify.json"
    stages = []

    if contract_file.exists():
        try:
            with contract_file.open(encoding="utf-8") as fh:
                contract = json.load(fh)
            stages = contract.get("stages", [])
        except (json.JSONDecodeError, OSError):
            pass

    # 2. Fallback: Standard-Checks, wenn kein Contract
    if not stages:
        stages = [
            {"id": "pytest", "command": ["python3", "-m", "pytest", "-q"]},
            {"id": "ruff", "command": ["ruff", "check", "."]},
        ]

    # 3. Stages ausfuehren
    for stage in stages:
        cmd = stage.get("command")
        if not cmd:
            continue
        try:
            res = subprocess.run(
                cmd, cwd=str(project_dir),
                capture_output=True, text=True, timeout=300, check=False
            )
            if res.returncode != 0:
                errors.append(f"{stage.get('id', '?')}: {res.stdout[-500:]}")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{stage.get('id', '?')}-Fehler: {exc}")

    if errors:
        from werkstatt.audit import audit
        audit("loop_verify_failed", {"errors": errors}, project_dir, getattr(state, "project_name", "?"))
        return False

    return True

def _get_baseline_error_details() -> str:
    """Holt den echten Fehlertext fuer die Reflexion."""
    try:
        res = subprocess.run(
            ["python3", "/opt/werkstatt/tools/quality_gate.py", "--json"],
            cwd="/opt/werkstatt",
            capture_output=True, text=True, timeout=300, check=False
        )
        return res.stdout[:4000]
    except Exception:  # noqa: BLE001
        return "Baseline-Check fehlgeschlagen (Timeout/OSError)"


def _reflection_loop(state: RunState, max_runden: int = 3) -> bool:
    """Echter Reflection-Loop (Aider-Prinzip)."""
    pd = state.project_dir
    pn = state.project_name
    api_key = getattr(state, "api_key", "")
    
    if not api_key:
        audit("loop_reflection_kein_key", {}, pd, pn)
        return False

    for runde in range(1, max_runden + 1):
        if _verify_patches(state):
            return True

        error_ctx = _get_baseline_error_details()
        audit("loop_reflection_runde", {"runde": runde}, pd, pn)

        reflection_prompt = (
            f"Dein letzter Patch hat die Baseline zerstoert.\n"
            f"Hier ist der echte Fehler-Output:\n\n{error_ctx}\n\n"
            "Bitte schreibe einen korrigierten Patch (git diff), "
            "der nur diesen Fehler behebt. Gib NUR den Patch aus."
        )

        reply = ask_llm(
            api_key,
            "Du bist ein Repair-Agent. Behebe die Baseline-Fehler.",
            reflection_prompt,
            model="deepseek-chat",
            temperature=0.1,
        )

        if not reply.ok:
            audit("loop_reflection_llm_fehler", {"runde": runde, "fehler": reply.error}, pd, pn)
            continue

        patch_text = reply.content.strip()
        if patch_text and "diff --git" in patch_text:
            patch_datei = Path("/tmp/loop_reflection.patch")
            patch_datei.write_text(patch_text)
            apply_res = subprocess.run(
                ["git", "apply", str(patch_datei)],
                cwd="/opt/werkstatt", capture_output=True, text=True, check=False
            )
            if apply_res.returncode != 0:
                audit("loop_reflection_patch_fehler", {"runde": runde, "fehler": apply_res.stderr[:200]}, pd, pn)
        else:
            audit("loop_reflection_kein_patch", {"runde": runde}, pd, pn)

    return _verify_patches(state)




def _call_hook(hook_name: str, payload: dict) -> dict:
    """Ruft einen Hook auf und gibt das JSON-Ergebnis zurueck."""
    import json as _json
    hook_path = Path(f"/opt/werkstatt/hooks/{hook_name}")
    if not hook_path.exists():
        return {"allow": True, "reason": "Hook nicht gefunden (fail-open)"}
    try:
        res = subprocess.run(
            ["python3", str(hook_path)],
            input=_json.dumps(payload),
            cwd="/opt/werkstatt",
            capture_output=True, text=True, timeout=30, check=False,
        )
        if res.returncode != 0:
            return {"allow": False, "reason": f"Hook rc={res.returncode}"}
        return _json.loads(res.stdout)
    except Exception as exc:  # noqa: BLE001
        return {"allow": False, "reason": f"Hook-Fehler: {exc}"}




def _get_git_diff_for_hook() -> str:
    """Holt den aktuellen Git-Diff fuer Hooks."""
    try:
        res = subprocess.run(
            ["git", "diff", "HEAD"],
            cwd="/opt/werkstatt", capture_output=True, text=True, timeout=30, check=False
        )
        return res.stdout[:10000]
    except Exception:  # noqa: BLE001
        return ""



PROJECTS_DIR = Path("/opt/werkstatt/projects")


def load_project_config(project_name: str) -> dict:
    """Laedt die Projekt-Konfiguration aus /opt/werkstatt/projects/<name>.yaml.

    Liefert ein dict mit 'project_dir' (Pfad zum Zielprojekt).
    Fallback: /opt/<project_name>, wenn keine YAML existiert.
    """
    import yaml  # type: ignore[import-untyped]
    cfg_path = PROJECTS_DIR / f"{project_name}.yaml"
    if cfg_path.exists():
        try:
            with cfg_path.open(encoding="utf-8") as fh:
                cfg = yaml.safe_load(fh) or {}
            if "project_dir" in cfg:
                return cfg
        except (yaml.YAMLError, OSError):
            pass
    # Fallback: /opt/<project_name>
    fallback_dir = Path(f"/opt/{project_name}")
    if fallback_dir.exists():
        return {"project_dir": str(fallback_dir)}
    return {"project_dir": None}

def run_pipeline_loop(
    project_name: str,
    aufgabe: str,
    state_ref: list[RunState],
    *,
    phasen_state: RunState | None = None,
) -> int:
    """Echter Loop: Plan -> Planner -> Builder -> Verify -> Reflection -> Human."""
    state = phasen_state or (state_ref[-1] if state_ref else None)

    # Projekt-Pfad aus Config aufloesen, falls nicht gesetzt
    if state is not None and getattr(state, "project_dir", None) is None:
        cfg = load_project_config(project_name)
        if cfg.get("project_dir"):
            state.project_dir = Path(cfg["project_dir"])  # type: ignore[attr-defined]

    if state is None or getattr(state, "project_dir", None) is None:
        return pipeline.run_pipeline(
            project_name, aufgabe, state_ref, phasen_state=phasen_state
        )

    pd = state.project_dir
    pn = state.project_name

    # 0. Aufgabe in State setzen (fuer Planner)
    state.aufgabe = aufgabe  # type: ignore[attr-defined]

    # 0b. Explorer (Phase 14, read-only). Einmal pro Loop-Lauf.
    explorer_result = run_explorer(state, aufgabe)
    if explorer_result.get("key_files"):
        audit("loop_explorer_ok", {"files": len(explorer_result["key_files"])}, pd, pn)
        state.explorer_context = explorer_result  # type: ignore[attr-defined]
    else:
        audit("loop_explorer_leer", {}, pd, pn)

    # 1. Plan-Gate (leer -> Planner muss erst laufen)
    if not _plan_gate(state):
        audit("loop_plan_missing", {"aufgabe": aufgabe[:100]}, pd, pn)
        # 1a. Planner aufrufen
        if not run_planner(state):
            audit("loop_planner_failed", {}, pd, pn)
            return 1
        # 1b. Plan-Gate erneut pruefen
        if not _plan_gate(state):
            audit("loop_gate_failed", {"gate": "plan"}, pd, pn)
            return 1

    audit("loop_phase", {"phase": "plan", "status": "ok"}, pd, pn)

    # 2. Pre-Build Verify
    if not _verify_patches(state):
        audit("loop_gate_failed", {"gate": "pre_build"}, pd, pn)
        return 1

    # 3. Autonomer Task-Loop (Claude-Code-Prinzip)
    #    Alle Tasks werden abgearbeitet ohne Unterbrechung.
    #    Human-Gate kommt nur am Ende der Phase.
    tasks = getattr(state, "tasks", [])
    for i, task in enumerate(tasks, 1):
        task_name = task.get("name", f"Task {i}") if isinstance(task, dict) else str(task)
        audit("loop_task_start", {"task_id": i, "name": task_name}, pd, pn)

        # Builder fuer diesen Task
        state.aktuelle_task = task  # type: ignore[attr-defined]
        if not run_builder(state):
            audit("loop_builder_failed", {"task_id": i}, pd, pn)
            return 1

        # Patches anwenden (git apply)
        patches = getattr(state, "patches", [])
        for patch in patches:
            if not isinstance(patch, dict):
                continue
            file = patch.get("file", "")
            old_str = patch.get("old_string", "")
            new_str = patch.get("new_string", "")
            if not file or not old_str or not new_str:
                continue
            target = Path(pd) / file
            if not target.exists():
                audit("loop_patch_file_missing", {"file": file}, pd, pn)
                continue
            content = target.read_text()
            if old_str not in content:
                audit("loop_patch_old_string_not_found", {"file": file, "old": old_str[:50]}, pd, pn)
                continue
            content = content.replace(old_str, new_str, 1)
            target.write_text(content)
            audit("loop_patch_applied", {"file": file}, pd, pn)

        # PreToolUse-Hook (Phase 15, NEU): Patch pruefen, BEVOR er angewendet wird.
        patches = getattr(state, "patches", [])
        for patch in patches:
            patch_text = patch.get("new_string", "") if isinstance(patch, dict) else str(patch)
            hook_res = _call_hook("pre_tool_use.py", {"patch": patch_text})
            if not hook_res.get("allow", False):
                audit("loop_hook_blocked", {"hook": "pre_tool_use", "reason": hook_res.get("reason", "")}, pd, pn)
                # Reflection-Loop: Builder korrigiert den Patch
                if not _reflection_loop(state):
                    return 1
                # Nach Reflection: Patch neu pruefen (rekursiv? Nein, einfach weiter)
                break

        # PostToolUse-Hook (Phase 10)
        hook_res = _call_hook("post_tool_use.py", {})
        if not hook_res.get("allow", False):
            audit("loop_hook_blocked", {"hook": "post_tool_use", "reason": hook_res.get("reason", "")}, pd, pn)
            if not _reflection_loop(state):
                return 1

        # Simplify-Hook (Phase 11)
        hook_res = _call_hook("simplify.py", {"diff": _get_git_diff_for_hook()})
        if not hook_res.get("allow", False):
            audit("loop_hook_blocked", {"hook": "simplify", "reason": hook_res.get("reason", "")}, pd, pn)
            if not _reflection_loop(state):
                return 1

        # Post-Build Verify + Reflection (automatisch)
        if not _verify_patches(state):
            audit("loop_gate_failed", {"gate": "post_build", "task_id": i}, pd, pn)
            if not _reflection_loop(state):
                audit("loop_reflection_gescheitert", {"task_id": i}, pd, pn)
                return 1

        # Reviewer (Phase 9)
        if not run_reviewer(state):
            audit("loop_reviewer_rejected", {"task_id": i}, pd, pn)
            # Reflection-Loop versuchen (Builder korrigiert)
            if not _reflection_loop(state):
                audit("loop_reviewer_reflection_gescheitert", {"task_id": i}, pd, pn)
                return 1

        audit("loop_task_ok", {"task_id": i, "name": task_name}, pd, pn)

    # 4. Post-Build Verify + Reflection (nach allen Tasks)
    if not _verify_patches(state):
        audit("loop_gate_failed", {"gate": "post_build"}, pd, pn)
        if _reflection_loop(state):
            audit("loop_reflection_erfolg", {"project_name": project_name}, pd, pn)
        else:
            audit("loop_reflection_gescheitert", {"project_name": project_name}, pd, pn)
            return 1

    # 5. Human-Gate (isoliert aus dem alten Code)
    #    (approval_und_human_gate ist noch in pipeline.py, wir rufen es direkt)
    audit("loop_phase", {"phase": "human_gate", "status": "start"}, pd, pn)
    try:
        from werkstatt.config import Config
        config = Config(pipeline.load_project_config(project_name))
        rc = pipeline._approval_und_human_gate(
            state, pd, pn, config
        )
    except Exception:  # noqa: BLE001
        # Fallback: Delegation an Monolithen, falls Human-Gate nicht aufrufbar
        audit("loop_human_gate_fallback", {}, pd, pn)
        rc = pipeline.run_pipeline(
            project_name, aufgabe, state_ref, phasen_state=phasen_state
        )

    if rc == 0:
        audit("loop_erfolg", {"project_name": project_name}, pd, pn)
    return rc
