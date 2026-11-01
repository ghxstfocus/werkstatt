"""OP-062a: Redaction darf Code-Pruef-LLMs nicht anonymisieren.

Der Phase-End-Reviewer und der Task-Reviewer muessen echte IPs sehen,
sonst koennen sie Code semantisch nicht pruefen. Live-Beleg 15:16
OP-002b3: Phase-Reviewer sieht '[IPV4]' und '[IPV4]' und meldet
"Test ruft zweimal dieselbe IP auf", obwohl der Test gruen ist
(1.1.1.1 und 2.2.2.2).

Option A: ask_llm bekommt redact-Parameter. Builder, Reviewer und
Phase-End-Review rufen mit redact=False. Planner/Architect/Scout
behalten redact=True (Default).

Datenschutz-Kontext: Private IPs (10.x, 192.168.x, 127.x) werden
bereits von der Redaction nicht angefasst (siehe test_redaction.py).
Oeffentliche IPs (1.1.1.1, 8.8.8.8) werden maskiert. Fuer Code-
Pruefung ist das falsch — der Reviewer braucht die echten Werte.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from werkstatt import agent as agent_mod


def _mk_reply(content: str = "{}"):
    from werkstatt.agent import LLMReply
    return LLMReply(ok=True, content=content, error="", model="test")


def test_ask_llm_redact_parameter_existiert() -> None:
    """Signatur muss redact-Parameter haben."""
    import inspect
    sig = inspect.signature(agent_mod.ask_llm)
    assert "redact" in sig.parameters, (
        f"ask_llm hat keinen redact-Parameter: {sig}"
    )
    assert sig.parameters["redact"].default is True, (
        "Default muss True sein (Datenschutz-konservativ)"
    )


def test_ask_llm_redact_false_laesst_oeffentliche_ip_durch(
    monkeypatch
) -> None:
    """Mit redact=False: 1.1.1.1 bleibt im Payload."""
    _captured = {}

    class _FakeResp:
        status_code = 200

        def json(self):
            return {
                "choices": [{"message": {"content": "ok"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            }

    def _fake_post(url, *, headers=None, json=None, timeout=None, **kw):
        _captured["payload"] = json
        return _FakeResp()

    monkeypatch.setattr(agent_mod.requests, "post", _fake_post)
    monkeypatch.setattr(agent_mod, "_dump_prompt", lambda *a, **kw: None)

    agent_mod.ask_llm(
        "dummy-key",
        "system",
        "Test mit IP 1.1.1.1 und 2.2.2.2",
        model="deepseek-chat", temperature=0.0,
        redact=False,
    )
    msg = _captured["payload"]["messages"][1]["content"]
    assert "1.1.1.1" in msg, f"1.1.1.1 fehlt in {msg!r}"
    assert "2.2.2.2" in msg, f"2.2.2.2 fehlt in {msg!r}"
    assert "[IPV4]" not in msg, f"unerwartete Redaction: {msg!r}"


def test_ask_llm_redact_true_default_maskiert(
    monkeypatch
) -> None:
    """Default (redact=True): 1.1.1.1 wird zu [IPV4]."""
    _captured = {}

    class _FakeResp:
        status_code = 200

        def json(self):
            return {
                "choices": [{"message": {"content": "ok"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            }

    def _fake_post(url, *, headers=None, json=None, timeout=None, **kw):
        _captured["payload"] = json
        return _FakeResp()

    monkeypatch.setattr(agent_mod.requests, "post", _fake_post)
    monkeypatch.setattr(agent_mod, "_dump_prompt", lambda *a, **kw: None)

    agent_mod.ask_llm(
        "dummy-key",
        "system",
        "Test mit IP 1.1.1.1",
        model="deepseek-chat", temperature=0.0,
        # redact nicht gesetzt -> Default True
    )
    msg = _captured["payload"]["messages"][1]["content"]
    assert "[IPV4]" in msg, f"Redaction fehlt: {msg!r}"


def test_ask_llm_redact_false_private_ip_bleibt(
    monkeypatch
) -> None:
    """Mit redact=False bleiben auch private IPs (waren schon vorher)."""
    _captured = {}

    class _FakeResp:
        status_code = 200

        def json(self):
            return {
                "choices": [{"message": {"content": "ok"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            }

    def _fake_post(url, *, headers=None, json=None, timeout=None, **kw):
        _captured["payload"] = json
        return _FakeResp()

    monkeypatch.setattr(agent_mod.requests, "post", _fake_post)
    monkeypatch.setattr(agent_mod, "_dump_prompt", lambda *a, **kw: None)

    agent_mod.ask_llm(
        "dummy-key", "system",
        "Private IP 192.168.178.10",
        model="deepseek-chat", temperature=0.0,
        redact=False,
    )
    msg = _captured["payload"]["messages"][1]["content"]
    assert "192.168.178.10" in msg


def test_reviewer_ruft_mit_redact_false(
    tmp_path: Path, monkeypatch
) -> None:
    """Task-Reviewer: ask_llm mit redact=False."""
    _calls = []

    def _fake_ask(*args, **kwargs):
        _calls.append(kwargs)
        return _mk_reply('{"approved": true, "bugs": [], "summary": "ok"}')

    monkeypatch.setattr(
        "werkstatt.reviewer.ask_llm", _fake_ask,
    )

    from werkstatt.state import RunState
    from werkstatt.reviewer import run_reviewer

    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "x.py").write_text("x = 1\n")
    st = RunState(
        block_id="p", aufgabe="a", start_ts="", docs={}, agents={},
        always={}, optional={}, file_whitelist=[], api_key="dummy",
        budget={}, agent_docs={}, project_dir=tmp_path, project_name="p",
    )
    st.tasks = [{"id": "t1", "task_files": ["core/x.py"]}]
    st.aktuelle_task = st.tasks[0]
    st.patches = [{"file": "core/x.py", "action": "update"}]

    with patch("werkstatt.reviewer._get_git_diff",
               return_value="+ x = 2\n"):
        try:
            run_reviewer(st)
        except Exception:
            pass  # LLM-Parsing egal, wir pruefen den ask_llm-Call

    assert _calls, f"ask_llm nicht aufgerufen; calls={_calls}"
    assert _calls[0].get("redact") is False, (
        f"Task-Reviewer ruft nicht mit redact=False: {_calls[0]}"
    )
