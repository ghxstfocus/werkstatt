"""OP-381j: aggregate_live_feed Backend.

Verbotenes Verhalten:
- Steps nicht chronologisch sortiert (Log unlesbar)
- Aktiv-Step erscheint doppelt (in steps UND in aktiv)
- Naechster-Schritt-Heuristik fehlt (User sieht 'was kommt?')
- Run-Filter greift nicht (alte Runs mischen rein)
- Limit wirkt nicht (UI erschlaegt bei 200+ Events)
"""
from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest

from werkstatt import audit as _audit
from werkstatt import event_store as _es
from werkstatt import paths as _paths
from werkstatt import projection as _proj
from werkstatt.web import inspector


@pytest.fixture
def projektion(monkeypatch, tmp_path):
    monkeypatch.setattr(_paths, "werkstatt_home", lambda: tmp_path)
    monkeypatch.setattr(_audit, "_werkstatt_home", lambda: tmp_path)
    monkeypatch.setattr(_proj, "_werkstatt_home", lambda: tmp_path)
    monkeypatch.setattr(_es, "werkstatt_home", lambda: tmp_path)
    monkeypatch.setattr(inspector, "werkstatt_home", lambda: tmp_path)
    yield tmp_path


def _schreibe(tmp_path, events: list[dict]) -> None:
    d = tmp_path / "audit-logs"
    d.mkdir(exist_ok=True)
    with (d / "agent-pipeline-2026-11-09.jsonl").open("w", encoding="utf-8") as fh:
        for ev in events:
            fh.write(json.dumps(ev) + "\n")


def test_steps_chronologisch(projektion, tmp_path):
    """Steps sind aufsteigend sortiert (aelteste zuerst)."""
    jetzt = datetime.now(UTC)
    _schreibe(tmp_path, [
        {"kind": "loop_started", "run_id": "r1", "project": "werkstatt",
         "timestamp": (jetzt - timedelta(seconds=10)).isoformat(),
         "agent": "agent_pipeline"},
        {"kind": "explorer_result", "run_id": "r1", "project": "werkstatt",
         "timestamp": (jetzt - timedelta(seconds=5)).isoformat(),
         "agent": "explorer"},
        {"kind": "loop_failed", "run_id": "r1", "project": "werkstatt",
         "timestamp": jetzt.isoformat(), "agent": "agent_pipeline"},
    ])
    feed = inspector.aggregate_live_feed("werkstatt")
    steps = feed.get("steps") or []
    assert len(steps) == 3
    # kind-Reihenfolge
    assert steps[0]["kind"] == "loop_started"
    assert steps[1]["kind"] == "explorer_result"
    assert steps[2]["kind"] == "loop_failed"


def test_aktiv_bei_offenem_llm_call(projektion, tmp_path):
    """llm_call_start als letztes -> aktiv.rolle=architect."""
    jetzt = datetime.now(UTC)
    _schreibe(tmp_path, [
        {"kind": "loop_started", "run_id": "r1", "project": "werkstatt",
         "timestamp": (jetzt - timedelta(seconds=20)).isoformat(),
         "agent": "agent_pipeline"},
        {"kind": "llm_call_start", "run_id": "r1", "project": "werkstatt",
         "timestamp": (jetzt - timedelta(seconds=5)).isoformat(),
         "agent": "architect", "model": "deepseek-reasoner"},
    ])
    feed = inspector.aggregate_live_feed("werkstatt")
    assert feed["aktiv"].get("rolle") == "architect"
    assert feed["aktiv"].get("kind") == "llm_call_start"
    # Aktiv-Event NICHT in steps (doppelt vermeiden)
    kinds_in_steps = [s["kind"] for s in (feed.get("steps") or [])]
    assert "llm_call_start" not in kinds_in_steps


def test_naechster_aus_rolle(projektion, tmp_path):
    """aktiv=explorer -> naechster.rolle=scout."""
    jetzt = datetime.now(UTC)
    _schreibe(tmp_path, [
        {"kind": "llm_call_start", "run_id": "r1", "project": "werkstatt",
         "timestamp": (jetzt - timedelta(seconds=5)).isoformat(),
         "agent": "explorer"},
    ])
    feed = inspector.aggregate_live_feed("werkstatt")
    assert feed.get("naechster", {}).get("rolle") == "scout"


