"""Werkstatt: Dataclasses und Enums.

W36 (2026-10-17): Extrahiert aus pipeline.py.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from werkstatt.config import Config

SUBPROCESS_TIMEOUT = 60


class BudgetExhausted(Exception):
    """Wird geworfen, wenn das LLM-Budget erschoepft ist."""


@dataclass(frozen=True)
class Measurement:
    mid: str
    argv: tuple[str, ...]
    beschreibung: str
    timeout_s: int = SUBPROCESS_TIMEOUT


@dataclass
class Messung:
    """W52b (2026-10-18): strukturierte Einzelmessung.

    Ersetzt schrittweise mess_protokoll (String).
    Jede Messung liegt als Datei unter
    .werkstatt/<run_id>/messungen/<sha1>.txt.
    """
    pfad: str           # Zieldatei-Pfad
    sha1: str           # Inhalt-Hash
    mtime: float        # mtime zum Mess-Zeitpunkt
    groesse: int        # Bytes
    quelle: str         # "builder", "planner", "reviewer"
    datei: Path | None = None  # Pfad zur Mess-Datei


@dataclass
class LLMReply:
    ok: bool
    content: str = ""
    error: str = ""
    # MESS-1: Prompt-Laengen (Zeichen nach Redaktion, vor HTTP).
    system_len: int = 0
    user_len: int = 0


class SolverDiagnose(Enum):
    """Auflage 2183 A2: vier Solver-Diagnostypen."""
    GLEICHER_FEHLER = "gleicher_fehler"
    ANDERER_FEHLER = "anderer_fehler"
    WIDERSPRUCH = "widerspruch"
    UNKLAR = "unklar"


@dataclass
class SolverBefund:
    """Auflage 2183 A2: strukturierter Solver-Befund.

    Wird vom Solver (B) erzeugt und in state.solver_befunde
    gespeichert. Getrennt von RecoveryVorschlag.
    """
    art: SolverDiagnose
    kandidaten: list[str] = field(default_factory=list)
    praezisierter_auftrag: str = ""
    rueckspiel_hinweis: str = ""
    eskalation: str = ""
    run_id: str = ""

    def ist_vollstaendig(self) -> bool:
        """Auflage 2183 A2: Felder fuer die Diagnose gefuellt?"""
        if self.art == SolverDiagnose.GLEICHER_FEHLER:
            return bool(self.kandidaten)
        if self.art == SolverDiagnose.ANDERER_FEHLER:
            return bool(self.praezisierter_auftrag)
        if self.art == SolverDiagnose.WIDERSPRUCH:
            return bool(self.rueckspiel_hinweis)
        if self.art == SolverDiagnose.UNKLAR:
            return bool(self.eskalation)
        return False


@dataclass
class RepairAttempt:
    nummer: int
    fehler_vor: list[str]
    massnahme: str
    erfolg: bool
    protokoll: str


@dataclass
class RecoveryVorschlag:
    art: str
    diagnose: str = ""
    reparaturplan: list[str] = field(default_factory=list)
    empfehlung: str = ""
    blockgroesse: str = ""
    frage_an_menschen: str = ""
    rohantwort: str = ""


@dataclass
class RunState:
    block_id: str = ""
    aufgabe: str = ""
    start_ts: str = ""
    docs: dict[str, str] = field(default_factory=dict)
    agents: dict[str, dict[str, Any]] = field(default_factory=dict)
    always: dict[str, Measurement] = field(default_factory=dict)
    optional: dict[str, Measurement] = field(default_factory=dict)
    file_whitelist: list[str] = field(default_factory=list)
    api_key: str = ""
    budget: dict[str, int] = field(default_factory=dict)
    agent_docs: dict[str, list[str]] = field(default_factory=dict)
    project_dir: Path = field(default_factory=lambda: Path("."))
    # Agent-Memory A2: Projekt-Stand (aus memory.yaml).
    projekt_stand: dict = field(default_factory=dict)
    start_monotonic: float = 0.0  # Auflage 2080: Zeitmessung
    scout_api_auszug: dict = field(default_factory=dict)
    # OP-135b: Explorer-Dateiliste (key_files + findings + next_reads).
    # Struktur identisch zu pipeline_phases.py:explorer_result.
    explorer_context: dict = field(default_factory=dict)

    # M-WelleE (2026-11-02): strukturierte Explorer-Findings.
    # Fliesst in Architect- und Builder-Prompt. Format:
    # {"pytest_laufzeit_s": int, "ruff_befunde": list, ...}
    explorer_findings: dict = field(default_factory=dict)
    # Welle H (2026-11-02): Plan-Reject-Reflection.
    # last_reject_kind: "plan" | "human" | "" — woher der Reject kam
    # last_reject_reason: freier Text vom User (beim n-Reject abgefragt)
    last_reject_kind: str = ""
    last_reject_reason: str = ""


    # M-WelleB (2026-11-02): Content-Check-Bestätigung.
    # True = Auftrag-bereits-erfuellt wurde durch DETERMINISTISCHEN
    # Content-Check bestätigt (nicht durch LLM-Urteil).
    # Quelle: aus welcher Setzen-Stelle (für Audit).
    auftrag_bereits_erfuellt_bestaetigt: bool = False
    auftrag_bereits_erfuellt_quelle: str = ""

    # W51g: lokales Dedup-Set (Loop-Lebenszyklus,
    # in _planner_lauf gesetzt und verworfen).
    _w51g_gemessen: set[str] = field(default_factory=set)
    # Timeout-Fix 2026-10-16: Gesamt-Deadline
    # pro ask_llm-Aufruf (Retry-Kette).
    max_total_llm_s: int = 240
    git_author_name: str = ""
    git_author_email: str = ""
    project_name: str = ""
    basis_protokoll: str = ""
    basis_protokoll_nach_apply: str = ""  # UMB-1b
    mess_protokoll: str = ""
    # DEPRECATED (W52b-E): String-Kanal. Wird parallel zu
    # state.messungen gefuellt, damit Bestandsleser bis zum
    # vollstaendigen Umbau funktionieren. Neue Leser MUESSEN
    # state.messungen (Datei-Referenzen) nutzen. Entfaellt,
    # sobald alle Leser umgestellt sind.
    # W52b (2026-10-18): strukturierte Messungen.
    # Wird parallel zu mess_protokoll gefuellt,
    # bis alle Leser umgestellt sind.
    messungen: list = field(default_factory=list)
    # W59 (2026-10-18): gelesene Dateien + mtime.
    # Pfad -> mtime. apply_code_patches prueft.
    gelesene_dateien: dict = field(default_factory=dict)
    # Post-Apply-Neumessung 2026-10-16:
    # read_file-Messungen fuer new_file-Pfade nach Apply.
    mess_protokoll_nach_apply: str = ""
    # DEPRECATED (W52b-E): String-Kanal. Strukturierte Quelle
    # ist state.messungen_nach_apply. Fallback fuer Bestands-
    # leser bis zum vollstaendigen Umbau.
    # WEG-X-P22a (2026-10-17): strukturierte Gate-Ergebnisse
    # aus _basis_gate_pytest_ziel / _basis_gate_pytest_suite.
    # Pro Aufruf ein dict mit scope, exit_code, klassifizierung,
    # failed_count, passed_count, failed_test_ids, raw_tail.
    basis_gate_test_results: list[dict[str, Any]] = \
        field(default_factory=list)
    # W25 (2026-10-17): Skills (on-demand).
    geladene_skills: list[str] = field(default_factory=list)
    # Bug-Fix 2026-10-14: True, sobald mindestens
    # ein Apply passiert ist. Der GEMESSENER
    # INHALT-Block ist dann der Stand VOR dem
    # Apply. Kein Reset (mess_protokoll ist
    # akkumulativ).
    mess_protokoll_veraltet: bool = False
    # Auflage 2183 A2: run_id fuer Korrelation.
    run_id: str = ""
    # Post-Apply-Fix 2026-10-16: Recovery-Plan aus
    # apply_and_recheck fuer die Builder-Korrektur-Runde.
    letzter_recovery_vorschlag: object = None
    code_patches: list[dict[str, str]] = field(default_factory=list)  # UMB-1b
    commit_paket: dict[str, Any] = field(default_factory=dict)
    llm_calls: int = 0
    # Block P2a: Phasen-Modus (Stufe 2).
    phase_id: str | None = None
    phase_titel: str = ""
    phase_unterbloecke: list[dict[str, Any]] = \
        field(default_factory=list)
    phase_aktueller_index: int = 0
    phase_start_head: str = ""
    phase_aktiv: bool = False
    # M-299a: Preflight-Scan + Fehler-Klassifikation.
    # Liste von dicts: [{klasse, stage_id, datei, text}, ...]
    preflight_fehler: list[dict] = field(default_factory=list)
    # M-310: Phasen-Hierarchie (Haupt- und Unterpunkte).
    phasen: list[dict] = field(default_factory=list)
    # M-314: Reviewer-Bugs (file/line/description/severity).
    # Wird von run_reviewer befuellt, von _reflection_loop
    # als Kontext an den Builder uebergeben.
    reviewer_bugs: list[dict] = field(default_factory=list)
    # K40: Historie aller Reviewer-Runden (pro Runde eine Bug-Liste).
    reviewer_bugs_history: list[list[dict]] = field(default_factory=list)
    # K47: Historie der Reflection-Runden pro Task.
    # Pro Eintrag: {runde, verify_errors, reviewer_bugs, patches_applied}.
    reflection_history: list[dict] = field(default_factory=list)
    # AST-Info einmal pro Lauf. Wird von run_architect befuellt,
    # von Builder und Architect-Prompt gelesen.
    api_index_cache: dict = field(default_factory=dict)

    # Stellschrauben 2026-11-03: Skills-Bloecke pro Rolle.
    planner_skills_block: str = ""
    reflection_skill_body: str = ""
    architect_skills_block: str = ""

    # FOLLOW_UP: Baseline-Schuld, ueber Phasen erhalten.
    follow_up_fehler: list[dict] = field(default_factory=list)
    # OP-067: in der laufenden Reflection-Runde angewendete Patches.
    # Dient als Fallback-Quelle fuer `_expand_cmd_placeholders`, wenn
    # `state.patches` bereits geleert wurde. Lebenszyklus: pro Runde
    # `clear()` + `extend()`, am Rundenende `clear()`.
    tasks: list[dict[str, object]] = field(default_factory=list)
    akzeptanzkriterien: list = field(default_factory=list)
    # OP-135b: Testliste aus PlannerOutput (Planer->Builder).
    tests: list = field(default_factory=list)
    architect_prosa: str = ""
    builder_feedback: dict[str, str] = field(default_factory=dict)
    patches: list[dict[str, object]] = field(default_factory=list)
    patches_aktuell_runde: list[dict[str, object]] = \
        field(default_factory=list)

    # === OP-141 Vorarbeit: Ghost-Felder deklariert (2026-11-05) ===
    # Vormals nur via state.X = ... gesetzt, nie deklariert. Jetzt sichtbar in
    # @dataclass, durchsuchbar via grep, typsicher in IDE/Static-Analysis.
    _reflection_bug_sigs_vorher: frozenset = field(default_factory=frozenset)
    _reflection_diff_hash: str | None = None
    aktuelle_task: dict = field(default_factory=dict)
    applied_count: int = 0
    auftrag_bereits_erfuellt: bool = False
    auto_approve: bool = False
    baseline_gruen: bool = False
    explorer_pytest_laufzeit_s: int = 0
    explorer_ruff_befunde: list = field(default_factory=list)
    last_planner_info: dict = field(default_factory=dict)
    # Letzter Test-Fehler aus einer vorherigen Runde. Wird von
    # `_reflection_loop` (OP-147) als zusaetzlicher Block in den
    # Feedback-Prompt gehaengt, sofern er nicht bereits identisch in
    # `last_verify_errors` enthalten ist (dedupliziert). Bei leerem
    # Wert kein Verhaltensdelta.
    letzter_test_fehler: str = ""
    last_verify_errors: list = field(default_factory=list)
    last_verify_hart_stages: set = field(default_factory=set)
    messungen_nach_apply: list = field(default_factory=list)
    phase_review_uebersprungen: str = ""
    progress_written_at_commit: bool = False
    reflection_erschoepft: bool = False
    reflection_phase: bool = False
    reviewer_deterministic_fail: bool = False
    reviewer_stagnation_false_positive: bool = False
    scout_bereits_erfuellt: bool = False
    spec_widerspruch_erkannt: bool = False
    split_failure_grund: str | None = None
    tasks_ok_counter: int = 0


@dataclass
class VorlaufErgebnis:
    """C0+C1: Rueckgabe von _vorlauf_und_state.

    Alle 10 Werte, die run_pipeline nach C0+C1 braucht.
    docs/agents fallen weg (in state.docs/state.agents).
    """
    state: RunState
    config: Config
    budget: dict
    max_llm: int
    max_minutes: int
    project_dir: Path
    file_whitelist: list
    api_key: str
    always: dict
    optional: dict


@dataclass
class NachlaufErgebnis:
    """Ergebnis des Nachlaufs von run_phase (3a-2c, M-83/M-85).

    3 Felder: rc, aggregat, wahl.
    """
    rc: int
    aggregat: dict
    wahl: str


@dataclass
class PhaseVorlaufErgebnis:
    """Ergebnis des Vorlaufs von run_phase (3a-2a).

    4 Felder. Bewusst NICHT VorlaufErgebnis (werkstatt/state.py) wieder-
    verwendet: VorlaufErgebnis hat 10 Felder (config, budget, max_llm,
    max_minutes, project_dir, file_whitelist, always, optional + state +
    api_key), davon 8 in 3a-2a ungenutzt. Konsistenz: state ist wie in
    VorlaufErgebnis enthalten (Durchreichen an untergeordnete Funktionen),
    damit kuenftige Felder (max_llm, budget) ohne Signatur-Bruch ergaenzt
    werden koennen.
    """
    state: RunState
    unterbloecke: list
    api_key: str
    max_phase: int


@dataclass
class PhaseMainVorlaufErgebnis:
    """Rueckgabe _phase_main_vorlauf (3a-3a).

    Aus _phase_main_pfad Block A (29da314 Z.10367..10462).
    11 Felder (M-120 A.1/A.2/A.3 Typen gemessen):
      api_key            os.getenv(...).strip()           -> str
      config             _lade_und_pruefe_projekt()       -> dict[str, Any]
      project_dir        Path(...).expanduser()           -> Path
      agents             {}                              -> dict[str, dict[str, Any]]
      docs               load_docs()                      -> dict[str, str]
      file_whitelist     config.get("file_whitelist", []) -> list[str]
      always_kat         build_catalog()[0]               -> dict[str, Measurement]
      optional_kat       build_catalog()[1]               -> dict[str, Measurement]
      planner_modus      str(_pcfg.get("modus", "manual"))-> str
      planner_max_runden int(_pcfg.get("max_runden", 3))  -> int
      plan_vorhanden     _phase_plan_laden()              -> dict[str, Any] | None
    """
    api_key: str
    config: Config
    project_dir: Path
    agents: dict[str, dict[str, Any]]
    docs: dict[str, str]
    file_whitelist: list[str]
    always_kat: dict[str, Measurement]
    optional_kat: dict[str, Measurement]
    planner_modus: str
    planner_max_runden: int
    plan_vorhanden: dict[str, Any] | None


@dataclass
class PhaseMainPlannerKontext:
    """Rueckgabe _phase_main_planner_vorb (3a-3c-2a).

    6 Felder aus _phase_main_pfad body[17..27] (M-149).
    """
    state: RunState
    phase_plan_ok: bool
    phase_id: str
    phase_titel: str
    unterbloecke: list
    letzter_vorschlag: tuple | None
