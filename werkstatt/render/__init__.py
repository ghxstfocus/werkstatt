"""Loop-Renderer — Fassade (OP-138 Phase 2c).

Rendering lebt in werkstatt/render/*. Re-Export fuer
Rueckwaerts-Kompatibilitaet. Neue Aufrufer importieren direkt
aus werkstatt.render.<modul>.
"""
from __future__ import annotations

from . import emit as _emit_m  # noqa: F401
from . import progress as _progress_mod  # noqa: F401
from . import rich as _rich  # noqa: F401
from . import spinner as _spinner_mod  # noqa: F401
from . import tasks as _tasks_mod  # noqa: F401
from . import tee as _tee_mod  # noqa: F401
from .emit import (  # noqa: F401
    _EMITTERS,
    _EMITTERS_LOCK,
    _PROGRESS_OPEN,
    _PROJECT_CTX,
    TerminalEmitter,
    _emit,
    _emit_raw,
    _get_emitter,
    _get_project,
    _progress_write,
    _publish,
    get_emitter,
    get_project,
    set_project,
)
from .plan import (  # noqa: F401
    _emit_wrapped,
    _render_plan_plain,
    _render_plan_rich,
    panel_diff,
    panel_plan,
    plan,
)
from .progress import (  # noqa: F401
    _LAST_HEARTBEAT,
    _PROGRESS_LOCK,
    _PROGRESS_STATE,
    _emit_progress,
    _null_progress,
    heartbeat,
    progress_task,
)
from .rich import (  # noqa: F401
    _HAS_RICH,
    IS_CI,
    IS_LIVE,
    RENDER_MODE,
    USE_COLOR,
    BarColumn,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    _bold,
    _c,
    _console,
    _cyan,
    _dim,
    _green,
    _red,
    _RichConsole,
    _RichLive,
    _RichPanel,
    _RichProgress,
    _RichSpinner,
    _RichSyntax,
    _use_rich,
    _yellow,
)
from .spinner import (  # noqa: F401
    _live,
    _live_lock,
    _spinner_text,
    _with_spinner,
    spinner_start,
    spinner_stop,
    spinner_update,
)
from .tasks import (  # noqa: F401
    TOTAL_PHASES,
    _timestamp,
    footer,
    group_end,
    group_start,
    header,
    hook,
    log_line,
    patch,
    status_header,
    step,
    summary,
    task,
    task_done,
    task_failed,
    task_ok,
    task_started,
)
from .tee import (  # noqa: F401
    _TEE_LOCK,
    _TEE_STREAM,
    _tee,
    _TeeWriter,
    set_tee_stream,
)
