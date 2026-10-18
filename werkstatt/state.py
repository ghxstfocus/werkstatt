"""Werkstatt: Dataclasses und Enums.

W36 (2026-10-17): Extrahiert aus pipeline.py.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

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
    datei: "Path | None" = None  # Pfad zur Mess-Datei


@dataclass
class LLMReply:
    ok: bool
    content: str = ""
    error: str = ""


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
    block_id: str
    aufgabe: str
    start_ts: str
    docs: dict[str, str]
    agents: dict[str, dict[str, Any]]
    always: dict[str, Measurement]
    optional: dict[str, Measurement]
    file_whitelist: list[str]
    api_key: str
    budget: dict[str, int]
    agent_docs: dict[str, list[str]]
    project_dir: Path
    # Agent-Memory A2: Projekt-Stand (aus memory.yaml).
    projekt_stand: dict = field(default_factory=dict)
    start_monotonic: float = 0.0  # Auflage 2080: Zeitmessung
    # Auflage 2183 P1 (U3): Schwellwert + min_tokens
    # justierbar, nicht im Code hart.
    solver_config: dict[str, float] = field(
        default_factory=dict)
    # Planner-Konfiguration (Block P1, 2026-10-15).
    # SS7-(C): Modell als hartcodierter Default, analog
    # zu builder_model. Frontmatter wird heute nicht gelesen.
    planner_model: str = "deepseek-chat"
    planner_modus: str = "manual"
    # W35a-2 (2026-10-17): Planner-Resume-Cap
    # pro uid. Max 1x pro Unterblock pro Prozess.
    planner_resume_anzahl: dict[str, int] = \
        field(default_factory=dict)
    # W51g (2026-10-18): Format-Fehler-
    # Kontext fuer den Planner (Runde > 1).
    letzter_plan_fehler: str = ""
    # W51g: lokales Dedup-Set (Loop-Lebenszyklus,
    # in _planner_lauf gesetzt und verworfen).
    _w51g_gemessen: set[str] = field(default_factory=set)
    planner_runden: int = 0
    reviewer_verdict_model: str = "deepseek-chat"
    reviewer_recovery_model: str = "deepseek-reasoner"
    # W28b: Judge-Modell (Code-Review mit frischem Kontext).
    judge_model: str = "deepseek-reasoner"
    # W61c: Solver-Modell (eigene Rolle, Diagnose).
    # Reasoner-Klasse, weil Deadlock-Diagnose Reasoning braucht.
    solver_model: str = "deepseek-reasoner"
    # W28c: max_tokens pro Rolle.
    max_tokens_builder: int = 8192
    max_tokens_judge: int = 2048
    max_tokens_reviewer: int = 1024
    max_tokens_planner: int = 8192
    max_tokens_solver: int = 2048
    builder_model: str = "deepseek-chat"
    builder_temp: float = 0.3
    test_gen_model: str = "deepseek-chat"
    llm_timeout_s: int = 180
    # Timeout-Fix 2026-10-16: Gesamt-Deadline
    # pro ask_llm-Aufruf (Retry-Kette).
    max_total_llm_s: int = 240
    git_author_name: str = ""
    git_author_email: str = ""
    project_name: str = ""
    coverage_pct: int = -1  # -1 = nicht gemessen
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
    code_entwurf: str = ""
    # Auflage 2183 A1b: Historisierung fuer Solver-Vergleich.
    code_entwurf_historie: list[dict[str, Any]] = \
        field(default_factory=list)
    # Auflage 2183 A2: run_id fuer Korrelation.
    run_id: str = ""
    # Auflage 2183 A2: Solver-Befunde.
    solver_befunde: list[SolverBefund] = \
        field(default_factory=list)
    # Auflage 2183 C: Quellen der Solver-Laeufe.
    solver_trigger_quellen: list[str] = \
        field(default_factory=list)
    # Auflage 2183 Block 5: Zaehlt Solver-Versuche
    # (auch fehlgeschlagene, GG2).
    solver_aufrufe: int = 0
    # Stufe 0 Aenderung 2: Anker- und Ersatz-Fehler
    # im Builder-Loop. Wird in _builder_user_prompt
    # als Rueckmeldung angezeigt.
    letzte_anker_fehler: list[tuple[int, str, str, str]] = \
        field(default_factory=list)
    letzte_ersatz_fehler: list[tuple[int, str, str]] = \
        field(default_factory=list)
    anker_fehler_in_folge: int = 0
    # P2b-Frage-A / A4: Rueckfrage und Antwort.
    letzte_builder_frage: str = ""
    letzte_reviewer_antwort: str = ""
    # Plan-Korrektur / V-A1: geteilter Zyklus-Zaehler.
    phase_korrektur_zyklus: int = 0
    # Post-Apply-Fix 2026-10-16: Recovery-Plan aus
    # apply_and_recheck fuer die Builder-Korrektur-Runde.
    letzter_recovery_vorschlag: object = None
    # Block Auftrag-erfuellt B3: letzter Patch war
    # wirkungslos (anker == ersatz). Signal fuer B2.
    letzter_patch_wirkungslos: bool = False
    code_patches: list[dict[str, str]] = field(default_factory=list)  # UMB-1b
    test_vorschlaege: str = ""
    commit_paket: dict[str, Any] = field(default_factory=dict)
    commit_review: dict[str, Any] = field(default_factory=dict)
    review_runden: list[dict[str, Any]] = field(default_factory=list)
    commands_log: list[dict[str, str]] = field(default_factory=list)
    auflagen_log: list[list[str]] = field(default_factory=list)
    empfehlung_log: list[dict[str, str]] = field(default_factory=list)
    llm_calls: int = 0
    # Block P2a: Phasen-Modus (Stufe 2).
    phase_id: str | None = None
    phase_titel: str = ""
    phase_unterbloecke: list[dict[str, Any]] = \
        field(default_factory=list)
    phase_aktueller_index: int = 0
    phase_commit_pakete: list[dict[str, Any]] = \
        field(default_factory=list)
    phase_start_head: str = ""
    phase_aktiv: bool = False



