"""Werkstatt-Phasen — Fassade (OP-139 Phase 2b).

Phase-Orchestrierung lebt in werkstatt/phases/*. Diese Datei
re-exportiert die Phasen-Funktionen und die _common-Stubs fuer
Rueckwaerts-Kompatibilitaet.

Modul-Referenzen (_tasks_mod, _plan_mod, _explorer_mod,
_review_mod, _finalize_mod) sind fuer AST-Guard-Tests gedacht,
die raw-Quelltext ueber alle Phasen-Dateien scannen muessen.
"""
from __future__ import annotations

# Modul-Referenzen (fuer AST-Guard-Tests)
from . import explorer as _explorer_mod  # noqa: F401
from . import finalize as _finalize_mod  # noqa: F401
from . import plan as _plan_mod  # noqa: F401
from . import review as _review_mod  # noqa: F401
from . import tasks as _tasks_mod  # noqa: F401

# Re-Exports aus _common (as-alias-pattern)
from ._common import (
    _apply_one_patch as _apply_one_patch,
)
from ._common import (
    _call_hook as _call_hook,
)
from ._common import (
    _delete_ziel_erlaubt as _delete_ziel_erlaubt,
)
from ._common import (
    _extract_files_from_tasks as _extract_files_from_tasks,
)
from ._common import (
    _gate_failed_payload as _gate_failed_payload,
)
from ._common import (
    _get_git_diff_for_hook as _get_git_diff_for_hook,
)
from ._common import (
    _hat_human_review_tasks as _hat_human_review_tasks,
)
from ._common import (
    _human_gate as _human_gate,
)
from ._common import (
    _human_gate_plan as _human_gate_plan,
)
from ._common import (
    _normalize_tasks as _normalize_tasks,
)
from ._common import (
    _patches_wirklich_angewendet as _patches_wirklich_angewendet,
)
from ._common import (
    _phase_end_reflection as _phase_end_reflection,
)
from ._common import (
    _plan_gate as _plan_gate,
)
from ._common import (
    _pruefe_prior_failed_dependency as _pruefe_prior_failed_dependency,
)
from ._common import (
    _reflection_loop as _reflection_loop,
)
from ._common import (
    _reset_task_state as _reset_task_state,
)
from ._common import (
    _reviewer_rejected_payload as _reviewer_rejected_payload,
)
from ._common import (
    _ruff_fix_changed as _ruff_fix_changed,
)
from ._common import (
    _run_with_progress as _run_with_progress,
)
from ._common import (
    _split_task_on_demand as _split_task_on_demand,
)
from ._common import (
    _task_ende as _task_ende,
)
from ._common import (
    _validate_contract_safe as _validate_contract_safe,
)
from ._common import (
    _verify_patches as _verify_patches,
)
from ._common import (
    _verify_patches_soft as _verify_patches_soft,
)
from ._common import (
    _with_spinner as _with_spinner,
)
from ._common import (
    audit as audit,
)
from ._common import (
    run_builder as run_builder,
)
from ._common import (
    run_explorer as run_explorer,
)
from ._common import (
    run_planner as run_planner,
)
from ._common import (
    run_reviewer as run_reviewer,
)

# Phasen-Funktionen
from .explorer import _phase_explorer_and_setup as _phase_explorer_and_setup
from .finalize import _phase_finalize as _phase_finalize
from .plan import _phase_plan_and_preflight as _phase_plan_and_preflight
from .review import _phase_review_gate as _phase_review_gate
from .tasks import _phase_tasks_loop as _phase_tasks_loop
