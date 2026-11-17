"""Legacy loop helper exports used while call sites migrate to role modules."""
from __future__ import annotations

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
    run_reviewer as run_reviewer,
)
