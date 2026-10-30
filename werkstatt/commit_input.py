"""Commit/Judge-Input-Bau (Phase 2 / Gate 18, 2026-10-19).

Aus pipeline.py extrahiert (Reviewer-Gate 18 /
commit_input.py: B, B-2 zweite Haelfte).

Enthaelt:
- _build_commit_input (102 Z.)
- _build_judge_input (66 Z.)
- _build_phase_judge_input (69 Z.)
- _format_basis_gate_test_results (27 Z.)
- format_code_patches_fuer_commit (28 Z.)

Konsumenten: pipeline.py (Loop-Kontext).

Abhaengigkeiten (B-1): state.*-Zugriffe, keine
Rufe aus prompts.py, keine HARD_RULES_*.
measurement.py-Funktionen: collect_messwerte,
format_messwerte_block, _mess_index_block,
_mess_inhalt_nach_apply.

P1-Verortung (Befund BR): der 579-Verlust entsteht
NICHT hier, sondern in pipeline.py/_post_apply_messung
(Schreiber-Seite). _build_commit_input ist der
Konsument, nicht die Ursache.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Any

from werkstatt.measurement import (
    _mess_index_block,
    _mess_inhalt_nach_apply,
    collect_messwerte,
    format_messwerte_block,
)
from werkstatt.subprocess_env import subprocess_env

if TYPE_CHECKING:
    from werkstatt.state import RunState


def _build_phase_judge_input(
    state: RunState,
    aggregat: dict[str, Any],
) -> str:
    """W29b: User-Content fuer den Phase-Judge.

    W29-A4: Der Phase-Judge sieht Diff-Statistik
    + die 3 groessten Dateien als Voll-Diff,
    NICHT den vollen Diff. Vollstaendige
    Konsistenz-Pruefung ist bewusst nicht
    abgedeckt (Merkposten: Chunking bei
    wachsenden Phasen).
    """
    zeilen: list[str] = [
        f"=== PHASE {state.phase_id}: {state.phase_titel} ===",
        (f"Unterbloecke: {aggregat['unterbloecke_done']}"
         f" / {aggregat['unterbloecke_total']} done"),
        f"Pakete: {aggregat['pakete']}",
        f"Dateien (Union): {len(aggregat['dateien_union'])}",
        "",
    ]

    # Plan aus .werkstatt/plan.md.
    plan_text = _lese_plan(state)
    if plan_text:
        zeilen.append("=== PLAN (plan.md) ===")
        zeilen.append(plan_text.rstrip())
        zeilen.append("")

    start = state.phase_start_head or "HEAD"
    stat = _git_diff_phase(state.project_dir, start, "--stat")
    if stat.strip():
        zeilen.append(f"=== DIFF-STATISTIK ({start}..HEAD) ===")
        zeilen.append(stat.rstrip())
        zeilen.append("")

    # Top-3-Dateien nach Zeilenzahl als Voll-Diff.
    if aggregat["dateien_union"]:
        def _zeilen(pfad: str) -> int:
            numstat = _git_diff_phase(
                state.project_dir, start,
                "--numstat", "--", pfad)
            teile = numstat.split()
            try:
                return int(teile[0]) + int(teile[1])
            except (ValueError, IndexError):
                return 0

        top3 = sorted(
            aggregat["dateien_union"],
            key=_zeilen, reverse=True)[:3]
        for pfad in top3:
            voll = _git_diff_phase(
                state.project_dir, start, "--", pfad)
            if voll.strip():
                zeilen.append(f"=== VOLL-DIFF: {pfad} ===")
                zeilen.append(voll.rstrip()[:6000])
                zeilen.append("")

    # basis_gate_test_results (W23-Formatierer).
    test_block = _format_basis_gate_test_results(
        state.basis_gate_test_results)
    if test_block:
        zeilen.append("=== TEST-ERGEBNISSE (Letzter Suite-Lauf) ===")
        zeilen.append(test_block.rstrip())

    return "\n".join(zeilen)


def _format_basis_gate_test_results(
        results: list[dict[str, Any]],
) -> str:
    """W23 (2026-10-17): strukturiert basis_gate_test_results
    fuer den Commit-Review-Prompt.

    Liefert einen Block pro Aufruf: scope, exit_code,
    klassifizierung, failed_count, passed_count,
    failed_test_ids.
    """
    if not results:
        return ""
    teile: list[str] = []
    for tr in results:
        teile.append(
            f"--- {tr.get('scope', '?')} ---\n"
            f"  exit_code: {tr.get('exit_code', '?')}\n"
            f"  klassifizierung: "
            f"{tr.get('klassifizierung', '?')}\n"
            f"  failed: {tr.get('failed_count', '?')}, "
            f"passed: {tr.get('passed_count', '?')}\n"
            f"  failed_test_ids: "
            f"{tr.get('failed_test_ids', [])}\n"
        )
    return "\n".join(teile)


def _build_commit_input(
        state: RunState,
        diff_name_only: str,
        w11_unterblock_kontext: str,
        auflagen_text: str,
) -> str:
    """W23 (2026-10-17): baut den Commit-Review-Prompt.

    Ausgelagert aus run_pipeline, damit testbar und
    wartbar.

    A2-Aenderung: nach Apply ist der GEMESSENER INHALT
    (NACH Apply, verbindlich) = mess_protokoll_nach_apply.
    VOR Apply = historisch. Warnung bei veraltet.
    A4: Grenzfall nach_apply leer -> VOR verbindlich,
    Warnung + Hinweis.
    TEST-ERGEBNISSE-Block (basis_gate_test_results).
    """
    # A2/A4: Verfuegbarkeit pruefen.
    # W52b-D: strukturierte Nach-Apply-Messungen haben Vorrang.
    _nach_inhalt = _mess_inhalt_nach_apply(state)
    _nach_apply_ok = bool(_nach_inhalt)
    _veraltet = state.mess_protokoll_veraltet
    # Warnung.
    if _veraltet:
        _warnung = (
            "!!! ACHTUNG: Code-Patches wurden angewendet.\n"
            "!!! Der GEMESSENER INHALT (NACH Apply) ist\n"
            "!!! verbindlich. Der VOR-Stand steht als\n"
            "!!! historischer Kontext.\n\n")
    else:
        _warnung = ""
    # GEMESSENER INHALT (NACH oder VOR).
    if _veraltet and _nach_apply_ok:
        _mess_block = (
            "GEMESSENER INHALT (NACH Apply, verbindlich, "
            "gewinnt gegen ZIELDATEIEN):\n"
            f"{_nach_inhalt}\n\n"
            "MESS-INDEX (VOR Apply, historisch):\n"
            f"{_mess_index_block(state)}\n\n")
    elif _veraltet and not _nach_apply_ok:
        # A4 (c): VOR verbindlich, Hinweis.
        _mess_block = (
            "MESS-INDEX (VOR Apply, verbindlich):\n"
            f"{_mess_index_block(state)}\n\n"
            "!!! WARNUNG: NACH-Apply-Stand leer.\n"
            "!!! Pruefe mess_protokoll_veraltet-Flag und\n"
            "!!! basis_protokoll_nach_apply.\n\n")
    else:
        _mess_block = (
            "MESS-INDEX (verbindlich):\n"
            f"{_mess_index_block(state)}\n\n")
    # BASIS-GATE (NACH Apply).
    if state.basis_protokoll_nach_apply:
        _basis_nach = (
            "BASIS-GATE (NACH Apply):\n"
            f"{state.basis_protokoll_nach_apply}\n\n")
    else:
        _basis_nach = ""
    # TEST-ERGEBNISSE-Block.
    _test_results = _format_basis_gate_test_results(
        state.basis_gate_test_results)
    if _test_results:
        _test_block = (
            "TEST-ERGEBNISSE (NACH Apply):\n"
            f"{_test_results}\n\n")
    else:
        _test_block = ""
    return (
        _PHASE_HEADER_COMMIT_REVIEW
        + f"PHASEN-MODUS: "
        f"{'aktiv' if state.phase_aktiv else 'inaktiv'}\n"
        + w11_unterblock_kontext
        + "\n"
        + "CODE-GO ist erteilt. Pruefe das Commit-Paket.\n\n"
        + "=== COMMIT-MESSAGE (vollstaendig) ===\n"
        + f"{state.commit_paket.get('message', '')}\n"
        + "=== /COMMIT-MESSAGE ===\n\n"
        + "BETROFFENE DATEIEN:\n"
        + "\n".join(
            f"  - {d}"
            for d in state.commit_paket.get("dateien", []))
        + "\n\n"
        + f"GIT DIFF --NAME-ONLY HEAD:\n{diff_name_only}\n\n"
        + format_messwerte_block(collect_messwerte(state))
        + "\n\n"
        + _warnung
        + _mess_block
        + _basis_nach
        + _test_block
        + "CODE-PATCHES (angewendet):\n"
        + format_code_patches_fuer_commit(state.code_patches)
        + "\n\n"
        + f"AUFLAGEN AUS DIESER RUNDE:\n{auflagen_text}\n\n"
        + "Antworte mit COMMIT-GO, COMMIT-NO-GO oder "
        "COMMIT-ESKALATION."
    )


def _build_judge_input(state: RunState) -> str:
    """W28b2: baut den Judge-User-Content.

    Nur: contract.md, mess_nach.txt,
    basis_gate_test_results.
    NICHT: code_entwurf, mess_protokoll, basis_protokoll,
    commit_message, git_diff.
    """
    if not (0 <= state.phase_aktueller_index
            < len(state.phase_unterbloecke)):
        return (
            "=== KEIN AKTIVER UNTERBLOCK ===\n"
            "Der Phasen-Index ist ungueltig. "
            "ESKALATION an den Menschen.")
    uid = state.phase_unterbloecke[
        state.phase_aktueller_index].get("id", "?")
    contract = _lese_contract(state, uid)
    if not contract:
        contract = "(kein Contract vorhanden)"
    # W52b-D: aus strukturierten Nach-Apply-Messungen.
    mess_nach = _mess_inhalt_nach_apply(state)
    if not mess_nach:
        mess_nach = "(keine Messung nach Apply)"
    tests = _format_basis_gate_test_results(
        state.basis_gate_test_results)
    if not tests:
        tests = "(keine Test-Ergebnisse)"
    # W44 (2026-10-17): Judge-Prompt-Groesse
    # begrenzen. Ohne Begrenzung antwortet der
    # Judge bei >8000 Zeichen leer (raw_len=0,
    # kein Timeout). Ziel: Gesamt < 8000 Zeichen
    # (~2000 Token Budget).
    _W44_CONTRACT_MAX = 2000
    _W44_MESS_MAX = 4000
    _W44_TESTS_MAX = 1500

    def _w44_kuerzen(text: str, max_len: int) -> str:
        if len(text) <= max_len:
            return text
        return (
            text[:max_len]
            + f"\n[... GEKUERZT. {len(text) - max_len} "
            f"weitere Zeichen. ...]")

    contract = _w44_kuerzen(contract, _W44_CONTRACT_MAX)
    mess_nach = _w44_kuerzen(mess_nach, _W44_MESS_MAX)
    tests = _w44_kuerzen(tests, _W44_TESTS_MAX)
    return (
        f"=== CONTRACT ({uid}) ===\n"
        f"{contract}\n\n"
        f"=== GEMESSENER INHALT (nach Apply) ===\n"
        f"{mess_nach}\n\n"
        f"=== TEST-ERGEBNISSE ===\n"
        f"{tests}\n\n"
        "Bewerte. Erste Zeile: GO, NO_GO oder ESKALATION.\n"
        "Bei NO_GO: konkrete Problem-Liste (max 5 Punkte).")


def format_code_patches_fuer_commit(
        patches: list[dict[str, str]]) -> str:
    """Auflage 2191-R2: formatiert CODE-PATCHES fuer commit_input.

    Nur pfad und anker. Kein ersatz (Reviewer-Begruendung P1:
    ersatz ist nicht Pruefgegenstand in Phase 2, steht in
    Commit-Message und git diff).

    Format:
      PATCH <n> (pfad):
      anker:
      <anker>
      ---
    """
    if not patches:
        return "(keine)"
    bloecke: list[str] = []
    for i, p in enumerate(patches, start=1):
        pfad = p.get("pfad", "")
        # GOLD 2026-10-30: akzeptiere beide Patch-Formate.
        # Aktiv ist old_string/new_string (loop._apply_patches_with_hooks).
        # anker/ersatz kommt aus Legacy-Aufrufern.
        anker = p.get("old_string") or p.get("anker", "")
        bloecke.append(
            f"PATCH {i} ({pfad}):\n"
            f"anker:\n{anker}\n"
            "---"
        )
    return "\n".join(bloecke)




# Befund BV (2026-10-19): Abhaengigkeiten aus B-1-Messung.
# Gehoeren zum Commit/Judge-Input-Cluster.

def _git_diff_phase(
    project_dir: Path,
    start: str,
    *args: str,
) -> str:
    """W29b: git diff <start>..HEAD <args>.

    Duenne Huelle um subprocess.run, damit
    _build_phase_judge_input nicht mehrfach
    das Env-/Timeout-Muster kopiert.
    Rueckgabe: stdout (leer bei Fehler).
    """
    try:
        res = subprocess.run(
            ("git", "diff", f"{start}..HEAD") + args,
            cwd=str(project_dir),
            capture_output=True, text=True,
            timeout=30, check=False,
            env=subprocess_env(),
        )
    except (subprocess.TimeoutExpired, OSError):
        return ""
    if res.returncode != 0:
        return ""
    return res.stdout


def _plan_pfad(state: RunState) -> Path:
    """W26: Pfad zu .werkstatt/plan.md im Ziel-Projekt."""
    return state.project_dir / ".werkstatt" / "plan.md"


def _lese_plan(state: RunState) -> str:
    """W26: liest .werkstatt/plan.md.

    Liefert "" wenn nicht vorhanden.
    """
    plan_pfad = _plan_pfad(state)
    if not plan_pfad.exists():
        return ""
    try:
        return plan_pfad.read_text(encoding="utf-8")
    except OSError:
        return ""


def _contract_pfad(state: RunState, uid: str) -> Path:
    """W27: Pfad zu .werkstatt/contracts/<uid>.md."""
    return (state.project_dir / ".werkstatt"
            / "contracts" / f"{uid}.md")


def _lese_contract(state: RunState, uid: str) -> str:
    """W27: liest einen Contract.

    Liefert "" wenn nicht vorhanden.
    """
    pfad = _contract_pfad(state, uid)
    if not pfad.exists():
        return ""
    try:
        return pfad.read_text(encoding="utf-8")
    except OSError:
        return ""


_PHASE_HEADER_COMMIT_REVIEW = (
    "## PHASE: COMMIT-REVIEW (Phase 2)\n")


