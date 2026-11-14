"""OP-385: Scout-Report als einzige Architect-Kontext-Quelle.

Verbotenes Verhalten (Live 2026-11-09):
- Architect-Prompt enthaelt parallel: AST-Block (aus
  explorer_ctx.key_files), explorer_findings (1.020 Findings),
  scout_api_auszug (doppelt), measured_files (nochmal key_files).
- Folge: 100.000 user_len truncation, 35.550 prompt-Tokens Live.
- Scout ist der Filter-Agent — seine Verengung wird durch die
  parallelen Explorer-Kanaele aufgehoben.

Fix: Wenn state.scout_auftrag gesetzt, ist das die einzige Quelle.
Explorer-Blöcke werden in den Fallback-Pfad verschoben (greifen
nur bei leerem scout_auftrag — alte Runs, Scout-Fail).
"""
from __future__ import annotations

from types import SimpleNamespace


def _mk_state(scout_auftrag=None, explorer_findings=None,
              api_index_cache=None):
    return SimpleNamespace(
        scout_auftrag=scout_auftrag or {},
        explorer_findings=explorer_findings or {},
        scout_api_auszug={"x.py": ["f"]} if scout_auftrag else {},
        api_index_cache=api_index_cache or {},
        docs={},
        tasks=[],
    )


def test_scout_auftrag_ist_einzige_quelle():
    """Mit scout_auftrag: <scout_auftrag> im Prompt, KEIN <explorer_findings>."""
    from werkstatt.architect import _planner_system

    state = _mk_state(
        scout_auftrag={
            "auftrag_prosa": "Ersetze A durch B in auth.py",
            "api_auszug": {"werkstatt/web/auth.py": ["pruefe_ref"]},
            "risiken": ["ws.py hat Fallback"],
            "bereits_erfuellt": False,
        },
        explorer_findings={"pytest_laufzeit_s": 12, "ruff_befunde": ["F401"]},
    )
    prompt = _planner_system("Test-Aufgabe", None, state)

    assert "<scout_auftrag>" in prompt, (
        "AK b: scout_auftrag-Block MUSS im Prompt sein"
    )
    assert "</scout_auftrag>" in prompt
    assert "Ersetze A durch B in auth.py" in prompt
    assert "<explorer_findings>" not in prompt, (
        "AK b: explorer_findings darf bei gesetztem scout_auftrag "
        "NICHT mehr im Prompt sein"
    )


def test_fallback_bei_leerem_scout_auftrag():
    """Ohne scout_auftrag: altes Verhalten mit <explorer_findings>."""
    from werkstatt.architect import _planner_system

    state = _mk_state(
        scout_auftrag={},
        explorer_findings={"pytest_laufzeit_s": 12, "ruff_befunde": ["F401"]},
    )
    prompt = _planner_system("Test-Aufgabe", None, state)

    assert "<explorer_findings>" in prompt, (
        "AK c: Fallback bei leerem scout_auftrag MUSS explorer_findings "
        "wieder reinnehmen (alte Runs brechen sonst)"
    )
    assert "<scout_auftrag>" not in prompt


def test_bereits_erfuellt_hinweis_im_scout_block():
    """Wenn bereits_erfuellt=True: Hinweis im scout_auftrag-Block."""
    from werkstatt.architect import _planner_system

    state = _mk_state(
        scout_auftrag={
            "auftrag_prosa": "Auftrag X",
            "api_auszug": {},
            "risiken": [],
            "bereits_erfuellt": True,
        },
    )
    prompt = _planner_system("Test-Aufgabe", None, state)

    assert "<scout_auftrag>" in prompt
    assert "bereits erfuellt" in prompt.lower(), (
        "bereits_erfuellt-Hinweis MUSS im scout_auftrag-Block stehen"
    )

