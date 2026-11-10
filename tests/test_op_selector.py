"""Tests fuer die evidenzbasierte OP-Auswahl."""
from werkstatt.web.op_selector import parse_completed_op_ids, select_next_op


def _op(op_id: str, *, title: str = "Arbeit", status: str = "open",
        blockers: str = "—", criteria: str = "Ergebnis ist korrekt.",
        tests: str = "pytest -q tests/test_feature.py",
        phase: str = "") -> str:
    phase_field = f"- **Phase:** {phase}\n" if phase else ""
    return (
        f"### {op_id}: {title}\n"
        f"{phase_field}"
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


def test_duplicate_op_id_is_never_selected_or_used_as_dependency() -> None:
    duplicate = _op("OP-001", status="done") + _op("OP-001", status="open")
    waiting = _op("OP-002", blockers="OP-001")

    result = select_next_op(duplicate + waiting)

    assert result["zustand"] == "no_candidate"
    assert result["auswahl"] is None
    assert [item["id"] for item in result["kandidaten"]] == []
    assert sum(item["id"] == "OP-001" for item in result["ausgeschlossen"]) == 2
    reasons = " ".join(
        reason for item in result["ausgeschlossen"] for reason in item["gruende"]
    )
    assert "OP-ID kommt mehrfach in STATUS.md vor" in reasons
    assert "Unbekannte oder widerspruechliche Blocker" in reasons




def test_resolves_removed_dependency_only_with_explicit_progress_completion() -> None:
    waiting = _op("OP-002", blockers="OP-001")
    progress = "### 2026-11-10 — OP-001 abgeschlossen: erledigt\n"

    completed = parse_completed_op_ids(progress)
    result = select_next_op(waiting, completed_ids=completed)

    assert completed == {"OP-001"}
    assert result["zustand"] == "selected"
    assert result["auswahl"]["id"] == "OP-002"


def test_progress_mentions_and_superseded_rows_do_not_resolve_dependency() -> None:
    waiting = _op("OP-002", blockers="OP-001")
    progress = (
        "OP-001 wird als Voraussetzung diskutiert.\n"
        "- 2026-11-10 | OP-001 | superseded | ersetzt\n"
    )

    result = select_next_op(waiting, completed_ids=parse_completed_op_ids(progress))

    assert result["zustand"] == "no_candidate"
    assert "Unbekannte oder widerspruechliche Blocker" in " ".join(
        result["ausgeschlossen"][0]["gruende"]
    )


def test_progress_completion_does_not_hide_duplicate_status_identity() -> None:
    duplicate = _op("OP-001", status="done") + _op("OP-001", status="open")
    waiting = _op("OP-002", blockers="OP-001")

    result = select_next_op(
        duplicate + waiting,
        completed_ids={"OP-001"},
    )

    assert result["zustand"] == "no_candidate"
    assert any(
        "Unbekannte oder widerspruechliche Blocker" in " ".join(item["gruende"])
        for item in result["ausgeschlossen"]
    )



def test_resolves_status_autolog_done_row_as_completed_dependency() -> None:
    status = (
        "- 2026-11-09 | OP-381c | done | Gate-Modal fertig.\n"
        "OP-999 mentioned in explanatory prose is not a completion row.\n"
    )

    result = select_next_op(
        _op("OP-002", blockers="OP-381c"),
        completed_ids=parse_completed_op_ids("", status),
    )

    assert result["zustand"] == "selected"
    assert result["auswahl"]["id"] == "OP-002"


def test_phase_three_requires_completed_dogfooding_op() -> None:
    phase_three = _op("OP-101", phase="Phase-3 (Memory)")

    blocked = select_next_op(phase_three)
    assert blocked["zustand"] == "no_candidate"
    assert "Phase-3 gesperrt bis OP-382 abgeschlossen" in " ".join(
        blocked["ausgeschlossen"][0]["gruende"]
    )

    released = select_next_op(phase_three, completed_ids={"OP-382"})
    assert released["zustand"] == "selected"
    assert released["auswahl"]["id"] == "OP-101"