def test_limit(projektion, tmp_path):
    """40 Events, limit 10 -> 10 steps."""
    jetzt = datetime.now(UTC)
    events = []
    for i in range(40):
        events.append({
            "kind": f"event_{i}", "run_id": "r1", "project": "werkstatt",
            "timestamp": (jetzt - timedelta(seconds=40 - i)).isoformat(),
            "agent": "agent_pipeline",
        })
    _schreibe(tmp_path, events)
    feed = inspector.aggregate_live_feed("werkstatt", limit=10)
    assert len(feed.get("steps") or []) == 10


def test_run_filter(projektion, tmp_path):
    """Zwei Runs in einer Datei -> nur der letzte erscheint."""
    jetzt = datetime.now(UTC)
    _schreibe(tmp_path, [
        {"kind": "old_event", "run_id": "alt", "project": "werkstatt",
         "timestamp": (jetzt - timedelta(seconds=100)).isoformat(),
         "agent": "agent_pipeline"},
        {"kind": "loop_started", "run_id": "neu", "project": "werkstatt",
         "timestamp": (jetzt - timedelta(seconds=10)).isoformat(),
         "agent": "agent_pipeline"},
        {"kind": "loop_failed", "run_id": "neu", "project": "werkstatt",
         "timestamp": jetzt.isoformat(), "agent": "agent_pipeline"},
    ])
    feed = inspector.aggregate_live_feed("werkstatt")
    assert feed["run_id"] == "neu"
    kinds = [s["kind"] for s in feed.get("steps") or []]
    assert "old_event" not in kinds


def test_gate_open_als_aktiv(projektion, tmp_path):
    """OP-381: gate_open am Ende -> aktiv.kind=gate_open, rolle=loop."""
    jetzt = datetime.now(UTC)
    _schreibe(tmp_path, [
        {"kind": "loop_started", "run_id": "r1", "project": "werkstatt",
         "timestamp": (jetzt - timedelta(seconds=10)).isoformat(),
         "agent": "agent_pipeline"},
        {"kind": "gate_open", "run_id": "r1", "project": "werkstatt",
         "timestamp": jetzt.isoformat(), "agent": "agent_pipeline",
         "payload": {"gate_id": "g1", "prompt": "Plan ausfuehren?"}},
    ])
    feed = inspector.aggregate_live_feed("werkstatt")
    aktiv = feed.get("aktiv") or {}
    assert aktiv.get("kind") == "gate_open"
    assert aktiv.get("rolle") == "loop"
    assert "wart" in aktiv.get("aktion", "").lower()


def test_aktiv_grace_5s(projektion, tmp_path):
    """OP-394: gerade-fertig-Events <5s erscheinen als aktiv mit gerade_fertig=True."""
    jetzt = datetime.now(UTC)
    _schreibe(tmp_path, [
        {"kind": "loop_started", "run_id": "r1", "project": "werkstatt",
         "timestamp": (jetzt - timedelta(seconds=10)).isoformat(),
         "agent": "agent_pipeline"},
        {"kind": "loop_task_ok", "run_id": "r1", "project": "werkstatt",
         "timestamp": (jetzt - timedelta(seconds=2)).isoformat(),
         "agent": "agent_pipeline",
         "payload": {"elapsed_s": 1.5}},
    ])
    feed = inspector.aggregate_live_feed("werkstatt")
    aktiv = feed.get("aktiv") or {}
    assert aktiv.get("gerade_fertig") is True, aktiv
    assert aktiv.get("kind") == "loop_task_ok"

def test_open_task_remains_active_after_builder_context_event(
    projektion, tmp_path,
):
    """Zwischenereignisse des Builders duerfen den Task-Spinner nicht loeschen."""
    jetzt = datetime.now(UTC)
    _schreibe(tmp_path, [
        {
            "kind": "loop_started", "run_id": "r-active-task",
            "project": "werkstatt",
            "timestamp": (jetzt - timedelta(seconds=15)).isoformat(),
            "agent": "agent_pipeline",
        },
        {
            "kind": "loop_task_start", "run_id": "r-active-task",
            "project": "werkstatt",
            "timestamp": (jetzt - timedelta(seconds=8)).isoformat(),
            "agent": "agent_pipeline",
            "payload": {
                "task_id": "task-1",
                "name": "Reconnect-Anzeige vervollstaendigen",
            },
        },
        {
            "kind": "builder_file_context", "run_id": "r-active-task",
            "project": "werkstatt",
            "timestamp": jetzt.isoformat(),
            "agent": "builder",
            "payload": {"files": ["static/chat.js"]},
        },
    ])

    aktiv = inspector.aggregate_live_feed("werkstatt")["aktiv"]

    assert aktiv["kind"] == "loop_task_start"
    assert aktiv["activity_kind"] == "builder_file_context"
    assert aktiv["rolle"] == "builder"
    assert aktiv["task_id"] == "task-1"
    assert "baut" in aktiv["aktion"]
    assert "Reconnect-Anzeige" in aktiv["aktion"]


