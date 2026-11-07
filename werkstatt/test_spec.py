"""Test-Spec-Dataclasses und Schema-Validierung (OP-212, ADR-0016).

Der Architect liefert test_spec als strukturiertes Dict. Der
Test-Agent baut daraus die Tests. Der Validator
(werkstatt/test_spec_validator.py) prueft die Spec unabhaengig
gegen die Original-Anforderung.

Schema:
    {
      "requirement_id": "OP-NNN",
      "acceptance_criteria": [
        {
          "id": "AC-NNN",
          "condition": "Konkretes erwartetes Verhalten",
          "expected_behavior": "Beobachtbares Verhalten, nicht Dateiinhalt",
          "verification": "public_api|cli_output|file_content"
        }
      ],
      "negative_cases": ["Ungueltige Eingabe", "..."]
    }
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

VALID_VERIFICATIONS = ("public_api", "cli_output", "file_content")


@dataclass
class AcceptanceCriterion:
    id: str
    condition: str
    expected_behavior: str
    verification: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "condition": self.condition,
            "expected_behavior": self.expected_behavior,
            "verification": self.verification,
        }


@dataclass
class TestSpec:
    # Pytest sammelt Klassen mit Namen Test* automatisch. Wir
    # wollen keine Test-Klasse, sondern eine Datenklasse.
    __test__ = False

    requirement_id: str
    acceptance_criteria: list[AcceptanceCriterion] = field(default_factory=list)
    negative_cases: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "requirement_id": self.requirement_id,
            "acceptance_criteria": [ac.to_dict() for ac in self.acceptance_criteria],
            "negative_cases": list(self.negative_cases),
        }


def validate_schema(spec: TestSpec) -> list[str]:
    """Prueft Schema-Regeln. Liefert Liste von Fehlern (leer = ok)."""
    errors: list[str] = []
    if not spec.requirement_id or not isinstance(spec.requirement_id, str):
        errors.append("requirement_id fehlt oder ist kein String")
    if not spec.acceptance_criteria:
        errors.append("acceptance_criteria ist leer")
    seen_ids: set[str] = set()
    for ac in spec.acceptance_criteria:
        if not isinstance(ac.id, str) or not ac.id:
            errors.append("acceptance_criteria: ein Eintrag ohne id")
            continue
        if ac.id in seen_ids:
            errors.append(f"acceptance_criteria: doppelte id {ac.id}")
        seen_ids.add(ac.id)
        if not isinstance(ac.condition, str) or not ac.condition.strip():
            errors.append(f"AC {ac.id}: condition fehlt")
        if not isinstance(ac.expected_behavior, str) or not ac.expected_behavior.strip():
            errors.append(f"AC {ac.id}: expected_behavior fehlt")
        if ac.verification not in VALID_VERIFICATIONS:
            errors.append(
                f"AC {ac.id}: verification '{ac.verification}' ungueltig, "
                f"erlaubt: {VALID_VERIFICATIONS}"
            )
    if not isinstance(spec.negative_cases, list):
        errors.append("negative_cases ist keine Liste")
    return errors


def parse_test_spec(raw: dict[str, Any]) -> TestSpec:
    """Baut TestSpec aus Dict. Wirft ValueError bei strukturellen Fehlern.

    Schema-Validierung (Pflichtfelder, Typen, Duplikate) erfolgt
    separat in validate_schema(), damit parse_test_spec auch
    unvollstaendige Specs akzeptiert (Validator soll Fehler
    berichten, nicht crashen).
    """
    if not isinstance(raw, dict):
        raise ValueError(f"test_spec ist kein Dict: {type(raw).__name__}")  # noqa: TRY004
    rid = raw.get("requirement_id")
    acs_raw = raw.get("acceptance_criteria") or []
    ncs_raw = raw.get("negative_cases") or []
    if not isinstance(acs_raw, list):
        raise ValueError("acceptance_criteria ist keine Liste")  # noqa: TRY004
    if not isinstance(ncs_raw, list):
        raise ValueError("negative_cases ist keine Liste")  # noqa: TRY004
    acs: list[AcceptanceCriterion] = []
    for entry in acs_raw:
        if not isinstance(entry, dict):
            raise ValueError(f"AC-Eintrag ist kein Dict: {type(entry).__name__}")  # noqa: TRY004
        acs.append(AcceptanceCriterion(
            id=str(entry.get("id", "")),
            condition=str(entry.get("condition", "")),
            expected_behavior=str(entry.get("expected_behavior", "")),
            verification=str(entry.get("verification", "")),
        ))
    return TestSpec(
        requirement_id=str(rid) if rid is not None else "",
        acceptance_criteria=acs,
        negative_cases=[str(x) for x in ncs_raw],
    )
