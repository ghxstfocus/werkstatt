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
from werkstatt.planner import run_planner
from werkstatt.state import RunState


def _plan_gate(state: RunState) -> bool:
    """B1: Plan-Gate (deterministisch)."""
    return all((
        getattr(state, 'tasks', []),
        getattr(state, 'tests', []),
        getattr(state, 'akzeptanzkriterien', [])
    ))


def _verify_patches(state: RunState) -> bool:
    """B2: Verifier (deterministisch). Ruft quality_gate.py auf."""
    qg_path = Path("/opt/werkstatt/tools/quality_gate.py")
    if not qg_path.exists():
        return False
    try:
        res = subprocess.run(
            ["python3", str(qg_path), "--json"],
            cwd="/opt/werkstatt",
            capture_output=True, text=True, timeout=300, check=False
        )
        return res.returncode == 0 and (
            '"ok": true' in res.stdout or '"ok":true' in res.stdout
        )
    except Exception:  # noqa: BLE001
        return False


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


def run_pipeline_loop(
    project_name: str,
    aufgabe: str,
    state_ref: list[RunState],
    *,
    phasen_state: RunState | None = None,
) -> int:
    """Echter Loop: Plan -> Planner -> Builder -> Verify -> Reflection -> Human."""
    state = phasen_state or (state_ref[-1] if state_ref else None)

    if state is None or getattr(state, "project_dir", None) is None:
        return pipeline.run_pipeline(
            project_name, aufgabe, state_ref, phasen_state=phasen_state
        )

    pd = state.project_dir
    pn = state.project_name

    # 0. Aufgabe in State setzen (fuer Planner)
    state.aufgabe = aufgabe  # type: ignore[attr-defined]

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

    # 3. Builder (neuer Agent)
    audit("loop_phase", {"phase": "build", "status": "start"}, pd, pn)
    if not run_builder(state):
        audit("loop_builder_failed", {}, pd, pn)
        return 1
    audit("loop_phase", {"phase": "build", "status": "ok"}, pd, pn)

    # 4. Post-Build Verify + Reflection
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