def test_chat_job_events_join_project_live_feed(projektion, tmp_path):
    jetzt = datetime.now(UTC)
    _schreibe(tmp_path, [
        {
            "kind": "loop_started", "run_id": "r-chat",
            "project": "demo", "timestamp": jetzt.isoformat(),
            "agent": "agent_pipeline",
        },
        {
            "kind": "chat_job_started", "run_id": "r-chat",
            "project": "demo", "timestamp": jetzt.isoformat(),
            "agent": "agent_pipeline",
            "job_id": "job-1", "session_id": "session-1",
            "job_event_seq": 1, "status": "running",
        },
    ])
    store = _es.EventStore()
    store.append(
        "r-chat", "chat_job_started", "chat", "running",
        {
            "job_id": "job-1", "session_id": "session-1",
            "job_event_seq": 1,
        },
        event_id="chat-job:job-1:1", project="demo",
    )
    store.append(
        "r-chat", "chat_job_failed", "chat", "failed",
        {"job_id": "job-other", "session_id": "session-2"},
        event_id="chat-job:job-other:1", project="other-project",
    )

    feed = inspector.aggregate_live_feed("demo")
    aktiv = feed["aktiv"]
    assert aktiv["kind"] == "chat_job_started"
    assert aktiv["rolle"] == "chat"
    assert aktiv["aktion"] == "Projekt wird geprueft"
    assert sum(
        1 for item in [*feed["steps"], aktiv]
        if item.get("kind") == "chat_job_started"
    ) == 1
    assert not any(
        step["kind"] == "chat_job_failed" for step in feed["steps"]
    )


def test_live_feed_explizite_run_id_bleibt_projektisoliert(projektion, tmp_path):
    """Control-Livefeed zeigt bei gleicher Run-ID nur das aktive Projekt."""
    jetzt = datetime.now(UTC).isoformat()
    _schreibe(tmp_path, [
        {"kind": "builder_patch_updated", "run_id": "shared",
         "project": "demo", "timestamp": jetzt, "agent": "builder"},
        {"kind": "architect_plan", "run_id": "shared",
         "project": "anderes-projekt", "timestamp": jetzt, "agent": "architect"},
    ])
    feed = inspector.aggregate_live_feed("demo", run_id="shared")
    kinds = [step["kind"] for step in feed["steps"]]
    assert "builder_patch_updated" in kinds
    assert "architect_plan" not in kinds

def test_live_feed_exposes_only_curated_decision_evidence(projektion, tmp_path):
    """Timeline traegt Phasen/Task-Kontext fort, aber keine Rohgedanken."""
    jetzt = datetime.now(UTC)
    _schreibe(tmp_path, [
        {
            "kind": "loop_phase", "run_id": "r-evidence",
            "project": "demo",
            "timestamp": (jetzt - timedelta(seconds=2)).isoformat(),
            "agent": "agent_pipeline", "payload": {"phase": "verify"},
        },
        {
            "kind": "loop_task_start", "run_id": "r-evidence",
            "project": "demo",
            "timestamp": (jetzt - timedelta(seconds=1)).isoformat(),
            "agent": "builder",
            "payload": {"task_id": "t-2", "name": "Regressionstests ausfuehren"},
        },
        {
            "kind": "loop_verify_ok", "run_id": "r-evidence",
            "project": "demo", "timestamp": jetzt.isoformat(),
            "agent": "agent_pipeline",
            "payload": {
                "result_summary": "Alle 12 Tests bestanden.",
                "decision_summary": "Zielkriterien sind noch offen.",
                "evidence": ["pytest: 12 passed", "ruff: clean"],
                "next_step": "Offenes Akzeptanzkriterium pruefen.",
                "chain_of_thought": "Dieses interne Feld darf nie in der Timeline sein.",
            },
        },
    ])
    feed = inspector.aggregate_live_feed("demo")
    step = next(item for item in feed["steps"]
                if item["kind"] == "loop_verify_ok")
    assert step["project"] == "demo"
    assert step["run_id"] == "r-evidence"
    assert step["phase"] == "verify"
    assert step["task_id"] == "t-2"
    assert step["task_name"] == "Regressionstests ausfuehren"
    assert step["result_summary"] == "Alle 12 Tests bestanden."
    assert step["decision_summary"] == "Zielkriterien sind noch offen."
    assert step["evidence"] == ["pytest: 12 passed", "ruff: clean"]
    assert step["next_step"] == "Offenes Akzeptanzkriterium pruefen."
    assert "chain_of_thought" not in step
    assert "chain_of_thought" not in str(step)


