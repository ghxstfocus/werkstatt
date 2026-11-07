"""Test-Spec-Validator (OP-212, ADR-0016-Nachtrag).

Prueft eine TestSpec unabhaengig gegen die Original-Anforderung:
  - LLM-Call mit eigenem Prompt (nicht Architect-Prompt)
  - Smoke-Test-Heuristik (Config-Details vs Spec-Verhalten)
  - Schema-Validierung (Pflichtfelder, Duplikate)

Der Validator nimmt keine RunState — er ist standalone und wird
von OP-210 (Test-Loop-Phase) verdrahtet.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from werkstatt.agent import ask_llm
from werkstatt.test_spec import TestSpec, validate_schema

# Config-Dateien, deren Inhalte KEINE Spec-Tests sind.
_CONFIG_FILES = (
    "pytest.ini", "mypy.ini", "requirements.txt",
    ".gitignore", "pyproject.toml",
)


@dataclass
class ValidationResult:
    deckt_ab: bool
    fehlende_ak: list[str] = field(default_factory=list)
    negativ_faelle_ok: bool = False
    mehrdeutigkeiten: list[str] = field(default_factory=list)
    schema_fehler: list[str] = field(default_factory=list)
    smoke_test_verdacht: list[str] = field(default_factory=list)


_VALIDATOR_SYSTEM = """Du bist ein unabhaengiger Test-Spec-Validator.
Du pruefst, ob eine Test-Spec die Original-Anforderung vollstaendig
abdeckt — als Proxy fuer einen menschlichen Reviewer.

Du hast KEINE Informationen ueber die Architect-Interpretation.
Du kennst nur:
  1. Die Original-Anforderung (OP-Text).
  2. Die Test-Spec (Liste von Acceptance-Kriterien + Negativ-Faellen).

Pruefe:
  a) Deckt die Spec ALLE Anforderungen aus dem OP-Text ab?
     Fehlt ein Aspekt (Funktion, Fehlerfall, Grenzfall)?
  b) Sind die Negativ-Faelle ausreichend (ungueltige Eingabe,
     fehlende Berechtigung, Fehlerzustaende)?
  c) Sind AKs eindeutig pruefbar formuliert, oder gibt es
     mehrdeutige Stellen ("sollte", "koennte", "eventuell")?
  d) Prueft ein AK Config-Details (Datei-Inhalt in pytest.ini,
     requirements.txt, .gitignore), obwohl der OP das NICHT
     fordert? Das ist ein "Smoke-Test statt Spec-Test"-Verdacht.

Antworte NUR mit validem JSON:
{
  "deckt_ab": true|false,
  "fehlende_ak": ["..."],
  "negativ_faelle_ok": true|false,
  "mehrdeutigkeiten": ["..."],
  "smoke_test_verdacht": ["..."]
}
"""


def _detect_smoke_tests(spec: TestSpec, original_requirement: str) -> list[str]:
    """Heuristik: AKs mit verification=file_content auf Config-Dateien.

    Wenn die Original-Anforderung die Datei NICHT explizit nennt,
    ist ein Test, der sie prueft, ein Smoke-Test-Verdacht.
    """
    verdacht: list[str] = []
    req_lower = (original_requirement or "").lower()
    for ac in spec.acceptance_criteria:
        if ac.verification != "file_content":
            continue
        beh = (ac.expected_behavior + " " + ac.condition).lower()
        for cfg in _CONFIG_FILES:
            if cfg in beh and cfg not in req_lower:
                verdacht.append(
                    f"{ac.id}: prueft {cfg} ohne Anforderung im OP-Text"
                )
                break
    return verdacht


def _parse_validator_response(raw: str) -> dict | None:
    """Robustes JSON-Parsing (Slice + Klammern-Repair)."""
    if not raw:
        return None
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start >= 0 and end > start:
        try:
            obj = json.loads(raw[start:end])
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass
    # Klammern-Repair
    if start >= 0:
        slice_ = raw[start:]
        opens = slice_.count("{") - slice_.count("}")
        if opens > 0:
            try:
                obj = json.loads(slice_ + "}" * opens)
                if isinstance(obj, dict):
                    return obj
            except json.JSONDecodeError:
                pass
    return None


def validate_test_spec(
    original_requirement: str,
    spec: TestSpec,
    api_key: str,
) -> ValidationResult:
    """Prueft Spec gegen Original-Anforderung.

    - Schema-Validierung (deterministisch, immer)
    - Smoke-Test-Heuristik (deterministisch, immer)
    - LLM-Call nur wenn api_key und Schema ok

    Bei fehlendem api_key: nur deterministische Pruefungen,
    deckt_ab wird auf False gesetzt (fail-closed).
    """
    schema_fehler = validate_schema(spec)
    smoke = _detect_smoke_tests(spec, original_requirement)

    result = ValidationResult(
        deckt_ab=False,
        schema_fehler=schema_fehler,
        smoke_test_verdacht=smoke,
    )

    # Schema-Fehler oder Smoke-Test-Verdacht blocken LLM-Call
    if schema_fehler:
        return result

    if not api_key:
        # Ohne LLM kein unabhaengiges Urteil. Fail-closed.
        result.mehrdeutigkeiten.append(
            "Kein api_key — unabhaengige Pruefung nicht moeglich"
        )
        return result

    user_content = (
        f"## ORIGINAL-ANFORDERUNG\n{original_requirement}\n\n"
        f"## TEST-SPEC\n{json.dumps(spec.to_dict(), ensure_ascii=False, indent=2)}"
    )
    reply = ask_llm(
        api_key,
        _VALIDATOR_SYSTEM,
        user_content,
        model="deepseek-chat",
        temperature=0.0,
        max_tokens=2000,
        aufgabe="validator",
    )
    if not reply.ok:
        result.mehrdeutigkeiten.append(f"LLM-Fehler: {reply.error[:200]}")
        return result

    parsed = _parse_validator_response(reply.content)
    if parsed is None:
        result.mehrdeutigkeiten.append("LLM-Antwort nicht parsebar")
        return result

    result.deckt_ab = bool(parsed.get("deckt_ab", False))
    result.fehlende_ak = list(parsed.get("fehlende_ak") or [])
    result.negativ_faelle_ok = bool(parsed.get("negativ_faelle_ok", False))
    result.mehrdeutigkeiten = list(parsed.get("mehrdeutigkeiten") or [])
    # Smoke-Test aus LLM ergaenzen
    llm_smoke = list(parsed.get("smoke_test_verdacht") or [])
    for item in llm_smoke:
        if item not in result.smoke_test_verdacht:
            result.smoke_test_verdacht.append(item)
    return result
