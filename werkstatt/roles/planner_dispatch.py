"""Evidence-driven role selection for the Planner checkpoint workflow.

The dispatcher owns the *need* decision; role workers own their specialized
work. It never authorizes code changes or bypasses plan/human gates.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath

from werkstatt.roles.builder_direct import build_direct_edit_plan


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


def direct_builder_route_decision(
    task: str, scout_skip_path: str | None, project_dir,
) -> tuple[bool, str]:
    """Select deterministic Builder planning only with a unique source proof."""
    if scout_skip_path is None:
        return False, "kein_belegtes_einzeldateiziel"
    plan, reason = build_direct_edit_plan(task, scout_skip_path, project_dir)
    return plan is not None, reason


def architect_single_file_task_decision(
    *,
    goal: str,
    architect_prose: str,
    key_files: list[str],
    source_manifest: object,
    project_dir,
) -> tuple[dict | None, str]:
    """Compile one Architect file block only from a complete current proof.

    The Planner-Split remains necessary for multi-file, dependent, oversized,
    or weakly sourced plans. This route avoids another model call only when
    the Architect already supplied one complete, independent file task.
    """
    if not isinstance(goal, str) or not goal.strip() or len(goal) > 500:
        return None, "ziel_fehlt_oder_uebersteigt_einzel_task_limit"
    if re.search(
        r"\b(?:tests?|pytest|regress\w*|unit[- ]tests?)\b",
        goal,
        flags=re.IGNORECASE,
    ):
        return None, "ziel_verlangt_weitere_testplanung"
    if not isinstance(architect_prose, str) or len(architect_prose) > 12_000:
        return None, "architect_prosa_fehlt_oder_zu_gross"
    sections = list(re.finditer(
        r"^##\s+([^\s`]+\.py)\s*$", architect_prose, re.MULTILINE,
    ))
    if len(sections) != 1:
        return None, "architect_plan_hat_nicht_genau_einen_dateiblock"
    target = sections[0].group(1)
    relative = Path(target)
    if (
        relative.is_absolute()
        or PureWindowsPath(target).is_absolute()
        or ".." in relative.parts
        or target.startswith("tests/")
    ):
        return None, "architect_zieldatei_ausserhalb_einzel_task_scope"
    if target not in key_files:
        return None, "architect_zieldatei_nicht_durch_explorer_bestaetigt"

    from werkstatt.task_graph import (
        _check_explicit_keine_in_prosa,
        _parse_architect_deps_block,
    )

    found_dependencies, dependencies = _parse_architect_deps_block(
        architect_prose,
    )
    explicitly_independent = (
        dependencies == {target: []}
        or (
            not dependencies
            and _check_explicit_keine_in_prosa(architect_prose)
        )
    )
    if not found_dependencies or not explicitly_independent:
        return None, "architect_abhaengigkeiten_nicht_eindeutig_unabhaengig"

    if not isinstance(source_manifest, dict):
        return None, "architect_quellmanifest_fehlt"
    sources = source_manifest.get("sources")
    if not isinstance(sources, list):
        return None, "architect_quellbelege_fehlen"
    source_record = next((
        record for record in sources
        if isinstance(record, dict) and record.get("path") == target
    ), None)
    if (
        not isinstance(source_record, dict)
        or source_record.get("complete") is not True
    ):
        return None, "architect_quellbeleg_unvollstaendig"
    source_sha256 = source_record.get("source_sha256")
    if (
        not isinstance(source_sha256, str)
        or not re.fullmatch(r"[0-9a-f]{64}", source_sha256)
    ):
        return None, "architect_quellhash_ungueltig"
    try:
        root = Path(project_dir).resolve(strict=True)
        source_path = (root / relative).resolve(strict=True)
        source_path.relative_to(root)
        source_bytes = source_path.read_bytes()
    except (OSError, RuntimeError, ValueError, TypeError):
        return None, "architect_quellbeleg_nicht_lesbar"
    import hashlib

    if hashlib.sha256(source_bytes).hexdigest() != source_sha256:
        return None, "architect_quellbeleg_veraltet"

    section_end = (
        sections[1].start()
        if len(sections) > 1 else len(architect_prose)
    )
    description = architect_prose[sections[0].start():section_end].strip()
    if not description or len(description) > 12_000:
        return None, "architect_dateiblock_fehlt_oder_zu_gross"
    return {
        "id": "t1",
        "name": f"Architect: {target}",
        "action": "update",
        "task_files": [target],
        "dependencies": [],
        "criterion_refs": ["AC1"],
        "description": description,
    }, "einzelner_unabhaengiger_architect_dateiblock"


def architect_independent_file_tasks_decision(
    *,
    goal: str,
    architect_prose: str,
    key_files: list[str],
    source_manifest: object,
    project_dir,
) -> tuple[list[dict] | None, str]:
    """Compile a small independent Architect file set without another LLM.

    This is deliberately narrower than the Planner-Split: each file must be
    an Explorer-confirmed Python source, have a complete current source hash,
    and be explicitly declared dependency-free by Architect. Test planning,
    dependencies, stale evidence, and oversized plans remain role work.
    """
    if not isinstance(goal, str) or not goal.strip() or len(goal) > 500:
        return None, "ziel_fehlt_oder_uebersteigt_einzel_task_limit"
    if re.search(
        r"\b(?:tests?|pytest|regress\w*|unit[- ]tests?)\b",
        goal,
        flags=re.IGNORECASE,
    ):
        return None, "ziel_verlangt_weitere_testplanung"
    if not isinstance(architect_prose, str) or len(architect_prose) > 12_000:
        return None, "architect_prosa_fehlt_oder_zu_gross"
    sections = list(re.finditer(
        r"^##\s+([^\s`]+\.py)\s*$", architect_prose, re.MULTILINE,
    ))
    if not 2 <= len(sections) <= 5:
        return None, "architect_plan_hat_nicht_zwei_bis_fuenf_dateibloecke"
    targets = [match.group(1) for match in sections]
    if len(set(targets)) != len(targets):
        return None, "architect_plan_hat_doppelte_dateibloecke"
    for target in targets:
        relative = Path(target)
        if (
            relative.is_absolute()
            or PureWindowsPath(target).is_absolute()
            or ".." in relative.parts
            or target.startswith("tests/")
        ):
            return None, "architect_zieldatei_ausserhalb_einzel_task_scope"
        if target not in key_files:
            return None, "architect_zieldatei_nicht_durch_explorer_bestaetigt"

    from werkstatt.task_graph import (
        _check_explicit_keine_in_prosa,
        _parse_architect_deps_block,
    )

    found_dependencies, dependencies = _parse_architect_deps_block(
        architect_prose,
    )
    explicitly_independent = (
        dependencies == {target: [] for target in targets}
        or (
            not dependencies
            and _check_explicit_keine_in_prosa(architect_prose)
        )
    )
    if not found_dependencies or not explicitly_independent:
        return None, "architect_abhaengigkeiten_nicht_eindeutig_unabhaengig"

    if not isinstance(source_manifest, dict):
        return None, "architect_quellmanifest_fehlt"
    sources = source_manifest.get("sources")
    if not isinstance(sources, list):
        return None, "architect_quellbelege_fehlen"
    try:
        root = Path(project_dir).resolve(strict=True)
    except (OSError, RuntimeError, TypeError, ValueError):
        return None, "architect_quellbeleg_nicht_lesbar"

    import hashlib

    tasks: list[dict] = []
    for index, (target, section) in enumerate(zip(targets, sections, strict=True)):
        source_record = next((
            record for record in sources
            if isinstance(record, dict) and record.get("path") == target
        ), None)
        if (
            not isinstance(source_record, dict)
            or source_record.get("complete") is not True
        ):
            return None, "architect_quellbeleg_unvollstaendig"
        source_sha256 = source_record.get("source_sha256")
        if (
            not isinstance(source_sha256, str)
            or not re.fullmatch(r"[0-9a-f]{64}", source_sha256)
        ):
            return None, "architect_quellhash_ungueltig"
        try:
            source_path = (root / Path(target)).resolve(strict=True)
            source_path.relative_to(root)
            source_bytes = source_path.read_bytes()
        except (OSError, RuntimeError, ValueError, TypeError):
            return None, "architect_quellbeleg_nicht_lesbar"
        if hashlib.sha256(source_bytes).hexdigest() != source_sha256:
            return None, "architect_quellbeleg_veraltet"
        section_end = (
            sections[index + 1].start()
            if index + 1 < len(sections) else len(architect_prose)
        )
        description = architect_prose[section.start():section_end].strip()
        if not description or len(description) > 12_000:
            return None, "architect_dateiblock_fehlt_oder_zu_gross"
        tasks.append({
            "id": f"t{index + 1}",
            "name": f"Architect: {target}",
            "action": "update",
            "task_files": [target],
            "dependencies": [],
            "criterion_refs": ["AC1"],
            "description": description,
        })
    return tasks, "kleiner_unabhaengiger_architect_dateisatz"


def choose_next_planner_role(
    *,
    scout_skip_path: str | None,
    completed_role: str | None = None,
    scout_already_fulfilled: bool = False,
    deterministic_task_graph_ready: bool = False,
    direct_builder_ready: bool = False,
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
    if direct_builder_ready:
        return PlannerRoleDecision(
            "builder_direct", "unique_source_bound_edit_ready",
        )

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