def test_live_feed_shows_verify_recovery_as_curated_steps(projektion, tmp_path):
    """Recovery-Verlauf zeigt Ergebnis und nächsten Schritt ohne Rohprompt."""
    jetzt = datetime.now(UTC)
    _schreibe(tmp_path, [
        {
            "kind": "loop_verify_recovery_started", "run_id": "r-recovery",
            "project": "demo",
            "timestamp": jetzt.isoformat(),
            "agent": "agent_pipeline",
            "payload": {
                "stage_ids": ["pytest_regression"],
                "result_summary": "Gezielte Reparatur startet.",
                "decision_summary": "Nur belegte Verify-Befunde werden bearbeitet.",
                "evidence": ["Verify-Stage: pytest_regression"],
                "next_step": "Reparieren und vollständige Endprüfung wiederholen.",
                "prompt": "Dieses Rohfeld darf nicht in die Timeline.",
            },
        },
    ])
    feed = inspector.aggregate_live_feed("demo")
    step = next(
        item for item in feed["steps"]
        if item["kind"] == "loop_verify_recovery_started"
    )
    assert step["result_summary"] == "Gezielte Reparatur startet."
    assert step["decision_summary"] == "Nur belegte Verify-Befunde werden bearbeitet."
    assert step["evidence"] == ["Verify-Stage: pytest_regression"]
    assert step["next_step"] == "Reparieren und vollständige Endprüfung wiederholen."
    assert "prompt" not in step
    assert "prompt" not in str(step)



def test_llm_heartbeat_keeps_builder_activity_with_task_and_files(
    projektion, tmp_path,
):
    """Lange Builder-Aufrufe bleiben aktiv und zeigen begrenzten Task-Kontext."""
    jetzt = datetime.now(UTC)
    _schreibe(tmp_path, [
        {
            "kind": "llm_call_start",
            "run_id": "r1",
            "project": "werkstatt",
            "timestamp": (jetzt - timedelta(seconds=50)).isoformat(),
            "agent": "builder",
            "payload": {
                "task_id": "t3",
                "task_name": "Reconnect-Anzeige vervollstaendigen",
                "files": ["static/chat.js", "tests/test_chat_frontend.py"],
            },
        },
        {
            "kind": "llm_call_heartbeat",
            "run_id": "r1",
            "project": "werkstatt",
            "timestamp": jetzt.isoformat(),
            "agent": "builder",
            "payload": {
                "task_id": "t3",
                "task_name": "Reconnect-Anzeige vervollstaendigen",
                "files": ["static/chat.js", "tests/test_chat_frontend.py"],
                "elapsed_s": 45,
            },
        },
    ])

    feed = inspector.aggregate_live_feed("werkstatt")
    aktiv = feed["aktiv"]
    assert aktiv["kind"] == "llm_call_heartbeat"
    assert aktiv["rolle"] == "builder"
    assert "Reconnect-Anzeige vervollstaendigen" in aktiv["aktion"]
    assert "static/chat.js" in aktiv["aktion"]
    assert "45s" in aktiv["aktion"]

    heartbeat = next(
        step for step in feed["steps"]
        if step["kind"] == "llm_call_heartbeat"
    )
    assert heartbeat["label"] == "Modellaufruf läuft"
    assert heartbeat["detail"] == (
        "arbeitet weiter: Reconnect-Anzeige vervollstaendigen · "
        "static/chat.js, tests/test_chat_frontend.py · 45s"
    )



def test_kriterienfortschritt_ist_in_timeline_menschlich_beschriftet():
    label = inspector._tl_label("loop_criteria_progress", {})
    detail = inspector._tl_detail(
        "loop_criteria_progress",
        {
            "task_id": "t2",
            "covered": ["AC1"],
            "remaining": ["AC2", "AC3"],
            "next_step": "Weiter mit t3: Tests ergaenzen",
        },
    )

    assert label == "Akzeptanzkriterien: Fortschritt"
    assert detail == (
        "1 erledigt, 2 offen nach t2; danach: Weiter mit t3: Tests ergaenzen"
    )
