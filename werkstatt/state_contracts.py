"""State-Contracts — Dataclasses + Registry (OP-135a).

Read-only Property-Views auf RunState-Felder. Kein Pipeline-Fix.

Alle Dataclasses erben von ContractDict für dict-artigen Zugriff
(__getitem__, get, to_dict, from_dict) — für Rückwärts-Kompatibilität
mit bestehenden Aufrufern, die heute dict-Zugriff nutzen.

Kein Import aus werkstatt.* in diesem Modul — Modul bleibt leaf.
Lazy-Import in state.py verhindert Zirkularität.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Callable


class ContractDict:
    """Mixin: dict-artiger Zugriff auf Dataclass-Felder."""

    def __getitem__(self, key: str) -> Any:
        if hasattr(self, key):
            return getattr(self, key)
        raise KeyError(key)

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict | None) -> "ContractDict":
        if not d:
            return cls()
        known = {f.name for f in cls.__dataclass_fields__.values()}
        return cls(**{k: v for k, v in d.items() if k in known})


@dataclass
class KeyFile(ContractDict):
    file: str
    why: str = ""
    symbols: str = ""
    preview: str = ""
    confidence: str = "medium"


@dataclass
class ExplorerOutput(ContractDict):
    findings: str = ""
    key_files: list[KeyFile] = field(default_factory=list)
    next_reads: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.key_files = [
            k if isinstance(k, KeyFile) else KeyFile.from_dict(k)
            for k in self.key_files
        ]


@dataclass
class ExplorerDiagnostics(ContractDict):
    git_dirty: bool = False
    pytest_laufzeit_s: int = 0
    ruff_befunde: list = field(default_factory=list)


@dataclass
class ScoutOutput(ContractDict):
    api_auszug: dict[str, list[str]] = field(default_factory=dict)
    bereits_erfuellt: bool = False


@dataclass
class ArchitectOutput(ContractDict):
    prosa: str = ""


@dataclass
class PlannerOutput(ContractDict):
    tasks: list[dict] = field(default_factory=list)
    tests: list[str] = field(default_factory=list)
    akzeptanzkriterien: list[str] = field(default_factory=list)


@dataclass
class Contract:
    typ: str
    schreiber: list[str]
    leser: list[str]
    pflicht: bool = True
    validator: Callable | None = None
    hinweis: str = ""


CONTRACTS: dict[str, Contract] = {
    "explorer_output": Contract(
        typ="ExplorerOutput",
        schreiber=["pipeline_phases._phase_explorer_and_setup"],
        leser=["builder.run_builder", "planner.run_planner",
               "scout.run_scout"],
        pflicht=True,
    ),
    "explorer_diagnostics": Contract(
        typ="ExplorerDiagnostics",
        schreiber=["explorer.run_explorer (deterministischer Pfad, "
                   "neu in OP-135a)"],
        leser=["architect.run_architect"],
        pflicht=True,
        hinweis="Heute leer im LLM-Fallback; deterministischer Pfad "
                "befuellt ab OP-135a.",
    ),
    "scout_output": Contract(
        typ="ScoutOutput",
        schreiber=["planner._run_scout"],
        leser=["architect.run_architect", "builder.run_builder"],
        pflicht=False,
        hinweis="Scout kann ausbleiben (bereits_erfuellt).",
    ),
    "architect_output": Contract(
        typ="ArchitectOutput",
        schreiber=["architect.run_architect"],
        leser=["planner.run_planner", "builder.run_builder",
               "gates._human_gate_plan"],
        pflicht=True,
    ),
    "planner_output": Contract(
        typ="PlannerOutput",
        schreiber=["planner.run_planner", "task_runner.run_task"],
        leser=["builder.run_builder", "gates._human_gate_plan",
               "pipeline_phases"],
        pflicht=True,
    ),
}


# ============================================================
# OP-136: Contract-Validierung (fail-loud)
# ============================================================


class ContractViolation(Exception):
    """Pflichtfeld nicht befuellt — Loop muss abbrechen (OP-136)."""

    def __init__(self, transition: str, felder: list[str]):
        self.transition = transition
        self.felder = felder
        super().__init__(
            f"ContractViolation bei '{transition}': "
            f"Pflichtfelder leer: {', '.join(felder)}"
        )


# Welche Contract-Felder sind bei welchem Uebergang Pflicht?
# True = immer Pflicht, "auto" = nur wenn das Feld nicht leer ist.
TRANSITIONS: dict[str, list[tuple[str, bool | str]]] = {
    "explorer->scout": [
        ("explorer_output", True),
    ],
    "scout->architect": [
        ("scout_output", "auto"),  # Scout kann ausbleiben (bereits_erfuellt)
    ],
    "architect->planner": [
        ("architect_output", True),
    ],
    "planner->builder": [
        ("planner_output", True),
    ],
    "builder->reviewer": [
        ("planner_output", True),
    ],
}


# Mapping Contract-Name -> Property-Name auf RunState.
# Heute identisch; getrennt, damit Umbenennungen in OP-135b nur hier
# nachgezogen werden muessen.
_PROP_NAME: dict[str, str] = {
    "explorer_output": "explorer_output",
    "explorer_diagnostics": "explorer_diagnostics",
    "scout_output": "scout_output",
    "architect_output": "architect_output",
    "planner_output": "planner_output",
}


def _ist_leer(prop) -> bool:
    """Prueft, ob eine Property-View leer ist (alle Felder default)."""
    if prop is None:
        return True
    if isinstance(prop, ContractDict):
        d = prop.to_dict()
        return all(not v for v in d.values())
    return False


def _do_audit_violation(state, key: str, leer: list[str]) -> None:
    """Schreibt das Audit-Event (lazy import gegen Zirkularitaet).

    Der Call heisst bewusst 'audit(...)' (nicht 'audit_fn(...)'),
    damit tools/audit_drift.py ihn im AST findet.
    """
    try:
        from werkstatt.audit import audit
    except ImportError:
        return
    try:
        audit(
            "state_contract_violation",
            {"transition": key, "felder": leer},
            str(getattr(state, "project_dir", "")),
            str(getattr(state, "project_name", "")),
        )
    except Exception:  # noqa: BLE001
        pass  # Audit-Fehler darf Validation nicht verhindern


def validate_transition(
    von: str,
    zu: str,
    state,
    audit_fn=None,
) -> None:
    """Prueft Pflichtfelder fuer einen Rollenwechsel (OP-136).

    Wirft ContractViolation bei Verstoss. audit_fn (fuer Tests) ersetzt
    den Standard-audit()-Call aus _do_audit_violation.
    """
    key = f"{von}->{zu}"
    if key not in TRANSITIONS:
        return

    leer: list[str] = []
    for feld_name, regel in TRANSITIONS[key]:
        if regel == "auto":
            continue
        if regel is True:
            prop = getattr(state, _PROP_NAME[feld_name], None)
            if _ist_leer(prop):
                leer.append(feld_name)

    if not leer:
        return

    if audit_fn is not None:
        try:
            audit_fn(
                "state_contract_violation",
                {"transition": key, "felder": leer},
                str(getattr(state, "project_dir", "")),
                str(getattr(state, "project_name", "")),
            )
        except Exception:  # noqa: BLE001
            pass
    else:
        _do_audit_violation(state, key, leer)

    raise ContractViolation(key, leer)
