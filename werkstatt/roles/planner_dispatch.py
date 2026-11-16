"""Evidence-driven role selection for the Planner checkpoint workflow.

The dispatcher owns the *need* decision; role workers own their specialized
work. It never authorizes code changes or bypasses plan/human gates.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PlannerRoleDecision:
    """One auditable next action derived from the current planning evidence."""

    role: str | None
    reason: str


def scout_route_decision(
    task: str, explorer_context: object, project_dir,
) -> tuple[str | None, str]:
    """Skip Scout only for a current, explicit, low-scope source target."""
    text = str(task or "").strip()
    if not text:
        return None, "auftrag_leer"
    if project_dir is None or not isinstance(explorer_context, dict):
        return None, "explorer_beleg_fehlt"
    paths = set(re.findall(
        r"(?<![\w.-])(?:[\w.-]+/)*[\w.-]+\.(?:py|md)", text,
    ))
    if not paths:
        return None, "kein_expliziter_zieldateipfad"
    if len(paths) != 1:
        return None, "mehrere_explizite_zieldateien"
    target = next(iter(paths))
    target_path = Path(target)
    if target_path.is_absolute() or ".." in target_path.parts:
        return None, "zieldateipfad_unsicher"
    if target.startswith("tests/"):
        return None, "testdatei_braucht_scout"

    intent_text = text
    for explicit_path in sorted(paths, key=len, reverse=True):
        intent_text = re.sub(
            re.escape(explicit_path), " ", intent_text, flags=re.IGNORECASE,
        )
    lowered = intent_text.casefold()
    broad_markers = (
        ("alle", r"\balle\b"), ("all", r"\ball\b"),
        ("gesamt", r"\bgesamt\w*\b"), ("mehrere", r"\bmehrere\b"),
        ("multiple", r"\bmultiple\b"),
        ("umfassend", r"\bumfassend\w*\b"),
        ("architektur", r"\barchitektur\w*\b"),
        ("architecture", r"\barchitecture\w*\b"),
        ("schnittstelle", r"\bschnittstell\w*\b"),
        ("interface", r"\binterface\w*\b"), ("api", r"\bapi\b"),
        ("debug", r"\bdebug\w*\b"), ("fehler", r"\bfehler\w*\b"),
        ("error", r"\berror\w*\b"), ("bug", r"\bbug\b"),
        ("ursache", r"\bursach\w*\b"), ("cause", r"\bcause\b"),
        ("analys", r"\banalys\w*\b"),
        ("analyze", r"\banaly[sz]\w*\b"),
        ("inspect", r"\binspect\w*\b"),
        ("pruef", r"\bpr[uü]f\w*\b"),
        ("check", r"\bcheck(?:s|e|ed|ing)?\b"),
        ("review", r"\breview\w*\b"),
        ("refactor", r"\brefactor\w*\b"),
        ("aufraeum", r"\b(?:aufräum|aufraeum)\w*\b"),
        ("migrier", r"\bmigrier\w*\b"),
        ("migrate", r"\bmigrat\w*\b"),
        ("blockiert", r"\bblockier\w*\b"),
        ("blocked", r"\bblocked\b"),
        ("abhaengig", r"\b(?:abhängig|abhaengig)\w*\b"),
        ("dependent", r"\bdependen\w*\b"),
    )
    marker = next((
        label for label, pattern in broad_markers
        if re.search(pattern, lowered)
    ), None)
    if marker:
        return None, f"auftrag_enthaelt_breiten_marker:{marker}"
    edit_markers = (
        r"\b(?:setz|set|änder|aender|korrigier|ergänz|ergaenz|aktualisier|"
        r"entfern|ersetz|füg|fueg|update|change|edit|fix|add|remove|replace)"
        r"\w*\b"
    )
    if not re.search(edit_markers, lowered):
        return None, "aenderungsabsicht_nicht_eindeutig"
    explorer_files = explorer_context.get("key_files") or []
    confirmed = {
        item.get("file") for item in explorer_files
        if isinstance(item, dict) and isinstance(item.get("file"), str)
    }
    if target not in confirmed:
        return None, "explorer_bestaetigt_zieldatei_nicht"
    try:
        project_root = Path(project_dir).resolve(strict=True)
        resolved_target = (project_root / target_path).resolve(strict=True)
        resolved_target.relative_to(project_root)
        if not resolved_target.is_file():
            return None, "zieldatei_nicht_vorhanden"
        if resolved_target.stat().st_size > 24_000:
            return None, "zieldatei_uebersteigt_vollstaendigen_architect_auszug"
        source_text = resolved_target.read_text(encoding="utf-8")
    except (OSError, RuntimeError, UnicodeDecodeError, ValueError):
        return None, "zieldatei_nicht_sicher_lesbar"
    if len(source_text) > 6_000:
        return None, "zieldatei_uebersteigt_vollstaendigen_architect_auszug"
    return target, "explizite_einzeldatei_mit_explorer_beleg"


def architect_reasoning_route(
    task: str, scout_skip_path: str | None,
) -> tuple[bool, str]:
    """Use high reasoning for uncertain or complex design work.

    Scout routing and Architect effort are separate decisions: an explicit
    single-file target may make Scout unnecessary while the design still
    warrants deeper reasoning.
    """
    if scout_skip_path is None:
        return True, "scout_oder_breitere_belegsuche_erforderlich"

    text = str(task or "").casefold()
    markers = (
        ("sicherheit", r"\b(?:sicher\w*|security|auth\w*|berechtig\w*|permission\w*|credential\w*|secret\w*|krypt\w*)\b"),
        ("parallelitaet", r"\b(?:parallel\w*|concurren\w*|async\w*|thread\w*|race\w*|lock\w*|lease\w*|nebenlaeufig\w*|nebenläufig\w*)\b"),
        ("kompatibilitaet", r"\b(?:kompatib\w*|compatib\w*|rueckwaerts\w*|rückwärts\w*|backward\w*|migration\w*|schema\w*|transaktion\w*|transaction\w*)\b"),
        ("performance", r"\b(?:performance|performanz|latenz\w*|throughput|skalier\w*|scalab\w*|cache\w*)\b"),
        ("bedingungen_oder_invarianten", r"\b(?:solange|sofern|falls|unless|while|without|beibehalten|erhalten|invariant\w*|rueckfall\w*|rückfall\w*)\b"),
    )
    for label, pattern in markers:
        if re.search(pattern, text):
            return True, f"komplexitaetsmarker:{label}"

    action_pattern = (
        r"\b(?:aender\w*|änder\w*|korrigier\w*|ergänz\w*|ergaenz\w*|"
        r"aktualisier\w*|entfern\w*|ersetz\w*|füg\w*|fueg\w*|prüf\w*|"
        r"pruef\w*|verifizier\w*|test\w*|implementier\w*|update\w*|"
        r"change\w*|fix\w*|add\w*|remove\w*|replace\w*|check\w*|"
        r"verify\w*|implement\w*)\b"
    )
    if len(re.findall(action_pattern, text)) > 1:
        return True, "mehrere_aktionsschritte"
    if len(text) > 360:
        return True, "umfangreicher_einzeldateiauftrag"
    return False, "explorer_belegte_routine_einzeldatei"


def choose_next_planner_role(
    *,
    scout_skip_path: str | None,
    completed_role: str | None = None,
    scout_already_fulfilled: bool = False,
    deterministic_task_graph_ready: bool = False,
    architect_output_ready: bool = False,
    task_graph_ready: bool = False,
) -> PlannerRoleDecision:
    """Choose only the next missing Planner capability.

    ``scout_skip_path`` is supplied only after the current Explorer evidence
    and source path have passed the Scout-skip validator. The deterministic
    completion flags are supplied only after their corresponding evidence or
    compiled task graph has passed validation.
    """
    if task_graph_ready:
        return PlannerRoleDecision(None, "validated_task_graph_ready")
    if scout_already_fulfilled:
        return PlannerRoleDecision(None, "scout_reports_goal_already_fulfilled")
    if deterministic_task_graph_ready:
        return PlannerRoleDecision(None, "validated_deterministic_task_graph_ready")

    if completed_role is None:
        if scout_skip_path:
            return PlannerRoleDecision(
                "architect", "scout_skipped_current_explorer_source_evidence",
            )
        return PlannerRoleDecision("scout", "scout_evidence_missing")

    if completed_role == "scout":
        if not scout_skip_path and not architect_output_ready:
            return PlannerRoleDecision(
                "architect", "scout_report_needs_design_decision",
            )
        if architect_output_ready:
            return PlannerRoleDecision(
                "planner_split", "architect_output_needs_task_graph_compilation",
            )
        return PlannerRoleDecision(
            "architect", "scout_skipped_but_architect_output_missing",
        )

    if completed_role == "architect":
        if architect_output_ready:
            return PlannerRoleDecision(
                "planner_split", "architect_output_needs_task_graph_compilation",
            )
        return PlannerRoleDecision(
            "architect", "architect_output_missing_recover_role",
        )

    if completed_role == "planner_split":
        return PlannerRoleDecision(None, "planner_split_checkpoint_completed")

    raise ValueError(f"Unbekannte abgeschlossene Planner-Rolle: {completed_role}")

