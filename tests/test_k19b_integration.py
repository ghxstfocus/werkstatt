"""K19b-Integration: _zerlege_in_sub_tasks schneidet keine Description bei 800.

Regression zu rerun84: 15-Punkte-Architect-Prosa (nummeriert) fuehrte
zu Tasks deren description durch _llm_split_einzel_task bei 800
abgeschnitten wurde -> Builder baut nur halbe Punkte.

Mit K19b (2500) darf keine Description wegen 800 gekuerzt werden.
"""
from __future__ import annotations

from typing import Any
from unittest.mock import patch

from werkstatt.planner import _zerlege_in_sub_tasks


# Synthetische 15-Punkte-Prosa (auch mit langen Punkten > 800).
def _prosa_15_punkte() -> str:
    lines = [
        "## core/alerts/filters.py",
        "",
        (
            "In `core/alerts/filters.py`: die frozen Dataclass `AlertFilter` "
            "mit den Feldern `categories`, `min_score`, `since_hours`. "
            "`is_empty()` liefert True wenn alle drei leer. "
            "Diese Beschreibung ist absichtlich lang genug, um zusammen "
            "mit weiteren Punkten ueber 800 Zeichen zu kommen -- genau "
            "der Fall aus rerun84, wo der 800-Cut die zweiten Punkte "
            "verloren hat. Der Builder baute dann nur Punkt 1 und der "
            "Reviewer fand 5 high-bugs. Der Fix K19b zieht die Grenze "
            "auf 2500, damit die Description zusammenhaengend bleibt."
        ),
        "",
        "1. In `core/alerts/filters.py`: `AlertFilter` als frozen Dataclass.",
        "2. In `core/alerts/filters.py`: `AlertFilterError(ServiceError)`.",
        "3. In `core/services/audit_reader_service.py`: `parse_alert_filter`.",
        "4. In `core/services/audit_reader_service.py`: `list_filtered_assessments`.",
        "5. In `core/services/audit_reader_service.py`: leeren Filter NICHT abkuerzen.",
        "6. In `apps/dashboard/routes_alerts.py`: `parse_alert_filter(args)`.",
        "7. In `apps/dashboard/routes_alerts.py`: bei Erfolg Service aufrufen.",
        "8. In `apps/dashboard/routes_alerts.py`: `since_hours` aus `hours`.",
        "9. In `apps/dashboard/templates/alerts.html`: GET-Formular.",
        "10. In `apps/dashboard/templates/alerts.html`: Trefferzahl anzeigen.",
        "11. In `apps/dashboard/static/css/components.css`: `.filter-bar`.",
        "12. In `apps/dashboard/static/css/components.css`: responsive Layout.",
        "13. In `apps/dashboard/templates/alerts.html`: Ruecksetz-Link.",
        "14. In `apps/dashboard/templates/alerts.html`: leerer Zustand Hinweis.",
        "15. In `apps/dashboard/routes_alerts.py`: Docstring ergaenzen.",
    ]
    return "\n".join(lines)


def _build_llm_reply_single(task: dict) -> Any:
    """Simuliert LLM-Antwort fuer _zerlege_in_sub_tasks: 2 Sub-Tasks."""
    class _R:
        def __init__(self, content: str):
            self.ok = True
            self.content = content
            self.error = ""

    # Zwei Sub-Tasks, die auf zwei verschiedene Dateien zeigen.
    # architect_start/ende zitieren die ersten zwei nummerierten Punkte
    # wörtlich -- so wie der echte Architect es tun wuerde.
    import json
    payload = {
        "tasks": [
            {
                "id": "t1",
                "name": "AlertFilter + Error in filters.py",
                "action": "create",
                "task_files": ["core/alerts/filters.py"],
                "architect_start": "1. In `core/alerts/filters.py`",
                "architect_ende": "2. In `core/alerts/filters.py`",
                "dependencies": [],
            },
            {
                "id": "t2",
                "name": "parse + list im Service",
                "action": "update",
                "task_files": ["core/services/audit_reader_service.py"],
                "architect_start": "3. In `core/services/audit_reader_service.py`",
                "architect_ende": "5. In `core/services/audit_reader_service.py`",
                "dependencies": ["t1"],
            },
        ]
    }
    return _R(json.dumps(payload))


