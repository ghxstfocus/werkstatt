"""Spec-Tests fuer OP-390: ref-Validierung vor git diff.

Verhalten, das dieser Test verbietet:
- Ein ``ref``-Wert mit fuehrendem ``-`` (z.B. ``--output=/tmp/x``
  oder ``--ext-diff``) wird ungeprueft an ``git diff`` uebergeben.
- ``werkstatt.validierung.pruefe_ref`` erlaubt Shell-Metazeichen
  oder ueberlange Strings.

Regress-Barriere: bei Revert des pruefe_ref-Aufrufs in
``chat_tools._git_diff`` MUSS test_chat_tools_git_diff_output_option_abgelehnt
rot werden.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from werkstatt import chat_tools
from werkstatt.validierung import REF_MUSTER, pruefe_ref

# ---------------------------------------------------------------------
# 1) Unit-Tests pruefe_ref — positive Faelle (muessen alle durchgehen)
# ---------------------------------------------------------------------

@pytest.mark.parametrize("ref", [
    "HEAD",
    "main",
    "HEAD~3",
    "HEAD^",
    "v1.0.0",
    "abc1234",
    "origin/main",
    "refs/heads/feature/foo-bar",
])
def test_pruefe_ref_akzeptiert_gueltige(ref: str) -> None:
    """Uebliche git-Revisionsformate muessen durchgelassen werden."""
    assert pruefe_ref(ref) == ref


# ---------------------------------------------------------------------
# 2) Unit-Tests pruefe_ref — negative Faelle (muessen ValueError werfen)
# ---------------------------------------------------------------------

@pytest.mark.parametrize("ref", [
    "--output=/tmp/owned",
    "-p",
    "--ext-diff",
    "",
    "abc def",
    "HEAD; rm -rf /",
    "a" * 200,
])
def test_pruefe_ref_lehnt_ungueltige_ab(ref: str) -> None:
    """Fuehrendes ``-``, Leerzeichen, Metazeichen, Ueberlaenge -> ValueError."""
    with pytest.raises(ValueError):
        pruefe_ref(ref)


# ---------------------------------------------------------------------
# 3) HTTP-Endpoint /api/projects/{name}/diff
# ---------------------------------------------------------------------

def _client_auth_disabled(monkeypatch) -> TestClient:
    from werkstatt.web import auth
    from werkstatt.web.app import create_app
    monkeypatch.setattr(auth, "_AUTH_DISABLED", True)
    return TestClient(create_app())


def test_endpoint_400_bei_output_option(monkeypatch) -> None:
    """``ref=--output=...`` MUSS 400 geben, kein git diff."""
    client = _client_auth_disabled(monkeypatch)
    r = client.get("/api/projects/werkstatt/diff?ref=--output=/tmp/owned")
    assert r.status_code == 400, r.text
    assert "ref" in r.text.lower()


def test_endpoint_400_bei_kurzer_option(monkeypatch) -> None:
    """``ref=-p`` MUSS 400 geben."""
    client = _client_auth_disabled(monkeypatch)
    r = client.get("/api/projects/werkstatt/diff?ref=-p")
    assert r.status_code == 400, r.text


def test_endpoint_200_bei_normalem_ref(monkeypatch) -> None:
    """``ref=HEAD`` MUSS 200 geben, Diff-Feld vorhanden."""
    client = _client_auth_disabled(monkeypatch)
    r = client.get("/api/projects/werkstatt/diff?ref=HEAD")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ref"] == "HEAD"
    assert "stat" in body and "diff" in body


# ---------------------------------------------------------------------
# 4) Chat-Tool _git_diff
# ---------------------------------------------------------------------

def test_chat_tools_git_diff_normaler_ref() -> None:
    """Normaler ref -> kein Validierungsfehler."""
    aus = chat_tools._git_diff({"ref": "HEAD"})
    assert isinstance(aus, str)
    assert "ungueltiger ref" not in aus


def test_chat_tools_git_diff_output_option_abgelehnt() -> None:
    """``--output=...`` -> Fehler-String, KEIN git-Aufruf.

    Regress-Barriere: dieser Test wird rot, sobald der pruefe_ref-
    Aufruf aus _git_diff entfernt wird.
    """
    aus = chat_tools._git_diff({"ref": "--output=/tmp/owned"})
    assert "ungueltiger ref" in aus


def test_chat_tools_git_diff_leerer_ref_abgelehnt() -> None:
    """Leerer ref -> Fehler-String."""
    aus = chat_tools._git_diff({"ref": ""})
    assert "ungueltiger ref" in aus


# ---------------------------------------------------------------------
# 5) Meta-Test: REF_MUSTER exportiert und kompilierbar
# ---------------------------------------------------------------------

def test_ref_muster_ist_kompiliertes_pattern() -> None:
    """REF_MUSTER muss ein kompiliertes re.Pattern sein (nicht None)."""
    import re
    assert isinstance(REF_MUSTER, re.Pattern)
    # Sanity: erlaubt HEAD, verbietet --output
    assert REF_MUSTER.fullmatch("HEAD") is not None
    assert REF_MUSTER.fullmatch("--output=/x") is None
