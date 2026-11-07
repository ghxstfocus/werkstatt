"""Spec-Tests fuer werkstatt.test_spec_validator (OP-212)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from werkstatt.test_spec import AcceptanceCriterion, TestSpec
from werkstatt.test_spec_validator import (
    _detect_smoke_tests,
    _parse_validator_response,
    validate_test_spec,
)


def _mk_spec(verification="public_api", behavior="Funktion liefert 3",
             cond="x", rid="OP-X"):
    return TestSpec(
        requirement_id=rid,
        acceptance_criteria=[
            AcceptanceCriterion(
                id="AC-001", condition=cond,
                expected_behavior=behavior, verification=verification,
            ),
        ],
        negative_cases=["ungueltige eingabe"],
    )


def _mk_llm_reply(content: str, ok: bool = True, error: str = ""):
    r = MagicMock()
    r.ok = ok
    r.content = content
    r.error = error
    return r


# ============ Unit: _detect_smoke_tests ============

def test_smoke_public_api_kein_verdacht():
    spec = _mk_spec(verification="public_api", behavior="Funktion liefert 3")
    assert _detect_smoke_tests(spec, "Baue Funktion foo()") == []


def test_smoke_file_content_config_ist_verdacht():
    """pytest.ini ist im behavior, nicht im OP-Text -> Smoke-Test."""
    spec = _mk_spec(
        verification="file_content",
        behavior="pytest.ini enthaelt testpaths",
    )
    verdacht = _detect_smoke_tests(spec, "Baue Funktion foo()")
    assert len(verdacht) == 1
    assert "pytest.ini" in verdacht[0]


def test_smoke_file_content_config_im_op_ok():
    """Wenn der OP die Config explizit nennt, ist der Test legitim."""
    spec = _mk_spec(
        verification="file_content",
        behavior="pytest.ini enthaelt testpaths",
    )
    verdacht = _detect_smoke_tests(spec, "Erweitere pytest.ini um testpaths")
    assert verdacht == []


def test_smoke_requirements_txt_verdacht():
    spec = _mk_spec(
        verification="file_content",
        behavior="requirements.txt hat 2 Kommentarzeilen",
    )
    verdacht = _detect_smoke_tests(spec, "Baue Feature")
    assert any("requirements.txt" in v for v in verdacht)


# ============ Unit: _parse_validator_response ============

def test_parse_gueltiges_json():
    raw = '{"deckt_ab": true, "fehlende_ak": [], "negativ_faelle_ok": true}'
    obj = _parse_validator_response(raw)
    assert obj is not None
    assert obj["deckt_ab"] is True


def test_parse_mit_prosa_prefix():
    raw = 'Vorwort\n{"deckt_ab": false, "fehlende_ak": ["AC-002"]}\nNachwort'
    obj = _parse_validator_response(raw)
    assert obj is not None
    assert obj["deckt_ab"] is False


def test_parse_truncated_klammer_repair():
    raw = '{"deckt_ab": true, "fehlende_ak": ["AC-001"]'
    obj = _parse_validator_response(raw)
    assert obj is not None
    assert obj["deckt_ab"] is True


def test_parse_garbage_none():
    assert _parse_validator_response("kein json") is None
    assert _parse_validator_response("") is None


# ============ validate_test_spec ============

def test_validate_schema_fehler_blockt_llm():
    """Schema-Fehler -> kein LLM-Call, deckt_ab=False."""
    spec = TestSpec(requirement_id="", acceptance_criteria=[])  # leer = schema-fehler
    with patch("werkstatt.test_spec_validator.ask_llm") as mock:
        result = validate_test_spec("Anforderung", spec, api_key="x")
    mock.assert_not_called()
    assert result.deckt_ab is False
    assert result.schema_fehler


def test_validate_ohne_api_key_fail_closed():
    """Ohne api_key: keine unabhaengige Pruefung moeglich."""
    spec = _mk_spec()
    result = validate_test_spec("Anforderung", spec, api_key="")
    assert result.deckt_ab is False
    assert any("Kein api_key" in m for m in result.mehrdeutigkeiten)


def test_validate_llm_ok_deckt_ab():
    spec = _mk_spec()
    reply = _mk_llm_reply(
        '{"deckt_ab": true, "fehlende_ak": [], '
        '"negativ_faelle_ok": true, "mehrdeutigkeiten": []}'
    )
    with patch("werkstatt.test_spec_validator.ask_llm", return_value=reply):
        result = validate_test_spec("Anforderung", spec, api_key="x")
    assert result.deckt_ab is True
    assert result.negativ_faelle_ok is True
    assert result.fehlende_ak == []


def test_validate_llm_smoke_test_merged():
    """LLM-Smoke-Test-Verdacht wird mit deterministischem gemerged."""
    spec = _mk_spec(
        verification="file_content",
        behavior="pytest.ini enthaelt testpaths",
    )
    reply = _mk_llm_reply(
        '{"deckt_ab": true, "fehlende_ak": [], '
        '"negativ_faelle_ok": true, "mehrdeutigkeiten": [], '
        '"smoke_test_verdacht": ["AC-999: LLM-Befund"]}'
    )
    with patch("werkstatt.test_spec_validator.ask_llm", return_value=reply):
        result = validate_test_spec("Anforderung", spec, api_key="x")
    # deterministischer Verdacht + LLM-Verdacht
    assert len(result.smoke_test_verdacht) == 2


def test_validate_llm_fehler_fail_closed():
    reply = _mk_llm_reply("", ok=False, error="timeout")
    with patch("werkstatt.test_spec_validator.ask_llm", return_value=reply):
        spec = _mk_spec()
        result = validate_test_spec("Anforderung", spec, api_key="x")
    assert result.deckt_ab is False
    assert any("LLM-Fehler" in m for m in result.mehrdeutigkeiten)


def test_validate_llm_unparsebar_fail_closed():
    reply = _mk_llm_reply("kein json hier")
    with patch("werkstatt.test_spec_validator.ask_llm", return_value=reply):
        spec = _mk_spec()
        result = validate_test_spec("Anforderung", spec, api_key="x")
    assert result.deckt_ab is False
    assert any("nicht parsebar" in m for m in result.mehrdeutigkeiten)
