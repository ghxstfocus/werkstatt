"""Strangler-Fig Loop (M-262 Option C, 2026-10-23).

Phase 4: Reflection-Loop.
Wenn die Baseline nach dem Build rot ist, wird der
echte Fehlertext als Reflexion an den Builder zurueckgegeben.
Max 3 Runden, dann Circuit Breaker.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pipeline
from werkstatt.agent import ask_llm
from werkstatt.audit import audit
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
    """Holt den echten Fehlertext (pytest/ruff/mypy) fuer die Reflexion."""
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
    """Echter Reflection-Loop (Aider-Prinzip).
    
    Nimmt den Fehlertext, schickt ihn an den Builder,
    wendet den Korrektur-Patch an. Max 3 Runden.
    """
    pd = state.project_dir
    pn = state.project_name
    api_key = getattr(state, "api_key", "")
    
    if not api_key:
        audit("loop_repair_kein_key", {}, pd, pn)
        return False

    for runde in range(1, max_runden + 1):
        if _verify_patches(state):
            return True

        error_ctx = _get_baseline_error_details()
        audit("loop_reflection_runde", {"runde": runde}, pd, pn)

        # Aider-Prinzip: Echter Fehlertext als User-Nachricht
        reflection_prompt = (
            f"Dein letzter Patch hat die Baseline zerstoert.\n"
            f"Hier ist der echte Fehler-Output:\n\n{error_ctx}\n\n"
            "Bitte schreibe einen korrigierten Patch (git diff), "
            "der nur diesen Fehler behebt. Gib NUR den Patch aus."
        )

        # Builder (ask_llm) mit Reflexions-Prompt aufrufen
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
    """Echter Loop: Plan -> Build -> Verify -> Reflection -> Human."""
    state = phasen_state or (state_ref[-1] if state_ref else None)

    if state is None or getattr(state, "project_dir", None) is None:
        return pipeline.run_pipeline(
            project_name, aufgabe, state_ref, phasen_state=phasen_state
        )

    pd = state.project_dir
    pn = state.project_name

    # 1. Plan-Gate
    if not _plan_gate(state):
        audit("loop_gate_failed", {"gate": "plan"}, pd, pn)
        return 1

    # 2. Pre-Build Verify
    if not _verify_patches(state):
        audit("loop_gate_failed", {"gate": "pre_build"}, pd, pn)
        return 1

    # 3. Delegation an alten Motor
    audit("loop_aktiv", {"project_name": project_name, "aufgabe": aufgabe[:100]}, pd, pn)
    rc = pipeline.run_pipeline(
        project_name, aufgabe, state_ref, phasen_state=phasen_state
    )

    # 4. Post-Build Verify + Reflection-Loop (Aider-Prinzip)
    if not _verify_patches(state):
        audit("loop_gate_failed", {"gate": "post_build"}, pd, pn)
        if _reflection_loop(state):
            audit("loop_reflection_erfolg", {"project_name": project_name}, pd, pn)
        else:
            audit("loop_reflection_gescheitert", {"project_name": project_name}, pd, pn)
            return rc or 1

    audit("loop_erfolg", {"project_name": project_name}, pd, pn)
    return rc
