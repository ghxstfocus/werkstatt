"""Tests fuer den Phasen-Modus (Block P2a).

Abdeckung (Auflagen P2a-S5b-A12, P2a-S5c-A4, A7):
  - _phase_main_pfad Signatur.
  - _AUDIT_KINDS_BEKANNT enthaelt phase_plan_* Werte.
  - main() --phase-Zweig: rc=65 bei leerem Phasentext.
  - main() Konflikt-Check: --phase + --planner -> rc=65.
  - _phase_plan_als_text: Roundtrip-Property + Fehler.
  - _phase_edit_modus: Signatur.
"""
from __future__ import annotations

import inspect
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pipeline

PIPELINE_PFAD = str(
    Path(__file__).resolve().parent.parent / "pipeline.py")


# =====================================================================
# _phase_main_pfad — Signatur
# =====================================================================

class TestPhaseMainPfad:
    def test_funktion_existiert(self) -> None:
        assert hasattr(pipeline, "_phase_main_pfad")

    def test_signatur(self) -> None:
        sig = inspect.signature(pipeline._phase_main_pfad)
        params = list(sig.parameters.keys())
        assert params == ["project_name", "phasen_text", "state_ref"]


# =====================================================================
# _AUDIT_KINDS_BEKANNT — neue Werte
# =====================================================================

class TestAuditKinds:
    def test_phase_plan_erstellt_vorhanden(self) -> None:
        assert "phase_plan_erstellt" in pipeline._AUDIT_KINDS_BEKANNT

    def test_phase_plan_parse_failed_vorhanden(self) -> None:
        assert "phase_plan_parse_failed" in pipeline._AUDIT_KINDS_BEKANNT

    def test_phase_plan_verworfen_vorhanden(self) -> None:
        assert "phase_plan_verworfen" in pipeline._AUDIT_KINDS_BEKANNT

    def test_phase_plan_editiert_vorhanden(self) -> None:
        assert "phase_plan_editiert" in pipeline._AUDIT_KINDS_BEKANNT


# =====================================================================
# main() --phase-Zweig — CLI-Validierung
# =====================================================================

class TestMainPhaseZweig:
    def test_leerer_phasentext_rc_65(self) -> None:
        """Leerer Phasentext -> rc=65, keine Aktion."""
        res = subprocess.run(
            [sys.executable, PIPELINE_PFAD,
             "--project", "security-ai", "--phase", ""],
            capture_output=True, text=True, timeout=30,
            check=False,
        )
        assert res.returncode in {65, 66}, (
            f"rc={res.returncode}, "
            f"stdout={res.stdout[:200]}, "
            f"stderr={res.stderr[:200]}")

    def test_konflikt_phase_planner_rc_65(self, tmp_path: Path) -> None:
        """P2a-S5c-A7: --phase und --planner gleichzeitig -> 65.

        Kein Zugriff auf projects/foo.yaml. Konflikt wird
        VOR allen Zweigen erkannt (nach Root-Guard).
        """
        res = subprocess.run(
            [sys.executable, PIPELINE_PFAD,
             "--project", "foo",
             "--phase", "x",
             "--planner", "y"],
            capture_output=True, text=True, timeout=30,
            cwd=str(tmp_path), check=False,
        )
        # Wenn als root: Root-Guard 66. Sonst 65.
        assert res.returncode in {65, 66}, (
            f"rc={res.returncode}, "
            f"stdout={res.stdout[:200]}, "
            f"stderr={res.stderr[:200]}")
        # Kein Traceback.
        assert "Traceback" not in res.stderr


# =====================================================================
# _phase_plan_als_text — Roundtrip-Eigenschaft
# =====================================================================

class TestPhasePlanAlsText:
    def test_funktion_existiert(self) -> None:
        assert hasattr(pipeline, "_phase_plan_als_text")

    def test_signatur(self) -> None:
        sig = inspect.signature(pipeline._phase_plan_als_text)
        params = list(sig.parameters.keys())
        assert params == ["phase_id", "phase_titel", "unterbloecke"]

    def test_roundtrip_einfach(self) -> None:
        unterbloecke = [
            {
                "id": "U1",
                "titel": "Test-U1",
                "unterpunkte": ["a", "b"],
                "geschaetzte_runden": 2,
            },
        ]
        text = pipeline._phase_plan_als_text(
            "P1", "Test", unterbloecke)
        wieder = pipeline._parse_phase_plan(text)
        assert wieder == unterbloecke

    def test_roundtrip_mit_bindestrich_im_titel(self) -> None:
        """P2a-S5c-A5: Titel mit ' - ' muss erhalten bleiben."""
        unterbloecke = [
            {
                "id": "U1",
                "titel": "A - B",
                "unterpunkte": ["x - y"],
                "geschaetzte_runden": 1,
            },
        ]
        text = pipeline._phase_plan_als_text(
            "P1", "Phase - Test", unterbloecke)
        wieder = pipeline._parse_phase_plan(text)
        assert wieder == unterbloecke
        assert wieder[0]["titel"] == "A - B"

    def test_roundtrip_mit_trailing_newline(self) -> None:
        """P2a-S5c-A4: text + '\\n' ergibt denselben Plan."""
        unterbloecke = [
            {
                "id": "U1",
                "titel": "T",
                "unterpunkte": ["p"],
                "geschaetzte_runden": 1,
            },
        ]
        text = pipeline._phase_plan_als_text("P1", "T", unterbloecke)
        ohne = pipeline._parse_phase_plan(text)
        mit = pipeline._parse_phase_plan(text + "\n")
        assert ohne == mit == unterbloecke

    def test_fehlende_unterpunkte(self) -> None:
        unterbloecke = [
            {
                "id": "U1",
                "titel": "T",
                "geschaetzte_runden": 1,
            },
        ]
        try:
            pipeline._phase_plan_als_text("P1", "T", unterbloecke)
        except ValueError:
            return
        raise AssertionError("ValueError erwartet")

    def test_fehlende_runden(self) -> None:
        unterbloecke = [
            {
                "id": "U1",
                "titel": "T",
                "unterpunkte": ["p"],
            },
        ]
        try:
            pipeline._phase_plan_als_text("P1", "T", unterbloecke)
        except ValueError:
            return
        raise AssertionError("ValueError erwartet")


# =====================================================================
# _phase_edit_modus — Signatur
# =====================================================================

class TestPhaseEditModus:
    def test_funktion_existiert(self) -> None:
        assert hasattr(pipeline, "_phase_edit_modus")

    def test_signatur(self) -> None:
        sig = inspect.signature(pipeline._phase_edit_modus)
        params = list(sig.parameters.keys())
        assert params == ["phase_id", "phase_titel", "unterbloecke"]
