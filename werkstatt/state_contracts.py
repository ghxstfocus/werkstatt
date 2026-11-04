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
