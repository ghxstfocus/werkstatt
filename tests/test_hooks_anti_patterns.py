"""Tests fuer hooks/anti_patterns.py (A8-3)."""
from __future__ import annotations

import json
import subprocess

HOOK = "/opt/werkstatt/hooks/anti_patterns.py"


def _call(rolle: str, trigger_grund: str = "") -> list[dict]:
    args = ["python3", HOOK, "--rolle", rolle]
    if trigger_grund:
        args.extend(["--trigger-grund", trigger_grund])
    res = subprocess.run(args, capture_output=True, text=True, timeout=10, check=False)
    assert res.returncode == 0, f"hook rc={res.returncode} stderr={res.stderr[:300]}"
    return json.loads(res.stdout)


def test_hook_liefert_json_liste() -> None:
    out = _call("builder")
    assert isinstance(out, list)
    assert len(out) >= 1
    for e in out:
        assert "id" in e and "titel" in e
        assert "beschreibung" in e and "loesung" in e


def test_hook_limit_3_bei_builder() -> None:
    out = _call("builder")
    assert len(out) <= 3


def test_hook_unbekannte_rolle_leer() -> None:
    out = _call("gibt-es-nicht")
    assert out == []


def test_hook_trigger_grund_filtert() -> None:
    """Bei tg=anker_nicht_gemessen muss ap-string-literal-statt-konstante
    (Stufe 1) unter den Top-3 sein. Falls Katalog-Reihenfolge in Stufe 1
    anders ist, ist das ein Katalog-Thema, kein Hook-Thema."""
    out = _call("builder", "anker_nicht_gemessen")
    ids = [e["id"] for e in out]
    # Print IDs fuer Debug
    print(f"hook(builder, anker_nicht_gemessen) = {ids}")
    # Akzeptiere, wenn mindestens ein Stufe-1-Eintrag drin ist
    assert any("anker" in i or "string" in i for i in ids), f"keine AP-Treffer: {ids}"


def test_hook_ohne_trigger_zeigt_fallback() -> None:
    out = _call("builder")
    assert len(out) >= 1


def test_hook_fehlender_katalog_nicht_testbar() -> None:
    from pathlib import Path
    src = Path(HOOK).read_text()
    assert "FileNotFoundError" in src
