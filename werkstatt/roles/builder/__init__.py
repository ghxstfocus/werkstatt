"""Werkstatt-Rolle Builder — Fassade (OP-140 Phase 2b).

Aufteilung:
  ast.py       Projekt-Python-Scan, Symbol-Checks
  prompt.py    BUILDER_SYSTEM + Prompt-Bau
  validate.py  Import-Validierung im Patch
  patch.py     Aider-Patch-Normalisierung, Apply-Filter
  run.py       _build_patches_fuer_datei + run_builder
  _common.py   ask_llm, audit (Modul-Globals fuer Tests)

Neue Aufrufer importieren direkt aus dem passenden Submodul.
AST-Helpers direkt: from werkstatt.roles.builder.ast import ...
"""
from __future__ import annotations

from . import _common as _common
from ._common import (
    ask_llm as ask_llm,
)
from ._common import (
    audit as audit,
)
from .ast import (
    _PY_IGNORE_PARTS as _PY_IGNORE_PARTS,
)
from .ast import (
    _ast_block_fuer_zieldatei as _ast_block_fuer_zieldatei,
)
from .ast import (
    _finde_modul_pfad as _finde_modul_pfad,
)
from .ast import (
    _hat_symbol as _hat_symbol,
)
from .ast import (
    _sammle_projekt_py_files as _sammle_projekt_py_files,
)
from .patch import (
    _architect_abschnitt as _architect_abschnitt,
)
from .patch import (
    _extrahiere_verbote as _extrahiere_verbote,
)
from .patch import (
    _filtere_auf_funktionen as _filtere_auf_funktionen,
)
from .patch import (
    _korrigiere_builder_action as _korrigiere_builder_action,
)
from .patch import (
    _korrigiere_doku_datum as _korrigiere_doku_datum,
)
from .patch import (
    _normalisiere_aider_patches as _normalisiere_aider_patches,
)
from .patch import (
    _pruefe_doku_patch_breite as _pruefe_doku_patch_breite,
)
from .prompt import (
    _REVIEWER_SCHNITTSTELLE as _REVIEWER_SCHNITTSTELLE,
)
from .prompt import (
    BUILDER_SYSTEM as BUILDER_SYSTEM,
)
from .prompt import (
    _builder_system as _builder_system,
)
from .prompt import (
    _format_explorer_findings_b as _format_explorer_findings_b,
)
from .prompt import (
    _format_scout_apis_for_builder as _format_scout_apis_for_builder,
)
from .run import (
    _build_patches_fuer_datei as _build_patches_fuer_datei,
)
from .run import (
    run_builder as run_builder,
)
from .validate import (
    _validate_imports_in_patch as _validate_imports_in_patch,
)
