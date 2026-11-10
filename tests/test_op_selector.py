"""Tests fuer die evidenzbasierte OP-Auswahl."""
from werkstatt.web.op_selector import select_next_op


def _op(op_id: str, *, title: str = "Arbeit", status: str = "open",
        blockers: str = "—", criteria: str = "Ergebnis ist korrekt.",
        tests: str = "pytest -q tests/test_feature.py") -> str:
    return (
        f"### {op_id}: {title}\n"
        f"- **Status:** {status}\n"
        f"- **Blockiert von:** {blockers}\n"
        f"- **Akzeptanzkriterien:** {criteria}\n"
        f"- **Tests:** {tests}\n"
    )


def test_selects_single_ready_op_and_explains_plan_gate() -> None:
    result = select_next_op(_op("OP-001", title="Einziger Kandidat"))

    assert result["zustand"] == "selected"
    assert result["auswahl"]["id"] == "OP-001"
    assert "Plan-Gate" in result["begruendung"]
    assert "pytest" in result["auswahl"]["verifikation"]


def test_abstains_when_multiple_ready_ops_exist() -> None:
    result = select_next_op(_op("OP-001") + "\n" + _op("OP-002"))

    assert result["zustand"] == "needs_input"
    assert result["auswahl"] is None
    assert [item["id"] for item in result["kandidaten"]] == ["OP-001", "OP-002"]


def test_excludes_open_dependency_and_resolves_completed_dependency() -> None:
    waiting = _op("OP-002", blockers="OP-001")
    open_result = select_next_op(_op("OP-001") + waiting)
    assert open_result["zustand"] == "selected"
    assert open_result["auswahl"]["id"] == "OP-001"
    assert any(
        "Abhaengigkeiten noch offen" in " ".join(item["gruende"])
        for item in open_result["ausgeschlossen"]
    )

    done_result = select_next_op(_op("OP-001", status="done") + waiting)
    assert done_result["zustand"] == "selected"
    assert done_result["auswahl"]["id"] == "OP-002"


def test_excludes_stale_blocker_and_missing_acceptance_or_tests() -> None:
    result = select_next_op(
        _op("OP-001", blockers="OP-999")
        + _op("OP-002", criteria="—")
        + _op("OP-003", tests="—")
    )

    assert result["zustand"] == "no_candidate"
    reasons = " ".join(
        reason for item in result["ausgeschlossen"] for reason in item["gruende"]
    )
    assert "Unbekannte oder widerspruechliche Blocker" in reasons
    assert "Akzeptanzkriterien fehlen" in reasons
    assert "Tests oder ein pruefbarer Nachweis fehlen" in reasons


def test_abstains_on_conflicting_status_metadata() -> None:
    result = select_next_op(_op("OP-001") + "- **Status:** done\n")

    assert result["zustand"] == "no_candidate"
    assert any(
        "Status fehlt oder ist mehrfach angegeben" in " ".join(item["gruende"])
        for item in result["ausgeschlossen"]
    )
