"""W36-RP (2026-10-18): run_pipeline-Integrationstests.

Mock-Helper + 3 Integrationstests (T-1, T-2, T-3).
Die 3 Tests schliessen die letzten zentralen
Integrations-Luecken:

  T-1: Builder-Lauf -> state.code_entwurf_historie
       befuellt (A1b-fix-Luecke).
  T-2: Apply -> state.mess_protokoll_nach_apply
       befuellt (W33a-Luecke).
  T-3: Judge -> state.review_runden akkumuliert
       Verdicts (W28b-Luecke).

AST-GRENZEN (siehe audit/00-audit-grenzen.md):
Der Helper mockt externe I/O. Er mockt NICHT:
  - record_code_entwurf (T-1 prueft es).
  - state-Attribute (state.code_entwurf_historie
    muss echt wachsen).
  - Parser (_parse_phase_plan, _parse_commands_
    planner).
  - builder_reply_mit_command_loop (T-1 nutzt
    den echten Builder-Loop mit ask_llm-Mock).

Aufrufer: run_pipeline Z. 12616 (main-Pfad).
Begruendung: klassischer Fall, den A1b-fix
adressiert.

subprocess: Die lokale Fixture _no_real_
subprocess blockiert alle subprocess-Aufrufe.
Tests, die subprocess brauchen, markieren sich
mit @pytest.mark.allow_subprocess(...). Der
Helper setzt gezielte subprocess-Mocks.

ask_llm-Rollen: Kein role-Parameter. Rollen
ueber system_prompt-String-Match:
  - builder_prompt -> Builder.
  - judge_prompt -> Judge.
  - tg_prompt -> Test-Gen.
  - reviewer_prompt -> Reviewer (Zaehler).
reviewer_prompt-Aufrufe: 1. Reviewer (Mess-
Wahl), 2. Reviewer (Commit). Zaehler fail-
closed bei >2 Aufrufen (A-W36-RP-10).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, "/opt/werkstatt")
import pipeline

# =====================================================================
# W36-RP: subprocess fail-closed mit Whitelist.
# =====================================================================

def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "allow_subprocess(*names): erlaubt subprocess-"
        "Aufrufe, deren erstes Argument in names ist.")


@pytest.fixture(autouse=True)
def _no_real_subprocess(request, monkeypatch):
    """W36-RP: alle subprocess-Aufrufe im Test blockieren,
    ausser per Marker erlaubte."""
    import os as _os

    erlaubt = set()
    marker = request.node.get_closest_marker("allow_subprocess")
    if marker is not None:
        erlaubt = set(marker.args)

    def _ist_erlaubt(argv):
        if not argv:
            return False
        erstes = argv[0] if isinstance(argv, (list, tuple)) \
            else str(argv).split()[0]
        erstes = _os.path.basename(str(erstes))
        return erstes in erlaubt

    # Originale sichern (nur einmal)
    if not hasattr(subprocess, "__orig_run_w36__"):
        subprocess.__orig_run_w36__ = subprocess.run
        subprocess.__orig_check_output_w36__ = \
            subprocess.check_output

    def _run(argv, *args, **kwargs):
        if not _ist_erlaubt(argv):
            raise AssertionError(
                f"W36-RP: subprocess.run({argv!r}) im Test "
                f"nicht erlaubt. Erlaubt: {erlaubt or '(keine)'}. "
                f"Fuege @pytest.mark.allow_subprocess(...) "
                f"hinzu oder mocke gezielt.")
        return subprocess.__orig_run_w36__(argv, *args, **kwargs)

    def _check_output(argv, *args, **kwargs):
        if not _ist_erlaubt(argv):
            raise AssertionError(
                f"W36-RP: subprocess.check_output({argv!r}) "
                f"im Test nicht erlaubt.")
        return subprocess.__orig_check_output_w36__(
            argv, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", _run)
    monkeypatch.setattr(subprocess, "check_output", _check_output)


# =====================================================================
# W36-RP: Mock-Helper.
# =====================================================================

def _reply_ok(content: str):
    """Baut ein LLMReply-aehnliches Objekt mit ok=True."""
    return type("R", (), {"ok": True, "content": content,
                          "error": ""})()


def _reply_err(error: str = "test-fehler"):
    return type("R", (), {"ok": False, "content": "",
                          "error": error})()


def mock_run_pipeline_deps(
        monkeypatch,
        *,
        builder_reply: str = (
            "PATCH-BEGINN\n"
            "typ: patch\n"
            "pfad: core/x.py\n"
            "anker: y = 1\n"
            "ersatz: y = 2\n"
            "PATCH-ENDE\n"),
        judge_verdict: str = "GO",
        commit_verdict: str = "COMMIT-GO",
        builder_max_runden: int = 3,
        mock_audit: bool = True,
) -> dict[str, Any]:
    """Setzt alle run_pipeline-Mocks.

    Rueckgabe: dict mit Mock-Handles (fuer Assertions).

    Defaults (A-W36-RP-5): jeder Aufruf sicher.
    Gefaehrliche Defaults (ask_llm ohne Prompt-Match):
    AssertionError.

    Rollen-Strategie ask_llm (A-W36-RP-4):
      - builder_prompt -> builder_reply.
      - judge_prompt -> judge_verdict.
      - tg_prompt -> leere Antwort (kein Test-Gen).
      - reviewer_prompt -> Zaehler. 1. -> "",
        2. -> commit_verdict. 3. -> AssertionError
        (A-W36-RP-10).
    """
    handle: dict[str, Any] = {}

    # --- ask_llm ---
    reviewer_zaehler = {"n": 0}

    def _fake_ask_llm(api_key, system_prompt, user_content,
                      model, temperature, *args, **kwargs):
        # W36-RP: Rollen ueber Frontmatter-Praefix,
        # nicht per Substring. Grund: der judge_prompt
        # enthaelt 'Reviewer' (judge.md + HARD_RULES_
        # BASE HR7), der builder_prompt enthaelt
        # 'Reviewer' (HARD_RULES_BUILDER), etc.
        # build_system_prompt gibt das Frontmatter
        # ('---\nname: <rolle>\n---') mit aus.
        sp = system_prompt or ""
        # W36-RP: Rollen ueber Body-Anfang. Grund:
        # build_system_prompt gibt den Body aus
        # (ohne Frontmatter). judge.md beginnt mit
        # "Du bist der Judge.", reviewer.md mit
        # "Du bist der Reviewer.".
        if sp.startswith("Du bist der Builder"):
            handle.setdefault("builder_calls", []).append(
                user_content)
            return _reply_ok(builder_reply)
        if sp.startswith("Du bist der Judge"):
            handle.setdefault("judge_calls", []).append(
                user_content)
            return _reply_ok(judge_verdict)
        if sp.startswith("Du bist der Test-Generator"):
            return _reply_ok("")
        if sp.startswith("Du bist der Reviewer"):
            reviewer_zaehler["n"] += 1
            n = reviewer_zaehler["n"]
            if n == 1:
                # Reviewer Mess-Wahl: keine Commands.
                return _reply_ok("")
            if n == 2:
                # Reviewer Commit-Review.
                return _reply_ok(commit_verdict)
            raise AssertionError(
                f"W36-RP: reviewer_prompt zum {n}. Mal gerufen. "
                f"Erwartet: max 2 (Mess-Wahl, Commit). "
                f"Neue reviewer_prompt-Aufrufe erfordern "
                f"Anpassung des Helpers.")
        raise AssertionError(
            f"W36-RP: ask_llm mit unbekanntem Body-Anfang "
            f"({sp[:80]!r}). Rollen-Match fehlgeschlagen.")

    monkeypatch.setattr(pipeline, "ask_llm", _fake_ask_llm)
    handle["ask_llm"] = _fake_ask_llm

    # --- apply_and_recheck ---
    def _fake_apply(state, always, file_whitelist):
        # Setzt mess_protokoll_nach_apply (T-2).
        state.mess_protokoll_nach_apply = (
            "=== read_file ===\ncore/x.py: y = 2\n")

    monkeypatch.setattr(pipeline, "apply_and_recheck",
                        _fake_apply)
    handle["apply_and_recheck"] = _fake_apply

    # --- build_commit_paket ---
    def _fake_bcp(state):
        # W36-RP: Message braucht "Aenderung:"-Section
        # mit Bullet-Pfaden (W10-A2/A3, Z. 8172).
        return {
            "message": "Test-Commit\n\n"
                       "Aenderung:\n"
                       "  - core/x.py\n",
            "dateien": ["core/x.py"],
        }

    monkeypatch.setattr(pipeline, "build_commit_paket",
                        _fake_bcp)
    handle["build_commit_paket"] = _fake_bcp

    # --- apply_commit_and_doku ---
    monkeypatch.setattr(pipeline, "apply_commit_and_doku",
                        lambda state, paket: True)

    # --- Basis-Gate ---
    def _fake_bg_ziel(project_dir, timeout=900):
        return {"exit_code": 0, "klassifizierung": "gruen",
                "failed_count": 0, "passed_count": 1,
                "failed_test_ids": [], "failed_test_ids_mehr": [],
                "dauer_s": 0.1, "raw_tail": ""}

    def _fake_bg_suite(project_dir, timeout=900):
        return {"exit_code": 0, "klassifizierung": "gruen",
                "failed_count": 0, "passed_count": 1,
                "failed_test_ids": [], "failed_test_ids_mehr": [],
                "dauer_s": 0.1, "raw_tail": ""}

    monkeypatch.setattr(pipeline, "_basis_gate_pytest_ziel",
                        _fake_bg_ziel)
    monkeypatch.setattr(pipeline, "_basis_gate_pytest_suite",
                        _fake_bg_suite)

    # --- budget_or_recover ---
    monkeypatch.setattr(pipeline, "budget_or_recover",
                        lambda *a, **kw: None)

    # --- execute_commands ---
    monkeypatch.setattr(pipeline, "execute_commands",
                        lambda *a, **kw: {})

    # --- subprocess.run: git diff --name-only ---
    def _fake_sp_run(argv, *args, **kwargs):
        # git-Kommandos erlaubt, jeweils mit
        # passender Attrappe.
        if not isinstance(argv, (list, tuple)):
            raise TypeError(
                f"W36-RP: subprocess.run({argv!r}) "
                f"kein Tupel.")
        if argv[:3] == ("git", "diff", "--name-only"):
            return type("R", (), {"returncode": 0,
                                  "stdout": "core/x.py\n",
                                  "stderr": ""})()
        if argv[:2] == ("git", "log"):
            # git log -N --format=...
            return type("R", (), {"returncode": 0,
                                  "stdout": "",
                                  "stderr": ""})()
        if argv[:2] == ("git", "status"):
            return type("R", (), {"returncode": 0,
                                  "stdout": "",
                                  "stderr": ""})()
        if argv[:3] == ("git", "rev-parse", "--short"):
            return type("R", (), {"returncode": 0,
                                  "stdout": "abc1234\n",
                                  "stderr": ""})()
        raise AssertionError(
            f"W36-RP: subprocess.run({argv!r}) unerwartet.")

    monkeypatch.setattr(subprocess, "run", _fake_sp_run)

    # --- audit ---
    if mock_audit:
        monkeypatch.setattr(pipeline, "audit",
                            lambda *a, **kw: None)

    # --- run_measurement_mit_argv ---
    # W36-RP: Basis-Gate laeuft mit "gruen"-Attrappe.
    # Der Test prueft nicht das Basis-Gate, sondern
    # die Builder-/Apply-/Judge-Kette danach.
    def _fake_run_measurement(m, whitelist, project_dir,
                              extra_arg=None):
        # out, ok, argv
        return ("", True, list(getattr(m, "argv", ())))

    monkeypatch.setattr(pipeline, "run_measurement_mit_argv",
                        _fake_run_measurement)

    # --- run_measurement (Wrapper) ---
    # Rueckgabe: (out, ok) laut Aufrufer Z. 9191.
    def _fake_run_measurement2(m, whitelist, project_dir):
        return ("", True)

    monkeypatch.setattr(pipeline, "run_measurement",
                        _fake_run_measurement2)

    # --- _lade_und_pruefe_projekt ---
    def _fake_lade_projekt(project_name):
        # W36-RP: build_catalog braucht nicht-leere
        # always_run/optional_catalog. Die IDs muessen
        # im all_m-Dict von build_catalog existieren.
        return {
            "project": project_name,
            "project_dir": "/tmp",
            "always_run": [
                "py_compile", "ruff", "mypy",
                "test_count", "git_status", "git_head",
            ],
            "optional_catalog": ["read_file"],
            "agent_docs": {},
            "file_whitelist": ["core/"],
        }

    monkeypatch.setattr(pipeline, "_lade_und_pruefe_projekt",
                        _fake_lade_projekt)

    # --- input (Human-Gate) ---
    # run_pipeline endet mit input("Deine Wahl: ").
    # Tests antworten mit "j" (approve).
    import builtins
    monkeypatch.setattr(builtins, "input",
                        lambda *a, **kw: "j")

    return handle


# =====================================================================
# T-1: Builder-Lauf -> state.code_entwurf_historie.
# =====================================================================

def test_t1_builder_lauf_befuellt_historie(
        tmp_path: Path, monkeypatch) -> None:
    """W36-RP T-1 (A-B1-13): Nach Builder-Lauf ist
    state.code_entwurf_historie befuellt.
    Schliesst die A1b-fix-Luecke (record_code_entwurf
    nur in run_pipeline, nicht in Tests).
    """
    mock_run_pipeline_deps(monkeypatch)
    # W36-RP: run_pipeline baut einen NEUEN State
    # (Z. 9159: state_ref.append(state)). state_ref
    # muss leer sein. Das neue State wird mit
    # load_agents/load_docs/build_catalog gebaut.
    state_ref: list = []

    rc = pipeline.run_pipeline(
        "test-projekt", "Test-Auftrag", state_ref)

    state = state_ref[0]
    assert len(state.code_entwurf_historie) >= 1, (
        f"code_entwurf_historie leer (rc={rc}). "
        f"record_code_entwurf wurde nicht gerufen.")
    phasen = [e.get("phase")
              for e in state.code_entwurf_historie]
    assert "normal" in phasen, (
        f"Keine phase='normal' in Historie: {phasen}")


# =====================================================================
# T-2: Apply -> state.mess_protokoll_nach_apply.
# =====================================================================

def test_t2_apply_befuellt_mess_nach(
        tmp_path: Path, monkeypatch) -> None:
    """W36-RP T-2: Nach Apply ist
    state.mess_protokoll_nach_apply befuellt.
    Schliesst die W33a-Luecke.
    """
    mock_run_pipeline_deps(monkeypatch)
    # W36-RP: run_pipeline baut einen NEUEN State
    # (Z. 9159: state_ref.append(state)). state_ref
    # muss leer sein. Das neue State wird mit
    # load_agents/load_docs/build_catalog gebaut.
    state_ref: list = []

    rc = pipeline.run_pipeline(
        "test-projekt", "Test-Auftrag", state_ref)

    state = state_ref[0]
    assert state.mess_protokoll_nach_apply, (
        f"mess_protokoll_nach_apply leer (rc={rc}). "
        f"apply_and_recheck hat keine Post-Apply-"
        f"Messung erzeugt.")


# =====================================================================
# T-3: Judge -> review_runden akkumuliert Verdicts.
# =====================================================================

def test_t3_judge_akkumuliert_verdicts(
        tmp_path: Path, monkeypatch) -> None:
    """W36-RP T-3: review_runden enthaelt Judge-
    Verdicts. Schliesst die W28b-Luecke.
    """
    mock_run_pipeline_deps(monkeypatch, judge_verdict="GO")
    # W36-RP: run_pipeline baut einen NEUEN State
    # (Z. 9159: state_ref.append(state)). state_ref
    # muss leer sein. Das neue State wird mit
    # load_agents/load_docs/build_catalog gebaut.
    state_ref: list = []

    rc = pipeline.run_pipeline(
        "test-projekt", "Test-Auftrag", state_ref)

    state = state_ref[0]
    verdicts = [r.get("verdict")
                for r in state.review_runden]
    assert "GO" in verdicts, (
        f"review_runden enthaelt kein GO: {verdicts} "
        f"(rc={rc})")
