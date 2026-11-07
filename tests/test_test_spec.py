"""Spec-Tests fuer werkstatt.test_spec (OP-212)."""
from __future__ import annotations

import pytest

from werkstatt.test_spec import (
    AcceptanceCriterion,
    TestSpec,
    parse_test_spec,
    validate_schema,
)


def _ac(id="AC-001", cond="x", beh="y", ver="public_api"):
    return AcceptanceCriterion(id=id, condition=cond, expected_behavior=beh, verification=ver)


def test_ac_construction():
    ac = _ac()
    assert ac.id == "AC-001"
    assert ac.verification == "public_api"


def test_spec_round_trip():
    spec = TestSpec(
        requirement_id="OP-212",
        acceptance_criteria=[_ac()],
        negative_cases=["ungueltige eingabe"],
    )
    spec2 = parse_test_spec(spec.to_dict())
    assert spec2.requirement_id == "OP-212"
    assert len(spec2.acceptance_criteria) == 1
    assert spec2.acceptance_criteria[0].id == "AC-001"
    assert spec2.negative_cases == ["ungueltige eingabe"]


def test_schema_ok():
    spec = TestSpec(requirement_id="OP-X", acceptance_criteria=[_ac()])
    assert validate_schema(spec) == []


def test_schema_leere_acs():
    spec = TestSpec(requirement_id="OP-X", acceptance_criteria=[])
    errors = validate_schema(spec)
    assert any("acceptance_criteria ist leer" in e for e in errors)


def test_schema_fehlende_requirement_id():
    spec = TestSpec(requirement_id="", acceptance_criteria=[_ac()])
    errors = validate_schema(spec)
    assert any("requirement_id" in e for e in errors)


def test_schema_ungueltige_verification():
    spec = TestSpec(requirement_id="OP-X", acceptance_criteria=[_ac(ver="bogus")])
    errors = validate_schema(spec)
    assert any("verification" in e for e in errors)


def test_schema_doppelte_ac_id():
    spec = TestSpec(requirement_id="OP-X", acceptance_criteria=[_ac(), _ac()])
    errors = validate_schema(spec)
    assert any("doppelte id" in e for e in errors)


def test_schema_leerer_expected_behavior():
    spec = TestSpec(requirement_id="OP-X", acceptance_criteria=[_ac(beh="")])
    errors = validate_schema(spec)
    assert any("expected_behavior fehlt" in e for e in errors)


def test_parse_nicht_dict_raises():
    with pytest.raises(ValueError, match="kein Dict"):
        parse_test_spec("nope")


def test_parse_acs_nicht_liste_raises():
    with pytest.raises(ValueError, match="acceptance_criteria"):
        parse_test_spec({"requirement_id": "OP-X", "acceptance_criteria": "nope"})


def test_parse_akzeptiert_unvollstaendig():
    spec = parse_test_spec({"requirement_id": "OP-X", "acceptance_criteria": [{"id": "AC-1"}]})
    assert spec.acceptance_criteria[0].id == "AC-1"
    assert spec.acceptance_criteria[0].expected_behavior == ""
