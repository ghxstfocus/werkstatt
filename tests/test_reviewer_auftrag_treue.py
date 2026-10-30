"""Spec: REVIEWER_SYSTEM prueft negative Anweisungen.

Fix B 2026-10-31: Reviewer hatte keinen Auftrags-Treue-Check.
Damit wurde eine Umnummerierung nicht als HIGH-Bug erkannt,
obwohl die Aufgabe "nicht umnummerieren" forderte.
"""
from __future__ import annotations
import sys
sys.path.insert(0, "/opt/werkstatt")
import pytest
from werkstatt.reviewer import REVIEWER_SYSTEM


class TestReviewerAuftragTreue:
    def test_check_ist_im_system_prompt(self) -> None:
        assert "AUFTRAG-TREUE-CHECK" in REVIEWER_SYSTEM

    def test_check_nennt_negative_marker(self) -> None:
        s = REVIEWER_SYSTEM.lower()
        assert "nicht" in s
        assert "kein" in s
        assert "behalte" in s
        assert "erhalte" in s

    def test_check_nennt_umnummerierung(self) -> None:
        assert "umnummerier" in REVIEWER_SYSTEM.lower()

    def test_high_severity_dokumentiert(self) -> None:
        idx = REVIEWER_SYSTEM.find("AUFTRAG-TREUE-CHECK")
        assert idx >= 0
        assert "HIGH" in REVIEWER_SYSTEM[idx:idx + 100]