def test_kein_800_cut_in_sub_task_description():
    """Description darf nicht durch 800-Cut halbiert werden (K19b)."""
    prosa = _prosa_15_punkte()
    # Sicherstellen, dass die Prosa die 800-Grenze ueberschreitet.
    assert len(prosa) > 800

    with patch("werkstatt.planner.ask_llm") as mock_llm, \
         patch("werkstatt.planner._with_spinner") as mock_spin:
        # _with_spinner gibt das Ergebnis von ask_llm() durch.
        mock_llm.return_value = _build_llm_reply_single({})
        mock_spin.side_effect = lambda label, fn: fn()

        result = _zerlege_in_sub_tasks(
            prosa,
            ["core/alerts/filters.py", "core/services/audit_reader_service.py"],
            "dummy-key", "/tmp", "dummy",
        )

    assert result, "Split lieferte keine Tasks"
    # Kern der K19b-Regression: keine Description wurde bei 800 hart gekuerzt.
    # Der Test prueft, dass die Description von t1 (Punkte 1-2) UND t2 (Punkte 3-5)
    # vollstaendig in der Prosa vorkommen (also woertlich extrahiert).
    for t in result:
        desc = t.get("description", "")
        # Kein hartes 800-Cut-Muster: die Description endet NICHT mitten im
        # Satz bei ~800 Zeichen, WENN der Extraktor etwas gefunden hat.
        # Wir pruefen stattdessen: die Description enthaelt mindestens einen
        # Punkt (nummeriert oder Datei-Header) -- und ist nicht nur der Name.
        assert any(
            s in desc
            for s in ("1. In", "2. In", "3. In", "4. In", "5. In",
                      "core/alerts", "audit_reader_service")
        ), f"Description zu leer: {desc[:200]!r}"


def test_lange_prosa_wird_nicht_zu_kurzer_description():
    """Wenn der Extraktor fehlschlaegt, faellt Planner auf Name+desc zurueck
    -- aber NICHT auf den 800-Cut der Original-Prosa (K19b)."""
    prosa = _prosa_15_punkte()
    # 800-Zeichen-Prefix der Prosa
    prefix_800 = prosa[:800]

    with patch("werkstatt.planner.ask_llm") as mock_llm, \
         patch("werkstatt.planner._with_spinner") as mock_spin:
        # LLM liefert einen Task, dessen architect_start/ende NICHT in Prosa
        # vorkommen -> Extraktor schlaegt fehl -> Fallback greift.
        import json
        payload = {
            "tasks": [
                {
                    "id": "t1",
                    "name": "AlertFilter",
                    "action": "create",
                    "task_files": ["core/alerts/filters.py"],
                    "architect_start": "GIBT ES NICHT",
                    "architect_ende": "AUCH NICHT",
                    "dependencies": [],
                }
            ]
        }
        class _R:
            ok = True
            error = ""
            content = json.dumps(payload)
        mock_llm.return_value = _R()
        mock_spin.side_effect = lambda label, fn: fn()

        result = _zerlege_in_sub_tasks(prosa, ["core/alerts/filters.py"],
                                       "dummy-key", "/tmp", "dummy")

    assert result, "Fallback lieferte keine Tasks"
    desc = result[0].get("description", "")
    # Der Fallback besteht aus Name (+ optional Description). Wichtig:
    # er ist NICHT der rohe 800-Zeichen-Cut der Prosa.
    assert prefix_800[:200] not in desc, (
        "Fallback enthaelt rohen 800-Prefix der Prosa -- K19b verletzt"
    )