def test_run_architect_nutzt_scout_nicht_doppelten_user_context(
    monkeypatch, tmp_path,
):
    """OP-385: Scout-Auftrag wird einmal im Systemprompt uebergeben."""
    from werkstatt import architect

    state = SimpleNamespace(
        project_dir=tmp_path,
        project_name="demo",
        api_index_cache={"already_built": True},
        docs={},
        scout_auftrag={
            "auftrag_prosa": "Ersetze A durch B in auth.py.",
            "api_auszug": {"auth.py": ["verify_token"]},
            "risiken": ["Cookie-Fallback bleibt kompatibel"],
            "api_widersprueche": [{
                "datei": "auth.py",
                "symbol": "verify_token",
                "art": "fehlt",
                "gefunden_in": [],
            }],
            "bereits_erfuellt": False,
        },
        scout_api_auszug={},
    )
    captured = {}

    class _Reply:
        ok = True
        content = "Architect-Plan. " * 8

    def _ask_llm(_key, system, user, **_kwargs):
        captured["system"] = system
        captured["user"] = user
        return _Reply()

    monkeypatch.setattr(architect, "_with_spinner", lambda _label, call: call())
    monkeypatch.setattr(architect, "ask_llm", _ask_llm)
    monkeypatch.setattr(architect, "audit", lambda *_args, **_kwargs: None)

    assert architect.run_architect(
        state, "Aufgabe", "Explorer-Rohdaten-Duplikat", "key", None,
    )
    assert "<scout_auftrag>" in captured["system"]
    assert "Ersetze A durch B in auth.py." in captured["system"]
    assert "Deterministischer API-Abgleich" in captured["system"]
    assert '"symbol": "verify_token"' in captured["system"]
    assert captured["user"] == ""
    assert "Explorer-Rohdaten-Duplikat" not in captured["system"]


def test_run_architect_faellt_bei_unvollstaendigem_scout_fail_closed(
    monkeypatch, tmp_path,
):
    """OP-385: Report ohne Architect-Auftrag darf den Fallback nicht oeffnen."""
    from types import SimpleNamespace

    from werkstatt import architect

    state = SimpleNamespace(
        project_dir=tmp_path,
        project_name="demo",
        api_index_cache={"already_built": True},
        docs={},
        scout_auftrag={"risiken": ["Risiko ohne Auftrag"]},
    )
    calls = []
    monkeypatch.setattr(architect, "ask_llm", lambda *a, **k: calls.append(a))
    monkeypatch.setattr(architect, "audit", lambda *_args, **_kwargs: None)

    assert not architect.run_architect(
        state, "Aufgabe", "Explorer-Rohdaten", "key", None,
    )
    assert calls == []

def test_run_architect_uebergibt_laufkontext_ohne_explorer_duplikat(
    monkeypatch, tmp_path,
):
    """OP-396: Historie bleibt erhalten, Explorer-Rohtext wird nicht dupliziert."""
    from types import SimpleNamespace

    from werkstatt import architect

    state = SimpleNamespace(
        project_dir=tmp_path,
        project_name="demo",
        api_index_cache={"already_built": True},
        docs={},
        scout_auftrag={
            "auftrag_prosa": "Fuege eine validierte Funktion hinzu.",
            "api_auszug": {},
            "risiken": [],
            "bereits_erfuellt": False,
        },
        architect_execution_context=(
            "## PROJEKT-FORTSCHRITT\nOP-123 wurde bereits verifiziert."
        ),
    )
    captured = {}

    class _Reply:
        ok = True
        content = "Architect-Plan. " * 8

    def _ask_llm(_key, _system, user, **_kwargs):
        captured["user"] = user
        return _Reply()

    monkeypatch.setattr(architect, "_with_spinner", lambda _label, call: call())
    monkeypatch.setattr(architect, "ask_llm", _ask_llm)
    monkeypatch.setattr(architect, "audit", lambda *_args, **_kwargs: None)

    assert architect.run_architect(
        state, "Aufgabe", "Explorer-Rohdaten-Duplikat", "key", None,
    )
    assert "PROJEKT-FORTSCHRITT" in captured["user"]
    assert "OP-123 wurde bereits verifiziert." in captured["user"]
    assert "Explorer-Rohdaten-Duplikat" not in captured["user"]
