import time

from werkstatt import agent


class _DummyResponse:
    status_code = 200

    def json(self):
        return {"choices": [{"message": {"content": "ok"}}]}


def test_heartbeat_bei_langem_call(capsys, monkeypatch):
    def fake_post(*args, **kwargs):
        time.sleep(1.5)
        return _DummyResponse()

    monkeypatch.setattr(agent.requests, "post", fake_post)

    agent.ask_llm(
        api_key="x",
        system_prompt="s",
        user_content="u",
        model="m",
        temperature=0.0,
        state=None,
    )

    out = capsys.readouterr().out
    assert sum(1 for line in out.splitlines() if "laeuft" in line) >= 1


def test_heartbeat_bei_schnellem_call(capsys, monkeypatch):
    def fake_post(*args, **kwargs):
        return _DummyResponse()

    monkeypatch.setattr(agent.requests, "post", fake_post)

    agent.ask_llm(
        api_key="x",
        system_prompt="s",
        user_content="u",
        model="m",
        temperature=0.0,
        state=None,
    )

    out = capsys.readouterr().out
    assert sum(1 for line in out.splitlines() if "laeuft" in line) <= 1


def test_heartbeat_stage_name_builder(capsys):
    thread, stop_event = agent._heartbeat_start("Builder")
    time.sleep(1.5)
    stop_event.set()
    thread.join(timeout=2.0)

    out = capsys.readouterr().out
    assert "Builder" in out
