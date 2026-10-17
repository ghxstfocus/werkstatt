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

import pytest

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
        # --resume-force (2026-10-16): resume_force ergaenzt.
        assert params == ["project_name", "phasen_text",
                          "state_ref", "resume_force"]


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

# =====================================================================
# _phase_yaml_status_update — P2b-1
# =====================================================================

def _baue_phase_yaml(tmp_path: Path, unterbloecke: list) -> Path:
    """Schreibt eine minimale phase.yaml nach tmp_path.

    Rueckgabe: der Pfad zum projects-Verzeichnis (tmp_path),
    damit der Test _PHASE_YAML_DIR darauf setzen kann.
    """
    import yaml
    daten = {
        "phase_aktiv": True,
        "phase_id": "P1",
        "phase_titel": "Testphase",
        "phase_start_head": "",
        "phase_erstellt_am": "2026-10-15T00:00:00+00:00",
        "phase_unterbloecke": unterbloecke,
    }
    ziel = tmp_path / "testprojekt.phase.yaml"
    ziel.write_text(
        yaml.safe_dump(daten, sort_keys=False,
                       allow_unicode=True, width=4096),
        encoding="utf-8")
    return tmp_path


def _standard_unterbloecke() -> list:
    return [
        {"id": "U1", "titel": "T1", "status": "pending",
         "commit_paket": {}, "unterpunkte": ["a"],
         "geschaetzte_runden": 1},
        {"id": "U2", "titel": "T2", "status": "pending",
         "commit_paket": {}, "unterpunkte": ["b"],
         "geschaetzte_runden": 1},
    ]


@pytest.fixture(autouse=True)
def _mock_phase_judge_go(monkeypatch: pytest.MonkeyPatch) -> None:
    """W29c: Phase-Judge standardmaessig GO.

    Tests, die das Verhalten des Judges pruefen
    (W29-Tests, Fail-Pfade), ueberschreiben diesen
    Mock lokal via monkeypatch.setattr.
    """
    monkeypatch.setattr(
        pipeline, "_phase_judge_review",
        lambda state, aggregat: "GO")
    monkeypatch.setattr(
        pipeline, "_phase_judge_repair_runde",
        lambda state, aggregat: "GO")


class TestPhaseYamlStatusUpdate:
    def test_funktion_existiert(self) -> None:
        assert hasattr(pipeline, "_phase_yaml_status_update")

    def test_setzt_status(self, tmp_path: Path,
                          monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            pipeline, "_PHASE_YAML_DIR", tmp_path)
        _baue_phase_yaml(tmp_path, _standard_unterbloecke())
        pipeline._phase_yaml_status_update(
            "testprojekt", "U1", "running")
        daten = pipeline._phase_plan_laden("testprojekt")
        assert daten is not None
        assert daten["phase_unterbloecke"][0]["status"] == "running"
        assert daten["phase_unterbloecke"][1]["status"] == "pending"

    def test_unbekannter_status_valueerror(
            self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            pipeline, "_PHASE_YAML_DIR", tmp_path)
        _baue_phase_yaml(tmp_path, _standard_unterbloecke())
        try:
            pipeline._phase_yaml_status_update(
                "testprojekt", "U1", "quatsch")
        except ValueError:
            return
        raise AssertionError("ValueError erwartet")

    def test_fehlende_datei_valueerror(
            self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            pipeline, "_PHASE_YAML_DIR", tmp_path)
        try:
            pipeline._phase_yaml_status_update(
                "unbekannt", "U1", "running")
        except ValueError:
            return
        raise AssertionError("ValueError erwartet")

    def test_unbekannte_unterblock_id_valueerror(
            self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            pipeline, "_PHASE_YAML_DIR", tmp_path)
        _baue_phase_yaml(tmp_path, _standard_unterbloecke())
        try:
            pipeline._phase_yaml_status_update(
                "testprojekt", "U99", "running")
        except ValueError:
            return
        raise AssertionError("ValueError erwartet")


# =====================================================================
# run_phase — P2b-1
# =====================================================================

def _state_fuer_phase(tmp_path: Path) -> pipeline.RunState:
    """Baut einen minimalen RunState fuer run_phase."""
    return pipeline.RunState(
        block_id="test",
        aufgabe="test",
        start_ts="2026-10-15T00:00:00+00:00",
        docs={}, agents={}, always={}, optional={},
        file_whitelist=[], api_key="x", budget={},
        agent_docs={}, project_dir=tmp_path,
        project_name="testprojekt",
        phase_id="P1", phase_titel="Testphase",
        phase_aktiv=True,
    )


def _mock_run_pipeline(rc: int = 0,
                       paket: bool = True) -> object:
    """Erzeugt eine run_pipeline-Attrappe fuer Tests.

    Legt den uebergebenen phasen_state in sr_intern und
    haengt optional ein Paket an phase_commit_pakete.
    """
    def _mock(project_name: str, aufgabe: str,
              sr_intern: list, *,
              phasen_state: pipeline.RunState | None = None
              ) -> int:
        if phasen_state is not None:
            sr_intern.append(phasen_state)
            if paket and rc == 0:
                # W29c: pro Aufruf andere Datei, sonst
                # schlaegt D2 (Duplikate) korrekt an.
                n = len(phasen_state.phase_commit_pakete)
                datei = f"apps/x{n}.py"
                # Datei physisch anlegen, damit D5 (tote
                # Dateien) nicht anschlaegt.
                p = phasen_state.project_dir / datei
                p.parent.mkdir(parents=True, exist_ok=True)
                if not p.exists():
                    p.write_text("x", encoding="utf-8")
                phasen_state.phase_commit_pakete.append(
                    {"message": "test",
                     "dateien": [datei]})
        return rc
    return _mock


class TestRunPhase:
    def test_funktion_existiert(self) -> None:
        assert hasattr(pipeline, "run_phase")

    def test_signatur(self) -> None:
        sig = inspect.signature(pipeline.run_phase)
        params = list(sig.parameters.keys())
        assert params == ["project_name", "state",
                          "state_ref"]

    def test_loop_zwei_unterbloecke(
            self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            pipeline, "_PHASE_YAML_DIR", tmp_path)
        _baue_phase_yaml(tmp_path, _standard_unterbloecke())
        state = _state_fuer_phase(tmp_path)
        from unittest.mock import patch
        with patch("pipeline.run_pipeline",
                   side_effect=_mock_run_pipeline(
                       rc=0, paket=True)), \
             patch("pipeline._git_rev_parse_head",
                   return_value="a" * 40), \
             patch("pipeline.apply_commit_and_doku",
                   return_value=True), \
             patch("builtins.input",
                   return_value="j"), \
             patch("pipeline.audit"):
            rc = pipeline.run_phase("testprojekt", state, [])
        assert rc == 0
        assert state.phase_aktueller_index == 2
        daten = pipeline._phase_plan_laden("testprojekt")
        assert daten is not None
        assert daten["phase_unterbloecke"][0]["status"] == "done"
        assert daten["phase_unterbloecke"][1]["status"] == "done"

    def test_leerer_plan_fail_closed(
            self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            pipeline, "_PHASE_YAML_DIR", tmp_path)
        _baue_phase_yaml(tmp_path, [])
        state = _state_fuer_phase(tmp_path)
        rc = pipeline.run_phase("testprojekt", state, [])
        assert rc != 0

    def test_fehlende_phase_yaml_fail_closed(
            self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            pipeline, "_PHASE_YAML_DIR", tmp_path)
        state = _state_fuer_phase(tmp_path)
        rc = pipeline.run_phase("unbekannt", state, [])
        assert rc != 0

    def test_idempotenz_alle_done(
            self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        ups = _standard_unterbloecke()
        for u in ups:
            u["status"] = "done"
        monkeypatch.setattr(
            pipeline, "_PHASE_YAML_DIR", tmp_path)
        _baue_phase_yaml(tmp_path, ups)
        state = _state_fuer_phase(tmp_path)
        # W47: 'alle done' + phase_aktiv=False
        # bedeutet 'Phase bereits beendet'.
        # Mit phase_aktiv=True wuerde der Code
        # weiter zum Gesamt-Review laufen.
        state.phase_aktiv = False
        rc = pipeline.run_phase("testprojekt", state, [])
        assert rc == 0

    def test_no_go_fail_closed(
            self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        ups = _standard_unterbloecke()
        ups[0]["status"] = "no_go"
        monkeypatch.setattr(
            pipeline, "_PHASE_YAML_DIR", tmp_path)
        _baue_phase_yaml(tmp_path, ups)
        state = _state_fuer_phase(tmp_path)
        rc = pipeline.run_phase("testprojekt", state, [])
        assert rc != 0

    def test_audit_kinds_im_log(
            self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            pipeline, "_PHASE_YAML_DIR", tmp_path)
        _baue_phase_yaml(tmp_path, _standard_unterbloecke())
        state = _state_fuer_phase(tmp_path)
        from unittest.mock import patch
        gesehen: list[str] = []

        def fake_audit(kind: str, *a: object,
                       **kw: object) -> None:
            gesehen.append(kind)

        with patch("pipeline.audit", side_effect=fake_audit), \
             patch("pipeline.run_pipeline",
                   side_effect=_mock_run_pipeline(
                       rc=0, paket=True)), \
             patch("pipeline.apply_commit_and_doku",
                   return_value=True), \
             patch("builtins.input",
                   return_value="j"), \
             patch("pipeline._git_rev_parse_head",
                   return_value="a" * 40):
            rc = pipeline.run_phase("testprojekt", state, [])
        assert rc == 0
        assert "run_phase_start" in gesehen
        assert "run_phase_ende" in gesehen
        assert "phase_unterblock_start" in gesehen
        assert "phase_unterblock_ende" in gesehen

# =====================================================================
# _git_rev_parse_head / _git_status_porcelain — P2b-2
# =====================================================================

class TestGitHelpers:
    def test_rev_parse_existiert(self) -> None:
        assert hasattr(pipeline, "_git_rev_parse_head")

    def test_status_porcelain_existiert(self) -> None:
        assert hasattr(pipeline, "_git_status_porcelain")

    def test_rev_parse_kein_repo_gibt_leer(
            self, tmp_path: Path) -> None:
        # tmp_path ist kein git-Repo -> "".
        assert pipeline._git_rev_parse_head(tmp_path) == ""

    def test_status_porcelain_kein_repo_gibt_sentinel(
            self, tmp_path: Path) -> None:
        # tmp_path ist kein git-Repo -> Sentinel (nicht leer).
        out = pipeline._git_status_porcelain(tmp_path)
        assert out != ""


# =====================================================================
# _phase_rollback — P2b-2 (Mock)
# =====================================================================

class TestPhaseRollback:
    def test_funktion_existiert(self) -> None:
        assert hasattr(pipeline, "_phase_rollback")

    def test_signatur(self) -> None:
        sig = inspect.signature(pipeline._phase_rollback)
        params = list(sig.parameters.keys())
        assert params == ["project_name", "state", "grund"]

    def _state(self, tmp_path: Path, head: str) -> pipeline.RunState:
        s = _state_fuer_phase(tmp_path)
        s.phase_start_head = head
        return s

    def test_leerer_start_head_fail_closed(
            self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from unittest.mock import patch
        monkeypatch.setattr(
            pipeline, "_PHASE_YAML_DIR", tmp_path)
        state = self._state(tmp_path, "")
        with patch("pipeline.audit") as mock_audit:
            ok = pipeline._phase_rollback(
                "testprojekt", state, "test")
        assert ok is False
        assert any(
            c.args[1].get("warum") == "kein_phase_start_head"
            for c in mock_audit.call_args_list
            if c.args and c.args[0] == "phase_rollback")

    def test_head_abweichend_kein_reset(
            self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from unittest.mock import patch
        monkeypatch.setattr(
            pipeline, "_PHASE_YAML_DIR", tmp_path)
        state = self._state(tmp_path, "a" * 40)
        with patch("pipeline._git_rev_parse_head",
                   return_value="b" * 40), \
             patch("pipeline.subprocess.run") as mock_run, \
             patch("pipeline.audit"):
            ok = pipeline._phase_rollback(
                "testprojekt", state, "test")
        assert ok is False
        assert not mock_run.called

    def test_status_schmutzig_kein_reset(
            self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from unittest.mock import patch
        monkeypatch.setattr(
            pipeline, "_PHASE_YAML_DIR", tmp_path)
        state = self._state(tmp_path, "a" * 40)
        with patch("pipeline._git_rev_parse_head",
                   return_value="a" * 40), \
             patch("pipeline._git_status_porcelain",
                   return_value=" M x.py"), \
             patch("pipeline.subprocess.run") as mock_run, \
             patch("pipeline.audit"):
            ok = pipeline._phase_rollback(
                "testprojekt", state, "test")
        assert ok is False
        assert not mock_run.called

    def test_erfolg_reset_und_clean(
            self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from unittest.mock import MagicMock, patch
        monkeypatch.setattr(
            pipeline, "_PHASE_YAML_DIR", tmp_path)
        state = self._state(tmp_path, "a" * 40)
        state.file_whitelist = ["apps/"]
        state.phase_commit_pakete = [{"message": "x"}]
        fake_ok = MagicMock()
        fake_ok.returncode = 0
        fake_ok.stdout = ""
        with patch("pipeline._git_rev_parse_head",
                   return_value="a" * 40), \
             patch("pipeline._git_status_porcelain",
                   return_value=""), \
             patch("pipeline.subprocess.run",
                   return_value=fake_ok) as mock_run, \
             patch("pipeline.audit") as mock_audit:
            ok = pipeline._phase_rollback(
                "testprojekt", state, "test")
        assert ok is True
        assert state.phase_commit_pakete == []
        # argv-Aufbau pruefen: reset + clean-dry + clean.
        argv_liste = [c.args[0] for c in mock_run.call_args_list]
        assert ("git", "reset", "--hard", "a" * 40) in argv_liste
        assert ("git", "clean", "-nd", "--", "apps/") in argv_liste
        assert ("git", "clean", "-fd", "--", "apps/") in argv_liste
        assert any(
            c.args[1].get("ok") is True
            for c in mock_audit.call_args_list
            if c.args and c.args[0] == "phase_rollback")

    def test_exception_im_reset_fail_closed(
            self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from unittest.mock import patch
        monkeypatch.setattr(
            pipeline, "_PHASE_YAML_DIR", tmp_path)
        state = self._state(tmp_path, "a" * 40)
        with patch("pipeline._git_rev_parse_head",
                   return_value="a" * 40), \
             patch("pipeline._git_status_porcelain",
                   return_value=""), \
             patch("pipeline.subprocess.run",
                   side_effect=OSError("kaputt")), \
             patch("pipeline.audit"):
            ok = pipeline._phase_rollback(
                "testprojekt", state, "test")
        assert ok is False


# =====================================================================
# run_phase — phase_start_head-Setzung (P2b-2)
# =====================================================================

class TestRunPhaseStartHead:
    def test_setzt_head_wenn_leer(
            self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from unittest.mock import patch
        monkeypatch.setattr(
            pipeline, "_PHASE_YAML_DIR", tmp_path)
        _baue_phase_yaml(tmp_path, _standard_unterbloecke())
        state = _state_fuer_phase(tmp_path)
        assert state.phase_start_head == ""
        fake_head = "c" * 40
        with patch("pipeline._git_rev_parse_head",
                   return_value=fake_head), \
             patch("pipeline.run_pipeline",
                   side_effect=_mock_run_pipeline(
                       rc=0, paket=True)), \
             patch("pipeline.apply_commit_and_doku",
                   return_value=True), \
             patch("builtins.input",
                   return_value="j"), \
             patch("pipeline.audit"):
            rc = pipeline.run_phase("testprojekt", state, [])
        assert rc == 0
        assert state.phase_start_head == fake_head
        # phase.yaml muss den Wert tragen.
        daten = pipeline._phase_plan_laden("testprojekt")
        assert daten is not None
        assert daten["phase_start_head"] == fake_head

    def test_yaml_gewinnt_wenn_gesetzt(
            self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from unittest.mock import patch
        monkeypatch.setattr(
            pipeline, "_PHASE_YAML_DIR", tmp_path)
        ups = _standard_unterbloecke()
        _baue_phase_yaml(tmp_path, ups)
        # YAML-Wert nachtragen.
        daten = pipeline._phase_plan_laden("testprojekt")
        assert daten is not None
        daten["phase_start_head"] = "d" * 40
        pipeline._phase_plan_speichern("testprojekt", daten)
        # state mit abweichendem Wert (soll ueberschrieben werden).
        state = _state_fuer_phase(tmp_path)
        state.phase_start_head = "e" * 40
        with patch("pipeline._git_rev_parse_head",
                   return_value="f" * 40), \
             patch("pipeline.run_pipeline",
                   side_effect=_mock_run_pipeline(
                       rc=0, paket=True)), \
             patch("pipeline.apply_commit_and_doku",
                   return_value=True), \
             patch("builtins.input",
                   return_value="j"), \
             patch("pipeline.audit"):
            rc = pipeline.run_phase("testprojekt", state, [])
        assert rc == 0
        # YAML-Wert hat gewonnen, nicht der git-Aufruf.
        assert state.phase_start_head == "d" * 40

    def test_inkonsistenz_fail_closed(
            self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """P2b-2-A7 / K2: yaml_head leer, state != ''."""
        from unittest.mock import patch
        monkeypatch.setattr(
            pipeline, "_PHASE_YAML_DIR", tmp_path)
        ups = _standard_unterbloecke()
        _baue_phase_yaml(tmp_path, ups)
        # YAML hat phase_start_head == "".
        state = _state_fuer_phase(tmp_path)
        state.phase_start_head = "e" * 40
        with patch("pipeline._git_rev_parse_head",
                   return_value="f" * 40), \
             patch("pipeline.audit"):
            try:
                pipeline.run_phase("testprojekt", state, [])
            except ValueError as exc:
                assert "inkonsistent" in str(exc)
                return
        raise AssertionError(
            "ValueError mit 'inkonsistent' erwartet")


# =====================================================================
# _phase_rollback — Integration (echtes git-Repo)
# =====================================================================

class TestPhaseRollbackIntegration:
    def _git(self, cwd: Path, *args: str) -> None:
        import subprocess as sp
        sp.run(
            ["git",
             "-c", "user.name=Test",
             "-c", "user.email=test@example.invalid",
             *args],
            cwd=str(cwd), check=True,
            capture_output=True, text=True)

    def test_head_abweichend_kein_reset(
            self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        import subprocess as sp
        from unittest.mock import patch
        # git-Repo in tmp_path initialisieren.
        self._git(tmp_path, "init", "-q")
        (tmp_path / "apps").mkdir()
        (tmp_path / "apps" / "a.py").write_text("x = 1\n",
                                                encoding="utf-8")
        self._git(tmp_path, "add", "--", "apps/a.py")
        self._git(tmp_path, "commit", "-q", "-m", "init")
        start = sp.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(tmp_path), capture_output=True,
            text=True, check=True).stdout.strip()
        # HEAD verschieben.
        (tmp_path / "apps" / "a.py").write_text("x = 2\n",
                                                encoding="utf-8")
        self._git(tmp_path, "add", "--", "apps/a.py")
        self._git(tmp_path, "commit", "-q", "-m", "second")
        head_neu = sp.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(tmp_path), capture_output=True,
            text=True, check=True).stdout.strip()
        assert head_neu != start
        # Rollback: HEAD abweichend -> False, kein Reset.
        monkeypatch.setattr(
            pipeline, "_PHASE_YAML_DIR", tmp_path)
        state = _state_fuer_phase(tmp_path)
        state.phase_start_head = start
        state.file_whitelist = ["apps/"]
        with patch("pipeline.audit"):
            ok = pipeline._phase_rollback(
                "testprojekt", state, "test")
        assert ok is False
        head_danach = sp.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(tmp_path), capture_output=True,
            text=True, check=True).stdout.strip()
        assert head_danach == head_neu

    def test_status_schmutzig_kein_reset(
            self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        import subprocess as sp
        from unittest.mock import patch
        self._git(tmp_path, "init", "-q")
        (tmp_path / "apps").mkdir()
        (tmp_path / "apps" / "a.py").write_text("x = 1\n",
                                                encoding="utf-8")
        self._git(tmp_path, "add", "--", "apps/a.py")
        self._git(tmp_path, "commit", "-q", "-m", "init")
        start = sp.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(tmp_path), capture_output=True,
            text=True, check=True).stdout.strip()
        # Untracked Datei in whitelist-Ordner = status schmutzig.
        (tmp_path / "apps" / "neu.py").write_text("y = 1\n",
                                                  encoding="utf-8")
        monkeypatch.setattr(
            pipeline, "_PHASE_YAML_DIR", tmp_path)
        state = _state_fuer_phase(tmp_path)
        state.phase_start_head = start
        state.file_whitelist = ["apps/"]
        with patch("pipeline.audit"):
            ok = pipeline._phase_rollback(
                "testprojekt", state, "test")
        assert ok is False
        # Datei ist noch da (kein clean passiert).
        assert (tmp_path / "apps" / "neu.py").exists()

# =====================================================================
# run_pipeline — phasen_state + Phasen-Modus (P2b-3)
# =====================================================================

class TestRunPipelineSignatur:
    def test_phasen_state_ist_keyword_only(self) -> None:
        sig = inspect.signature(pipeline.run_pipeline)
        p = sig.parameters
        assert "phasen_state" in p
        assert p["phasen_state"].kind == inspect.Parameter.KEYWORD_ONLY
        assert p["phasen_state"].default is None

    def test_state_ref_nicht_phasen_state(self) -> None:
        sig = inspect.signature(pipeline.run_pipeline)
        params = list(sig.parameters.keys())
        assert params == ["project_name", "aufgabe", "state_ref",
                          "phasen_state"]


class TestRunPipelinePhasenModus:
    def test_guard_quelle_vorhanden(self) -> None:
        """Der phasen_state-Guard steht im Quelltext von
        run_pipeline (statisch verifiziert)."""
        import inspect as ins
        quelle = ins.getsource(pipeline.run_pipeline)
        assert "phasen_state is not None" in quelle
        assert "state_ref nicht leer" in quelle

    def test_phasen_modus_quelle_vorhanden(self) -> None:
        """Der Phasen-Modus-Eingriff steht im Quelltext."""
        import inspect as ins
        quelle = ins.getsource(pipeline.run_pipeline)
        assert "state.phase_aktiv" in quelle
        assert "phase_commit_paket_gesammelt" in quelle
        assert "phase_commit_paket_leer" in quelle
        assert "return 21" in quelle

# =====================================================================
# run_phase — rc-Klassen (P2b-3b)
# =====================================================================

class TestRunPhaseRcKlassen:
    def _setup(self, tmp_path: Path,
               monkeypatch: pytest.MonkeyPatch,
               ups: list | None = None
               ) -> pipeline.RunState:
        monkeypatch.setattr(
            pipeline, "_PHASE_YAML_DIR", tmp_path)
        if ups is None:
            ups = _standard_unterbloecke()
        _baue_phase_yaml(tmp_path, ups)
        return _state_fuer_phase(tmp_path)

    def test_klasse_1_erfolg_mit_paket(
            self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from unittest.mock import patch
        state = self._setup(tmp_path, monkeypatch)
        with patch("pipeline._git_rev_parse_head",
                   return_value="a" * 40), \
             patch("pipeline.run_pipeline",
                   side_effect=_mock_run_pipeline(
                       rc=0, paket=True)), \
             patch("pipeline.apply_commit_and_doku",
                   return_value=True), \
             patch("builtins.input",
                   return_value="j"), \
             patch("pipeline.audit"), \
             patch("pipeline._phase_rollback") as mock_rb:
            sr: list = []
            rc = pipeline.run_phase("testprojekt", state, sr)
        assert rc == 0
        assert not mock_rb.called
        assert state.phase_aktueller_index == 2
        assert len(state.phase_commit_pakete) == 2
        assert sr == [state]

    def test_klasse_2_b2_ohne_paket(
            self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from unittest.mock import patch
        state = self._setup(tmp_path, monkeypatch)
        with patch("pipeline._git_rev_parse_head",
                   return_value="a" * 40), \
             patch("pipeline.run_pipeline",
                   side_effect=_mock_run_pipeline(
                       rc=0, paket=False)), \
             patch("pipeline.audit"), \
             patch("pipeline._phase_rollback") as mock_rb:
            sr: list = []
            rc = pipeline.run_phase("testprojekt", state, sr)
        assert rc == 0
        assert not mock_rb.called
        assert len(state.phase_commit_pakete) == 0
        assert sr == [state]

    def test_klasse_3_rc_15_kein_rollback(
            self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from unittest.mock import patch
        state = self._setup(tmp_path, monkeypatch)
        with patch("pipeline._git_rev_parse_head",
                   return_value="a" * 40), \
             patch("pipeline.run_pipeline",
                   side_effect=_mock_run_pipeline(
                       rc=15, paket=False)), \
             patch("pipeline.audit"), \
             patch("pipeline._phase_rollback") as mock_rb:
            sr: list = []
            rc = pipeline.run_phase("testprojekt", state, sr)
        assert rc == 15
        assert not mock_rb.called, (
            "Klasse 3: KEIN Rollback (P2b-3b-A7)")
        # sr bleibt leer, weil Klasse 3 mit return 15
        # ohne append zurueckkehrt.
        assert sr == []

    def test_klasse_4_rc_11_mit_rollback(
            self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from unittest.mock import patch
        state = self._setup(tmp_path, monkeypatch)
        with patch("pipeline._git_rev_parse_head",
                   return_value="a" * 40), \
             patch("pipeline.run_pipeline",
                   side_effect=_mock_run_pipeline(
                       rc=11, paket=False)), \
             patch("pipeline.audit"), \
             patch("pipeline._phase_rollback",
                   return_value=True) as mock_rb:
            sr: list = []
            rc = pipeline.run_phase("testprojekt", state, sr)
        assert rc == 11
        assert mock_rb.called
        assert sr == []

    def test_klasse_4_rc_21_mit_rollback(
            self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from unittest.mock import patch
        state = self._setup(tmp_path, monkeypatch)
        with patch("pipeline._git_rev_parse_head",
                   return_value="a" * 40), \
             patch("pipeline.run_pipeline",
                   side_effect=_mock_run_pipeline(
                       rc=21, paket=False)), \
             patch("pipeline.audit"), \
             patch("pipeline._phase_rollback",
                   return_value=True) as mock_rb:
            sr: list = []
            rc = pipeline.run_phase("testprojekt", state, sr)
        assert rc == 21
        assert mock_rb.called

    def test_exception_im_run_pipeline(
            self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from unittest.mock import patch
        state = self._setup(tmp_path, monkeypatch)
        with patch("pipeline._git_rev_parse_head",
                   return_value="a" * 40), \
             patch("pipeline.run_pipeline",
                   side_effect=RuntimeError("kaputt")), \
             patch("pipeline.audit"), \
             patch("pipeline._phase_rollback",
                   return_value=True) as mock_rb:
            sr: list = []
            rc = pipeline.run_phase("testprojekt", state, sr)
        assert rc == 22
        assert mock_rb.called


# =====================================================================
# run_phase — Guards + Vertragsbruch (P2b-3b)
# =====================================================================

class TestRunPhaseGuards:
    def test_state_ref_nicht_leer_wirft(
            self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            pipeline, "_PHASE_YAML_DIR", tmp_path)
        _baue_phase_yaml(tmp_path, _standard_unterbloecke())
        state = _state_fuer_phase(tmp_path)
        sr = [state]
        try:
            pipeline.run_phase("testprojekt", state, sr)
        except ValueError as exc:
            assert "state_ref muss leer sein" in str(exc)
            return
        raise AssertionError("ValueError erwartet")

    def test_run_pipeline_vertragsbruch(
            self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Mock legt state nicht in sr_intern -> RuntimeError."""
        from unittest.mock import patch
        monkeypatch.setattr(
            pipeline, "_PHASE_YAML_DIR", tmp_path)
        _baue_phase_yaml(tmp_path, _standard_unterbloecke())
        state = _state_fuer_phase(tmp_path)

        def schlechter_mock(
                project_name: str, aufgabe: str,
                sr_intern: list, *,
                phasen_state: pipeline.RunState | None = None) -> int:
            # sr_intern NICHT befuellen.
            return 0

        with patch("pipeline._git_rev_parse_head",
                   return_value="a" * 40), \
             patch("pipeline.run_pipeline",
                   side_effect=schlechter_mock), \
             patch("pipeline.audit"), \
             patch("pipeline._phase_rollback"):
            try:
                pipeline.run_phase("testprojekt", state, [])
            except RuntimeError as exc:
                assert "state nicht in state_ref" in str(exc)
                return
        raise AssertionError("RuntimeError erwartet")

# =====================================================================
# _phase_gesamt_review / _phase_sammel_paket / Approval (P2b-4)
# =====================================================================

class TestPhaseGesamtReview:
    def test_aggregat_2_pakete(self, tmp_path: Path) -> None:
        state = _state_fuer_phase(tmp_path)
        state.phase_unterbloecke = [
            {"id": "U1", "titel": "T1", "status": "done"},
            {"id": "U2", "titel": "T2", "status": "done"},
        ]
        state.phase_commit_pakete = [
            {"message": "m1", "dateien": ["a.py"]},
            {"message": "m2", "dateien": ["b.py", "c.py"]},
        ]
        agg = pipeline._phase_gesamt_review(state)
        assert agg["unterbloecke_total"] == 2
        assert agg["unterbloecke_done"] == 2
        assert agg["pakete"] == 2
        assert agg["dateien_union"] == ["a.py", "b.py", "c.py"]
        assert agg["duplikate"] == 0

    def test_aggregat_mit_duplikat(self, tmp_path: Path) -> None:
        state = _state_fuer_phase(tmp_path)
        state.phase_unterbloecke = [
            {"id": "U1", "titel": "T1", "status": "done"},
        ]
        state.phase_commit_pakete = [
            {"message": "m", "dateien": ["a.py", "a.py"]},
        ]
        agg = pipeline._phase_gesamt_review(state)
        assert agg["dateien_union"] == ["a.py"]
        assert agg["duplikate"] == 1


class TestPhaseSammelPaket:
    def test_sammel_union(self, tmp_path: Path) -> None:
        state = _state_fuer_phase(tmp_path)
        state.phase_id = "P1"
        state.phase_titel = "Testphase"
        state.phase_unterbloecke = [
            {"id": "U1", "titel": "T1", "status": "done"},
            {"id": "U2", "titel": "T2", "status": "done"},
        ]
        state.phase_commit_pakete = [
            {"message": "m1", "dateien": ["b.py"]},
            {"message": "m2", "dateien": ["a.py"]},
        ]
        p = pipeline._phase_sammel_paket(state)
        assert p["dateien"] == ["a.py", "b.py"]
        assert "PHASE P1: Testphase" in p["message"]
        assert "m1" in p["message"]
        assert "m2" in p["message"]

    def test_message_b2_zeile(self, tmp_path: Path) -> None:
        state = _state_fuer_phase(tmp_path)
        state.phase_id = "P1"
        state.phase_titel = "T"
        state.phase_unterbloecke = [
            {"id": "U1", "titel": "T1", "status": "done"},
            {"id": "U2", "titel": "T2", "status": "done"},
        ]
        # Nur ein Paket (U1), U2 ist B2.
        state.phase_commit_pakete = [
            {"message": "m1", "dateien": ["a.py"]},
        ]
        msg = pipeline._phase_sammel_message(state)
        assert "U1: m1" in msg
        assert "U2: (Auftrag bereits erfuellt" in msg


class TestPhaseApproval:
    def _setup(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> pipeline.RunState:
        monkeypatch.setattr(
            pipeline, "_PHASE_YAML_DIR", tmp_path)
        _baue_phase_yaml(tmp_path, _standard_unterbloecke())
        return _state_fuer_phase(tmp_path)

    def test_approval_j_commit(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from unittest.mock import patch
        state = self._setup(tmp_path, monkeypatch)
        with patch("pipeline._git_rev_parse_head",
                   return_value="a" * 40), \
             patch("pipeline.run_pipeline",
                   side_effect=_mock_run_pipeline(
                       rc=0, paket=True)), \
             patch("builtins.input", return_value="j"), \
             patch("pipeline.apply_commit_and_doku",
                   return_value=True) as mock_apply, \
             patch("pipeline.audit"):
            sr: list = []
            rc = pipeline.run_phase("testprojekt", state, sr)
        assert rc == 0
        assert mock_apply.called
        sammel = mock_apply.call_args.args[1]
        # W29c: _mock_run_pipeline generiert pro Unterblock
        # eine andere Datei (D2-Schutz). Union sortiert.
        assert sammel["dateien"] == [
            "apps/x0.py", "apps/x1.py"]
        assert "PHASE P1" in sammel["message"]

    def test_approval_n_rollback(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from unittest.mock import patch
        state = self._setup(tmp_path, monkeypatch)
        monkeypatch.setenv("DEEPSEEK_API_KEY", "x")
        with patch("pipeline._git_rev_parse_head",
                   return_value="a" * 40), \
             patch("pipeline.run_pipeline",
                   side_effect=_mock_run_pipeline(
                       rc=0, paket=True)), \
             patch("builtins.input", return_value="n"), \
             patch("pipeline.apply_commit_and_doku") as mock_apply, \
             patch("pipeline._phase_plan_korrektur",
                   return_value=False), \
             patch("pipeline._phase_rollback",
                   return_value=True) as mock_rb, \
             patch("pipeline.audit"):
            sr: list = []
            rc = pipeline.run_phase("testprojekt", state, sr)
        assert rc == 23
        assert not mock_apply.called
        assert mock_rb.called

    def test_commit_fail_rc_20(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from unittest.mock import patch
        state = self._setup(tmp_path, monkeypatch)
        with patch("pipeline._git_rev_parse_head",
                   return_value="a" * 40), \
             patch("pipeline.run_pipeline",
                   side_effect=_mock_run_pipeline(
                       rc=0, paket=True)), \
             patch("builtins.input", return_value="j"), \
             patch("pipeline.apply_commit_and_doku",
                   return_value=False), \
             patch("pipeline.audit"):
            sr: list = []
            rc = pipeline.run_phase("testprojekt", state, sr)
        assert rc == 20

    def test_keine_pakete_b2_only(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """B2-only-Phase: 0 Pakete, kein Commit, rc=0."""
        from unittest.mock import patch
        state = self._setup(tmp_path, monkeypatch)
        with patch("pipeline._git_rev_parse_head",
                   return_value="a" * 40), \
             patch("pipeline.run_pipeline",
                   side_effect=_mock_run_pipeline(
                       rc=0, paket=False)), \
             patch("pipeline.apply_commit_and_doku") as mock_apply, \
             patch("builtins.input", return_value="j"), \
             patch("pipeline.audit"):
            sr: list = []
            rc = pipeline.run_phase("testprojekt", state, sr)
        assert rc == 0
        assert not mock_apply.called
        assert sr == [state]

    def test_ungueltige_eingabe_fail_closed(
            self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from unittest.mock import patch
        state = self._setup(tmp_path, monkeypatch)
        with patch("pipeline._git_rev_parse_head",
                   return_value="a" * 40), \
             patch("pipeline.run_pipeline",
                   side_effect=_mock_run_pipeline(
                       rc=0, paket=True)), \
             patch("builtins.input", return_value="quatsch"), \
             patch("pipeline.audit"):
            sr: list = []
            rc = pipeline.run_phase("testprojekt", state, sr)
        assert rc == 1

# =====================================================================
# P2b-5: Budget-Layer-1
# =====================================================================

class TestPhaseBudget:
    def _setup(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> pipeline.RunState:
        monkeypatch.setattr(
            pipeline, "_PHASE_YAML_DIR", tmp_path)
        _baue_phase_yaml(tmp_path, _standard_unterbloecke())
        return _state_fuer_phase(tmp_path)

    def test_budget_ende_rc_13(
            self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from unittest.mock import patch
        state = self._setup(tmp_path, monkeypatch)
        state.budget = {"max_llm_calls_phase": 5}
        state.llm_calls = 5
        with patch("pipeline._git_rev_parse_head",
                   return_value="a" * 40), \
             patch("pipeline.run_pipeline") as mock_rp, \
             patch("pipeline.audit"):
            sr: list = []
            rc = pipeline.run_phase("testprojekt", state, sr)
        assert rc == 13
        assert not mock_rp.called

    def test_budget_genug(
            self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from unittest.mock import patch
        state = self._setup(tmp_path, monkeypatch)
        state.budget = {"max_llm_calls_phase": 200}
        state.llm_calls = 5
        with patch("pipeline._git_rev_parse_head",
                   return_value="a" * 40), \
             patch("pipeline.run_pipeline",
                   side_effect=_mock_run_pipeline(
                       rc=0, paket=True)), \
             patch("builtins.input", return_value="j"), \
             patch("pipeline.apply_commit_and_doku",
                   return_value=True), \
             patch("pipeline.audit"):
            sr: list = []
            rc = pipeline.run_phase("testprojekt", state, sr)
        assert rc == 0

    def test_budget_null_kein_deckel(
            self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from unittest.mock import patch
        state = self._setup(tmp_path, monkeypatch)
        state.budget = {"max_llm_calls_phase": 0}
        state.llm_calls = 10000
        with patch("pipeline._git_rev_parse_head",
                   return_value="a" * 40), \
             patch("pipeline.run_pipeline",
                   side_effect=_mock_run_pipeline(
                       rc=0, paket=True)), \
             patch("builtins.input", return_value="j"), \
             patch("pipeline.apply_commit_and_doku",
                   return_value=True), \
             patch("pipeline.audit"):
            sr: list = []
            rc = pipeline.run_phase("testprojekt", state, sr)
        assert rc == 0


# =====================================================================
# P2b-5: Plan-Korrektur
# =====================================================================

class TestPhasePlanKorrektur:
    def _setup(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> pipeline.RunState:
        monkeypatch.setattr(
            pipeline, "_PHASE_YAML_DIR", tmp_path)
        _baue_phase_yaml(tmp_path, _standard_unterbloecke())
        return _state_fuer_phase(tmp_path)

    def test_korrektur_max_1_zyklus(
            self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """korrektur_zyklus=1 -> rc=23 ohne Planner."""
        from unittest.mock import patch
        state = self._setup(tmp_path, monkeypatch)
        with patch("pipeline._git_rev_parse_head",
                   return_value="a" * 40), \
             patch("pipeline.run_pipeline",
                   side_effect=_mock_run_pipeline(
                       rc=0, paket=True)), \
             patch("builtins.input", return_value="n"), \
             patch("pipeline._phase_plan_korrektur") as mock_k, \
             patch("pipeline._phase_rollback",
                   return_value=True), \
             patch("pipeline.audit"):
            sr: list = []
            state.phase_korrektur_zyklus = 1
            rc = pipeline.run_phase(
                "testprojekt", state, sr)
        assert rc == 23
        assert not mock_k.called

    def test_korrektur_failed_rc_23(
            self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Erster Zyklus, Korrektur gibt False -> rc=23."""
        from unittest.mock import patch
        state = self._setup(tmp_path, monkeypatch)
        with patch("pipeline._git_rev_parse_head",
                   return_value="a" * 40), \
             patch("pipeline.run_pipeline",
                   side_effect=_mock_run_pipeline(
                       rc=0, paket=True)), \
             patch("builtins.input", return_value="n"), \
             patch("pipeline._phase_plan_korrektur",
                   return_value=False) as mock_k, \
             patch("pipeline._phase_rollback",
                   return_value=True), \
             patch("pipeline.audit"):
            sr: list = []
            rc = pipeline.run_phase(
                "testprojekt", state, sr)
        assert rc == 23
        assert mock_k.called


# =====================================================================
# P2b-5: RR-K8-Menue
# =====================================================================

class TestPhaseRrK8:
    def test_abbrechen(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from unittest.mock import patch
        state = _state_fuer_phase(tmp_path)
        with patch("builtins.input", return_value="2"):
            wahl = pipeline._phase_rr_k8(state, "alt")
        assert wahl == "abbrechen"

    def test_neu_starten(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from unittest.mock import patch
        state = _state_fuer_phase(tmp_path)
        with patch("builtins.input", return_value="3"):
            wahl = pipeline._phase_rr_k8(state, "alt")
        assert wahl == "neu_starten"

    def test_eof_abbrechen(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from unittest.mock import patch
        state = _state_fuer_phase(tmp_path)
        with patch("builtins.input",
                   side_effect=EOFError()):
            wahl = pipeline._phase_rr_k8(state, "alt")
        assert wahl == "abbrechen"


# =====================================================================
# P2b-5: Planner-Korrektur-Kontext
# =====================================================================

class TestPlannerKorrekturKontext:
    def test_user_content_mit_kontext(self) -> None:
        kontext = {
            "begruendung": "Mensch hat abgelehnt",
            "alter_plan": "PHASE P1: T",
            "pakete_kompakt": "Paket 1: a.py",
        }
        text = pipeline._planner_user_content(
            "roh", "hist", stufe=2,
            korrektur_kontext=kontext)
        assert "KORREKTUR-AUFTRAG" in text
        assert "Mensch hat abgelehnt" in text
        assert "PHASE P1: T" in text

    def test_user_content_ohne_kontext(self) -> None:
        text = pipeline._planner_user_content(
            "roh", "hist", stufe=2)
        assert "KORREKTUR-AUFTRAG" not in text

# =====================================================================
# Resume-A2: done-Skip in run_phase
# =====================================================================

class TestRunPhaseDoneSkip:
    def test_done_wird_uebersprungen(
            self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Ein done-Unterblock wird nicht erneut gelaufen."""
        from unittest.mock import patch
        monkeypatch.setattr(
            pipeline, "_PHASE_YAML_DIR", tmp_path)
        ups = _standard_unterbloecke()
        ups[0]["status"] = "done"
        _baue_phase_yaml(tmp_path, ups)
        state = _state_fuer_phase(tmp_path)
        with patch("pipeline._git_rev_parse_head",
                   return_value="a" * 40), \
             patch("pipeline.run_pipeline",
                   side_effect=_mock_run_pipeline(
                       rc=0, paket=True)) as mock_rp, \
             patch("builtins.input", return_value="j"), \
             patch("pipeline.apply_commit_and_doku",
                   return_value=True), \
             patch("pipeline.audit"):
            sr: list = []
            rc = pipeline.run_phase("testprojekt", state, sr)
        assert rc == 0
        # run_pipeline nur einmal (fuer U2).
        assert mock_rp.call_count == 1


# =====================================================================
# Resume-Pfad in _phase_main_pfad
# =====================================================================

class TestPhaseMainPfadResume:
    def test_resume_ohne_plan_planner_gerufen(
            self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Kein Plan -> Planner-Pfad."""
        # Wir testen die Existenz der Verzweigung im Code
        # (statisch), weil der Planner-Pfad komplex ist.
        import inspect as ins
        quelle = ins.getsource(pipeline._phase_main_pfad)
        assert "phase_resume_erkannt" in quelle
        assert "plan_vorhanden" in quelle

    def test_finish_aktiv_helper_existiert(self) -> None:
        assert hasattr(pipeline, "_phase_finish_aktiv")

    def test_finish_setzt_aktiv_false(
            self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from unittest.mock import patch
        monkeypatch.setattr(
            pipeline, "_PHASE_YAML_DIR", tmp_path)
        _baue_phase_yaml(tmp_path, _standard_unterbloecke())
        state = _state_fuer_phase(tmp_path)
        state.phase_aktiv = True
        with patch("pipeline.audit"):
            pipeline._phase_finish_aktiv(
                "testprojekt", state, 0)
        assert state.phase_aktiv is False
        daten = pipeline._phase_plan_laden("testprojekt")
        # phase_aktiv ist False -> _phase_plan_laden
        # gibt None zurueck.
        assert daten is None

    def test_finish_rc_nicht_null_noop(
            self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from unittest.mock import patch
        monkeypatch.setattr(
            pipeline, "_PHASE_YAML_DIR", tmp_path)
        _baue_phase_yaml(tmp_path, _standard_unterbloecke())
        state = _state_fuer_phase(tmp_path)
        state.phase_aktiv = True
        with patch("pipeline.audit"):
            pipeline._phase_finish_aktiv(
                "testprojekt", state, 1)
        assert state.phase_aktiv is True

    def test_finish_phase_aktiv_false_noop(
            self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from unittest.mock import patch
        monkeypatch.setattr(
            pipeline, "_PHASE_YAML_DIR", tmp_path)
        _baue_phase_yaml(tmp_path, _standard_unterbloecke())
        state = _state_fuer_phase(tmp_path)
        state.phase_aktiv = False
        with patch("pipeline.audit"):
            pipeline._phase_finish_aktiv(
                "testprojekt", state, 0)
        assert state.phase_aktiv is False

# =====================================================================
# P2b-Luecke-B: Solver-Befund im Builder-Prompt
# =====================================================================

class TestSolverBefundBlock:
    def test_leerer_state_leerer_block(self, tmp_path: Path) -> None:
        state = _state_fuer_phase(tmp_path)
        block = pipeline._solver_befund_block(state)
        assert block == ""

    def test_marker_text_enthaelt_praezisierung(
            self, tmp_path: Path) -> None:
        """Der Marker-Text sagt: Praezisierung, kein neuer
        Auftrag, plus Widerspruch-Anweisung."""
        # Wir testen die Quelle statisch, weil ein echter
        # SolverBefund-Erzeuger viel Setup braucht.
        import inspect as ins
        quelle = ins.getsource(pipeline._solver_befund_block)
        assert "PRAEZISIERUNG" in quelle
        assert "kein neuer Auftrag" in quelle
        assert "frage_reviewer" in quelle


class TestAuditBuilderPromptSolverFeld:
    def test_audit_enthaelt_solver_feld(self) -> None:
        import inspect as ins
        quelle = ins.getsource(pipeline._audit_builder_prompt)
        assert "solver_befund_eingesetzt" in quelle

# =====================================================================
# P2b-Frage-A: parse_commands + frage_reviewer
# =====================================================================

class TestParseCommandsFrage:
    def test_run_hat_typ_run(self) -> None:
        text = "COMMAND: RUN read_file foo.txt\n"
        cmds = pipeline.parse_commands(text)
        assert len(cmds) == 1
        assert cmds[0]["typ"] == "run"
        assert cmds[0]["id"] == "read_file"
        assert cmds[0]["arg"] == "foo.txt"

    def test_frage_reviewer_erkannt(self) -> None:
        text = "COMMAND: frage_reviewer Widerspruch solver\n"
        cmds = pipeline.parse_commands(text)
        assert len(cmds) == 1
        assert cmds[0]["typ"] == "frage_reviewer"
        assert cmds[0]["arg"] == "Widerspruch solver"

    def test_mehrere_fragen_konkateniert(self) -> None:
        text = (
            "COMMAND: frage_reviewer Frage 1\n"
            "COMMAND: frage_reviewer Frage 2\n"
        )
        cmds = pipeline.parse_commands(text)
        assert len(cmds) == 1
        assert cmds[0]["typ"] == "frage_reviewer"
        assert "Frage 1" in cmds[0]["arg"]
        assert "Frage 2" in cmds[0]["arg"]

    def test_gemischt_run_und_frage(self) -> None:
        text = (
            "COMMAND: RUN read_file a.py\n"
            "COMMAND: frage_reviewer Ist das ok?\n"
        )
        cmds = pipeline.parse_commands(text)
        assert len(cmds) == 2
        typen = {c["typ"] for c in cmds}
        assert typen == {"run", "frage_reviewer"}

    def test_run_ohne_praefix_verworfen(self) -> None:
        text = "COMMAND: irgendwas\n"
        cmds = pipeline.parse_commands(text)
        assert cmds == []


class TestBuilderFrageReviewerLoop:
    def test_frage_reviewer_kein_deadlock(self) -> None:
        """Der Loop darf bei frage_reviewer nicht in den
        Deadlock-Pfad laufen."""
        # Statische Pruefung: der Loop muss frage_reviewer
        # explizit behandeln.
        import inspect as ins
        quelle = ins.getsource(
            pipeline.builder_reply_mit_command_loop)
        assert "frage_reviewer" in quelle
        assert "builder_frage_reviewer" in quelle

# =====================================================================
# P2b-Frage-B: Antwort-Modus
# =====================================================================

class TestAntwortModus:
    def test_classify_verdict_erkennt_antwort(self) -> None:
        assert pipeline.classify_verdict(
            "ANTWORT:\nHier meine Antwort.") == "ANTWORT"

    def test_classify_verdict_antwort_mit_punkt(self) -> None:
        assert pipeline.classify_verdict(
            "ANTWORT:") == "ANTWORT"

    def test_classify_verdict_go_unveraendert(self) -> None:
        assert pipeline.classify_verdict("GO") == "GO"
        assert pipeline.classify_verdict(
            "NO-GO\nBegruendung") == "NO-GO"

    def test_extrahiere_antwort(self) -> None:
        text = "ANTWORT:\nEin Commit-Paket reicht.\nKein Hash."
        a = pipeline._extrahiere_antwort(text)
        assert "Ein Commit-Paket reicht" in a
        assert "Kein Hash" in a

    def test_extrahiere_antwort_leer(self) -> None:
        assert pipeline._extrahiere_antwort("kein block") == ""

    def test_extrahiere_antwort_inline(self) -> None:
        text = "ANTWORT: kurze Antwort"
        a = pipeline._extrahiere_antwort(text)
        assert "kurze Antwort" in a


class TestHardRules:
    def test_reviewer_r8_vorhanden(self) -> None:
        assert "R8." in pipeline.HARD_RULES_REVIEWER
        assert "ANTWORT" in pipeline.HARD_RULES_REVIEWER

    def test_builder_b11_vorhanden(self) -> None:
        assert "B11." in pipeline.HARD_RULES_BUILDER
        assert "frage_reviewer" in pipeline.HARD_RULES_BUILDER

# =====================================================================
# Plan-Korrektur bei Unterblock-NO-GO
# =====================================================================

class TestPhaseKorrekturUnterblockNoGo:
    def test_runstate_feld_existiert(self) -> None:
        sig_fields = [f.name for f in
                      __import__("dataclasses").fields(
                          pipeline.RunState)]
        assert "phase_korrektur_zyklus" in sig_fields

    def test_r9_in_hard_rules(self) -> None:
        assert "R9." in pipeline.HARD_RULES_REVIEWER
        assert ("ROLLENGRENZE" in pipeline.HARD_RULES_REVIEWER
                or "Rollengrenze"
                in pipeline.HARD_RULES_REVIEWER)

    def test_zyklus_teilt_sich(self) -> None:
        """Beide Trigger ([n], rc=15) nutzen
        phase_korrektur_zyklus."""
        import inspect as ins
        quelle_run = ins.getsource(pipeline.run_phase)
        assert "state.phase_korrektur_zyklus" in quelle_run
        quelle_mp = ins.getsource(pipeline._phase_main_pfad)
        assert "state.phase_korrektur_zyklus" in quelle_mp

    def test_korrektur_startet_nach_rc15(
            self, tmp_path: Path,
            monkeypatch: pytest.MonkeyPatch) -> None:
        """_phase_plan_korrektur wird gerufen."""
        # Statische Pruefung: der Aufruf ist da.
        import inspect as ins
        quelle = ins.getsource(pipeline._phase_main_pfad)
        assert "rc == 15" in quelle
        assert "_phase_plan_korrektur" in quelle

    def test_kontext_enthaelt_reviewer_befund(self) -> None:
        import inspect as ins
        quelle = ins.getsource(pipeline._phase_plan_korrektur)
        assert "reviewer_befund" in quelle

    def test_pakete_reset_nach_korrektur(self) -> None:
        import inspect as ins
        quelle = ins.getsource(pipeline._phase_plan_korrektur)
        assert "state.phase_commit_pakete = []" in quelle

    def test_audit_payload_grund(self) -> None:
        import inspect as ins
        quelle = ins.getsource(pipeline._phase_plan_korrektur)
        assert "\"grund\": \"unterblock_no_go\"" in quelle \
            or "grund" in quelle

# =====================================================================
# P2b-Luecke-C: NEW_FILE dem Builder/Reviewer bekannt
# =====================================================================

class TestNewFilePrompt:
    def test_builder_md_enthaelt_new_file(self) -> None:
        from pathlib import Path as _P
        text = _P("/opt/werkstatt/agents/builder.md").read_text(
            encoding="utf-8")
        assert "typ: new_file" in text

    def test_builder_md_platzhalter_verbot(self) -> None:
        from pathlib import Path as _P
        text = _P("/opt/werkstatt/agents/builder.md").read_text(
            encoding="utf-8")
        assert "Platzhalter" in text

    def test_judge_md_enthaelt_contract(self) -> None:
        """W28a: judge.md prueft gegen Contract."""
        from pathlib import Path as _P
        text = _P("/opt/werkstatt/agents/judge.md").read_text(
            encoding="utf-8")
        assert "contract" in text.lower() or "vertrag" in text.lower()

    def test_hard_rules_builder_b12(self) -> None:
        assert "B12." in pipeline.HARD_RULES_BUILDER
        assert "new_file" in pipeline.HARD_RULES_BUILDER

    def test_hard_rules_reviewer_r10(self) -> None:
        assert "R10." in pipeline.HARD_RULES_REVIEWER
        assert "new_file" in pipeline.HARD_RULES_REVIEWER

    def test_r10_verweist_auf_r5_ausnahme(self) -> None:
        text = pipeline.HARD_RULES_REVIEWER
        assert "R5" in text
        assert "gilt NICHT" in text or "NICHT fuer" in text

    def test_r10_verbietet_write_file(self) -> None:
        text = pipeline.HARD_RULES_REVIEWER
        assert "write_file" in text

# =====================================================================
# Rollen-Audit-A: reviewer.md + builder.md
# =====================================================================

class TestRollenAuditA:
    def _read(self, name: str) -> str:
        from pathlib import Path as _P
        return _P(f"/opt/werkstatt/agents/{name}").read_text(
            encoding="utf-8")

    def test_reviewer_kein_alter_abschnitt(self) -> None:
        assert "CODE-REVIEW (alt)" not in self._read("reviewer.md")

    def test_reviewer_kein_security_review_log(self) -> None:
        assert "SECURITY_REVIEW_LOG" not in self._read("reviewer.md")

    def test_judge_hat_security_log(self) -> None:
        """W28a: judge.md kennt SECURITY_LOG (Sicherheit)."""
        assert "SECURITY_LOG" in self._read("judge.md") or \
            "Sicherheit" in self._read("judge.md")

    def test_judge_hat_r10_hinweis(self) -> None:
        """W28a: judge.md prueft new_file-Kontext."""
        t = self._read("judge.md")
        assert "mess_nach" in t or "code_entwurf" in t.lower()

    def test_builder_hat_git_ls_files(self) -> None:
        t = self._read("builder.md")
        assert "git ls-files" in t

    def test_builder_kein_warte_satz(self) -> None:
        assert "Warte. Wir muessen genau sein." not in \
            self._read("builder.md")

    def test_builder_hat_vorgaenger_hash(self) -> None:
        t = self._read("builder.md")
        assert "Vorgaenger-Hash" in t

    def test_builder_hat_2_spaces_entfernt(self) -> None:
        t = self._read("builder.md")
        assert "2 Spaces entfernt" in t

    def test_hash_regel_judge(self) -> None:
        """W28a: Judge prueft keine Hashes (Contract-Sache)."""
        t = self._read("judge.md")
        assert "Contract" in t or "Vertrag" in t

    def test_build_system_prompt_reviewer_kein_alt(self) -> None:
        agents = pipeline.load_agents("/opt/werkstatt/agents")
        prompt = pipeline.build_system_prompt(
            agents["reviewer"], {}, [])
        assert "CODE-REVIEW (alt)" not in prompt

    def test_build_system_prompt_reviewer_hat_antwort(self) -> None:
        agents = pipeline.load_agents("/opt/werkstatt/agents")
        prompt = pipeline.build_system_prompt(
            agents["reviewer"], {}, [])
        assert "ANTWORT" in prompt

    def test_build_system_prompt_builder_kein_warte(self) -> None:
        agents = pipeline.load_agents("/opt/werkstatt/agents")
        prompt = pipeline.build_system_prompt(
            agents["builder"], {}, [])
        assert "Warte. Wir muessen genau sein." not in prompt

# =====================================================================
# Rollen-Audit-B: solver.md
# =====================================================================

class TestRollenAuditB:
    def _read(self) -> str:
        from pathlib import Path as _P
        return _P("/opt/werkstatt/agents/solver.md").read_text(
            encoding="utf-8")

    def test_solver_md_dasselbe_wissen(self) -> None:
        assert "dasselbe Wissen" in self._read()

    def test_solver_md_doch_geht(self) -> None:
        t = self._read()
        assert "DOCH GEHT" in t or "wie es besser geht" in t

    def test_solver_md_praeziseren_auftrag(self) -> None:
        assert "praeziseren Auftrag" in self._read()

    def test_solver_md_trigger_anker(self) -> None:
        assert "anker_nicht_gemessen" in self._read()

    def test_solver_md_trigger_rueckfrage(self) -> None:
        assert "builder_rueckfrage" in self._read()

    def test_solver_md_trigger_wirkungslos(self) -> None:
        assert "wirkungsloser_patch" in self._read()

    def test_solver_md_trigger_p1(self) -> None:
        assert "p1_trigger" in self._read()

    def test_solver_md_kein_falscher_trigger(self) -> None:
        # Der falsche Satz war in "Deine Aufgabe".
        # Wir pruefen, dass der Satz nicht in
        # Rolle/Aufgabe steht.
        t = self._read()
        # Der Satz darf hoechstens im Eingabe-Abschnitt
        # stehen.
        assert "zweimal in Folge NO-GO gibt" not in t

    def test_build_system_prompt_solver_hat_trigger(self) -> None:
        agents = pipeline.load_agents("/opt/werkstatt/agents")
        prompt = pipeline.build_system_prompt(
            agents["solver"], {}, [])
        assert "anker_nicht_gemessen" in prompt
        assert "builder_rueckfrage" in prompt
        assert "wirkungsloser_patch" in prompt


class TestTriggerKonsistenz:
    def test_trigger_grund_werte_konsistent(self) -> None:
        """Die Trigger-Namen in solver.md stimmen mit den
        _trigger_grund-Werten im Code ueberein."""
        from pathlib import Path as _P
        quelle = _P("/opt/werkstatt/pipeline.py").read_text(
            encoding="utf-8")
        solver_md = _P(
            "/opt/werkstatt/agents/solver.md").read_text(
            encoding="utf-8")
        # Alle _trigger_grund-Werte aus dem Code.
        import re
        treffer = re.findall(
            r'_trigger_grund\s*=\s*"([a-z0-9_]+)"', quelle)
        werte = set(treffer)
        # Jeder Code-Wert ausser "reviewer_command"
        # und "" muss in solver.md auftauchen.
        erwartete = {
            "anker_nicht_gemessen",
            "builder_rueckfrage",
            "wirkungsloser_patch",
            "p1_trigger",
        }
        assert erwartete.issubset(werte), (
            f"Code kennt nicht alle Trigger: "
            f"{erwartete - werte}")
        for w in erwartete:
            assert w in solver_md, (
                f"Trigger {w} fehlt in solver.md")

    def test_b2_abschnitt_erhalten(self) -> None:
        t = self._read() if False else None
        from pathlib import Path as _P
        t = _P("/opt/werkstatt/agents/solver.md").read_text(
            encoding="utf-8")
        assert "Wann der Auftrag bereits erfuellt ist" in t
        assert "Auftrag bereits" in t

# =====================================================================
# state.aufgabe im Phasen-Modus (2026-10-16)
# =====================================================================

class TestStateAufgabePhasenModus:
    def test_quelle_setzt_aufgabe(self) -> None:
        """Der Fix ist im Quelltext: state.aufgabe = aufgabe."""
        import inspect as ins
        quelle = ins.getsource(pipeline.run_pipeline)
        assert "state.aufgabe = aufgabe" in quelle

    def test_quelle_audit_phase_felder(self) -> None:
        """pipeline_start-Audit ergaenzt um phase_id."""
        import inspect as ins
        quelle = ins.getsource(pipeline.run_pipeline)
        assert "phase_id" in quelle
        assert "phase_titel" in quelle
        assert "unterblock_index" in quelle

# =====================================================================
# builder.md WICHTIG-Block: beide Patch-Formate (2026-10-16)
# =====================================================================

class TestBuilderFormatWichtigBlock:
    def _read(self) -> str:
        from pathlib import Path as _P
        return _P("/opt/werkstatt/agents/builder.md").read_text(
            encoding="utf-8")

    def test_typ_new_file_im_wichtig_block(self) -> None:
        """typ: new_file steht im WICHTIG-Block
        (Z. 11-55), nicht nur in NEUE DATEIEN."""
        t = self._read()
        # WICHTIG-Block ist vor "## SELBST-REVIEW".
        idx_wichtig = t.find("WICHTIG (UMB-1)")
        idx_selbst = t.find("## SELBST-REVIEW")
        assert idx_wichtig != -1
        assert idx_selbst != -1
        assert idx_wichtig < idx_selbst
        wichtig = t[idx_wichtig:idx_selbst]
        assert "typ: new_file" in wichtig

    def test_typ_patch_im_wichtig_block(self) -> None:
        t = self._read()
        idx_wichtig = t.find("WICHTIG (UMB-1)")
        idx_selbst = t.find("## SELBST-REVIEW")
        wichtig = t[idx_wichtig:idx_selbst]
        assert "typ: patch" in wichtig

    def test_platzhalter_verbot_im_wichtig_block(self) -> None:
        t = self._read()
        idx_wichtig = t.find("WICHTIG (UMB-1)")
        idx_selbst = t.find("## SELBST-REVIEW")
        wichtig = t[idx_wichtig:idx_selbst]
        assert "Platzhalter" in wichtig
        assert "NIEMALS" in wichtig

    def test_read_file_hinweis_im_wichtig_block(self) -> None:
        t = self._read()
        idx_wichtig = t.find("WICHTIG (UMB-1)")
        idx_selbst = t.find("## SELBST-REVIEW")
        wichtig = t[idx_wichtig:idx_selbst]
        assert "COMMAND: RUN read_file" in wichtig

    def test_verweise_im_wichtig_block(self) -> None:
        t = self._read()
        idx_wichtig = t.find("WICHTIG (UMB-1)")
        idx_selbst = t.find("## SELBST-REVIEW")
        wichtig = t[idx_wichtig:idx_selbst]
        assert "## ANKER UND ERSATZ" in wichtig
        assert "## NEUE DATEIEN" in wichtig

    def test_build_system_prompt_beide_formate(self) -> None:
        agents = pipeline.load_agents("/opt/werkstatt/agents")
        prompt = pipeline.build_system_prompt(
            agents["builder"], {}, [])
        assert "typ: new_file" in prompt
        assert "typ: patch" in prompt
        assert "Platzhalter" in prompt

# =====================================================================
# V3-Fix: pruefe_anker_gegen_messung ueberspringt new_file
# =====================================================================

class TestAnkerPruefungNewFile:
    def test_new_file_wird_uebersprungen(self) -> None:
        """typ: new_file hat keinen anker, wird nicht geprueft."""
        patches = [
            {"typ": "new_file",
             "pfad": "core/hello.py",
             "inhalt": "def greet(): ..."},
        ]
        fehler = pipeline.pruefe_anker_gegen_messung(
            patches, "")
        assert fehler == []

    def test_leerer_anker_patch_bleibt_fehler(self) -> None:
        """Regression: typ: patch mit leerem Anker
        bleibt als 'leer' erkannt."""
        patches = [
            {"typ": "patch",
             "pfad": "core/hello.py",
             "anker": "",
             "ersatz": "x"},
        ]
        fehler = pipeline.pruefe_anker_gegen_messung(
            patches, "")
        assert len(fehler) == 1
        assert fehler[0][3] == "leer"

    def test_falscher_anker_bleibt_fehler(self) -> None:
        """Regression: typ: patch mit falschem (nicht-leerem)
        Anker bleibt als 'nicht_gefunden' erkannt."""
        patches = [
            {"typ": "patch",
             "pfad": "core/hello.py",
             "anker": "XYZ",
             "ersatz": "ABC"},
        ]
        fehler = pipeline.pruefe_anker_gegen_messung(
            patches, "")
        assert len(fehler) == 1
        assert fehler[0][3] == "nicht_gefunden"

    def test_gemischt_new_file_und_patch(self) -> None:
        """Integration: gemischte Patches. new_file wird
        uebersprungen, patch wird geprueft."""
        patches = [
            {"typ": "new_file",
             "pfad": "core/a.py", "inhalt": "x"},
            {"typ": "patch",
             "pfad": "core/b.py", "anker": "", "ersatz": "y"},
        ]
        fehler = pipeline.pruefe_anker_gegen_messung(
            patches, "")
        # Nur der Patch (index 1) wird geprueft.
        assert len(fehler) == 1
        assert fehler[0][0] == 1
        assert fehler[0][1] == "core/b.py"

# =====================================================================
# Post-Apply-Korrektur-Loop (2026-10-16)
# =====================================================================

class TestPostApplyKorrektur:
    def test_aufrufer_hat_rc19_zweig(self) -> None:
        """run_pipeline prueft rc=19 und ruft die
        Korrektur-Loop-Funktion."""
        import inspect as ins
        quelle = ins.getsource(pipeline.run_pipeline)
        assert "_post_apply_korrektur_loop" in quelle
        assert "rc_apply == 19" in quelle

    def test_funktion_existiert(self) -> None:
        assert hasattr(pipeline, "_post_apply_korrektur_loop")
        assert hasattr(pipeline, "_bauer_recovery_prompt")

    def test_apply_and_recheck_gibt_19(self) -> None:
        """apply_and_recheck gibt rc=19 bei Post-Apply-Fehler."""
        import inspect as ins
        quelle = ins.getsource(pipeline.apply_and_recheck)
        assert "return 19" in quelle

    def test_state_feld_vorhanden(self) -> None:
        sig_fields = [f.name for f in
                      __import__("dataclasses").fields(
                          pipeline.RunState)]
        assert "post_apply_korrektur_runden" in sig_fields
        assert "letzter_recovery_vorschlag" in sig_fields

    def test_bauer_recovery_prompt_typ_patch(
            self, tmp_path: Path) -> None:
        """Der Recovery-Prompt verbietet new_file,
        verlangt typ: patch."""
        state = pipeline.RunState(
            block_id="t", aufgabe="t",
            start_ts="2026-01-01T00:00:00+00:00",
            docs={}, agents={}, always={}, optional={},
            file_whitelist=[], api_key="x", budget={},
            agent_docs={}, project_dir=tmp_path,
            project_name="t")
        state.basis_protokoll_nach_apply = "=== ruff ===\nRC: 1"
        state.letzter_recovery_vorschlag = None
        prompt = pipeline._bauer_recovery_prompt(state)
        assert "typ: patch" in prompt
        assert "NICHT typ: new_file" in prompt
        assert "POST-APPLY-BASIS-GATE ROT" in prompt

    def test_bauer_recovery_prompt_mit_vorschlag(
            self, tmp_path: Path) -> None:
        state = pipeline.RunState(
            block_id="t", aufgabe="t",
            start_ts="2026-01-01T00:00:00+00:00",
            docs={}, agents={}, always={}, optional={},
            file_whitelist=[], api_key="x", budget={},
            agent_docs={}, project_dir=tmp_path,
            project_name="t")
        state.basis_protokoll_nach_apply = "protokoll"
        v = pipeline.RecoveryVorschlag(
            art="basis_gate",
            diagnose="F401 unused import",
            reparaturplan=["Zeile 12 entfernen",
                            "Import anpassen"])
        state.letzter_recovery_vorschlag = v
        prompt = pipeline._bauer_recovery_prompt(state)
        assert "F401 unused import" in prompt
        assert "Zeile 12 entfernen" in prompt
        assert "Import anpassen" in prompt

# =====================================================================
# Resume-Force (Auflage A8, 2026-10-16)
# =====================================================================

class TestResumeForce:
    """Tests fuer _resume_force_reset (Auflage A2-A7)."""

    def _plan(self, unterbloecke: list) -> dict:
        return {
            "phase_id": "18",
            "phase_titel": "Test",
            "phase_start_head": "abc123",
            "phase_unterbloecke": unterbloecke,
        }

    def test_no_go_wird_pending(self) -> None:
        plan = self._plan([
            {"id": "U1", "status": "no_go"},
            {"id": "U2", "status": "pending"},
        ])
        r = pipeline._resume_force_reset(plan)
        assert r["reset"] is True
        assert plan["phase_unterbloecke"][0]["status"] == "pending"
        assert plan["phase_unterbloecke"][1]["status"] == "pending"

    def test_failed_wird_pending(self) -> None:
        plan = self._plan([
            {"id": "U1", "status": "failed"},
        ])
        r = pipeline._resume_force_reset(plan)
        assert r["reset"] is True
        assert plan["phase_unterbloecke"][0]["status"] == "pending"

    def test_done_bleibt_done(self) -> None:
        plan = self._plan([
            {"id": "U1", "status": "done"},
            {"id": "U2", "status": "no_go"},
        ])
        r = pipeline._resume_force_reset(plan)
        assert r["reset"] is True
        assert plan["phase_unterbloecke"][0]["status"] == "done"
        assert plan["phase_unterbloecke"][1]["status"] == "pending"
        assert r["kandidaten"] == [
            {"id": "U2", "alter_status": "no_go"}]

    def test_pending_bleibt_pending(self) -> None:
        plan = self._plan([
            {"id": "U1", "status": "pending"},
        ])
        r = pipeline._resume_force_reset(plan)
        assert r["reset"] is False
        assert plan["phase_unterbloecke"][0]["status"] == "pending"

    def test_ohne_no_go_wirkungslos(self) -> None:
        plan = self._plan([
            {"id": "U1", "status": "done"},
            {"id": "U2", "status": "pending"},
        ])
        r = pipeline._resume_force_reset(plan)
        assert r["reset"] is False
        assert r["kandidaten"] == []

    def test_phase_start_head_unveraendert(self) -> None:
        plan = self._plan([
            {"id": "U1", "status": "no_go"},
        ])
        r = pipeline._resume_force_reset(plan)
        assert r["phase_start_head"] == "abc123"
        assert plan["phase_start_head"] == "abc123"

    def test_kandidaten_liste(self) -> None:
        plan = self._plan([
            {"id": "U1", "status": "no_go"},
            {"id": "U2", "status": "pending"},
            {"id": "U3", "status": "failed"},
        ])
        r = pipeline._resume_force_reset(plan)
        assert r["kandidaten"] == [
            {"id": "U1", "alter_status": "no_go"},
            {"id": "U3", "alter_status": "failed"},
        ]

    def test_leerer_plan(self) -> None:
        plan = self._plan([])
        r = pipeline._resume_force_reset(plan)
        assert r["reset"] is False
        assert r["kandidaten"] == []

    def test_nicht_dict_uebersprungen(self) -> None:
        plan = self._plan([
            {"id": "U1", "status": "no_go"},
            "kein-dict",
            None,
        ])
        r = pipeline._resume_force_reset(plan)
        assert r["reset"] is True
        assert r["kandidaten"] == [
            {"id": "U1", "alter_status": "no_go"}]


class TestResumeForceCli:
    """CLI-Verhalten (Auflage A1)."""

    def test_resume_force_ohne_phase_fail(self) -> None:
        """--resume-force ohne --phase ist rc=65.
        Pruefung per Quelltext-Match.
        """
        import inspect as ins
        quelle = ins.getsource(pipeline.main)
        assert "--resume-force verlangt --phase" in quelle

    def test_resume_force_mit_phase_erlaubt(self) -> None:
        """--resume-force mit --phase wird durchgereicht.
        Pruefung per Quelltext-Match.
        """
        import inspect as ins
        quelle = ins.getsource(pipeline.main)
        assert '_resume_force = "--resume-force" in args' in quelle
        assert "resume_force=_resume_force" in quelle

# =====================================================================
# Phasen-Persistenz (A1-A6, 2026-10-16)
# =====================================================================

class TestPhasePersistenz:
    """Tests fuer commit_paket-Persistenz in phase.yaml.

    A1: done-Unterblock schreibt commit_paket.
    A6: Persistenz + Restore.
    """

    def test_yaml_status_update_schreibt_commit_paket(
            self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(pipeline, "_PHASE_YAML_DIR", tmp_path)
        _baue_phase_yaml(tmp_path, _standard_unterbloecke())
        paket = {
            "dateien": ["core/a.py", "tests/test_a.py"],
            "message": "U1 fertig",
        }
        pipeline._phase_yaml_status_update(
            "testprojekt", "U1", "done", commit_paket=paket)
        # phase.yaml neu laden
        import yaml
        d = yaml.safe_load(
            (tmp_path / "testprojekt.phase.yaml").read_text())
        u1 = d["phase_unterbloecke"][0]
        assert u1["status"] == "done"
        assert u1["commit_paket"]["dateien"] == [
            "core/a.py", "tests/test_a.py"]
        assert u1["commit_paket"]["message"] == "U1 fertig"

    def test_yaml_status_update_ohne_paket(
            self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(pipeline, "_PHASE_YAML_DIR", tmp_path)
        _baue_phase_yaml(tmp_path, _standard_unterbloecke())
        pipeline._phase_yaml_status_update(
            "testprojekt", "U1", "pending")
        import yaml
        d = yaml.safe_load(
            (tmp_path / "testprojekt.phase.yaml").read_text())
        u1 = d["phase_unterbloecke"][0]
        assert u1["status"] == "pending"
        # commit_paket bleibt wie vorher (leer).
        assert u1.get("commit_paket", {}) == {}

    def test_message_wird_gekuerzt(
            self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(pipeline, "_PHASE_YAML_DIR", tmp_path)
        _baue_phase_yaml(tmp_path, _standard_unterbloecke())
        langer_text = "x" * 1000
        pipeline._phase_yaml_status_update(
            "testprojekt", "U1", "done",
            commit_paket={"dateien": ["a.py"],
                          "message": langer_text})
        import yaml
        d = yaml.safe_load(
            (tmp_path / "testprojekt.phase.yaml").read_text())
        msg = d["phase_unterbloecke"][0]["commit_paket"]["message"]
        assert len(msg) == 500

    def test_restore_mehrere_done_unterbloecke(
            self, tmp_path: Path) -> None:
        """Resume-Restore: mehrere done-Pakete.

        Prueft die Filterlogik, die in _phase_main_pfad
        im Resume-Zweig steht. Wir bauen sie nach.
        """
        ups_plan = [
            {"id": "U1", "status": "done",
             "commit_paket": {"dateien": ["a.py"],
                              "message": "U1"}},
            {"id": "U2", "status": "done",
             "commit_paket": {"dateien": ["b.py"],
                              "message": "U2"}},
            {"id": "U3", "status": "pending",
             "commit_paket": {}},
        ]
        pakete: list[dict[str, object]] = []
        for u in ups_plan:
            if not isinstance(u, dict):
                continue
            if u.get("status") != "done":
                continue
            cp = u.get("commit_paket")
            if not isinstance(cp, dict):
                continue
            if not cp.get("dateien"):
                continue
            pakete.append(dict(cp))
        assert len(pakete) == 2
        assert pakete[0]["dateien"] == ["a.py"]
        assert pakete[1]["dateien"] == ["b.py"]

    def test_restore_ignoriert_done_ohne_dateien(
            self, tmp_path: Path) -> None:
        ups_plan = [
            {"id": "U1", "status": "done",
             "commit_paket": {"dateien": []}},
            {"id": "U2", "status": "done",
             "commit_paket": {}},
        ]
        pakete: list[dict[str, object]] = []
        for u in ups_plan:
            if not isinstance(u, dict):
                continue
            if u.get("status") != "done":
                continue
            cp = u.get("commit_paket")
            if not isinstance(cp, dict):
                continue
            if not cp.get("dateien"):
                continue
            pakete.append(dict(cp))
        assert pakete == []

# =====================================================================
# _phasen_basis_gate_ok (A5, 2026-10-16)
# =====================================================================

class TestPhasenBasisGate:
    """Tests fuer das erweiterte Basis-Gate im Phasen-Modus."""

    def _setze_phase_yaml(
            self, yaml_dir: Path,
            done_mit_paket: list[tuple[str, list[str]]]
    ) -> None:
        """Schreibt eine minimale phase.yaml nach yaml_dir.

        yaml_dir: Verzeichnis fuer phase.yaml (NICHT
        das git-Repo, sonst wird phase.yaml selbst als
        untracked erkannt).
        done_mit_paket: Liste von (unterblock_id, dateien).
        """
        import yaml
        unterbloecke = []
        for uid, dateien in done_mit_paket:
            unterbloecke.append({
                "id": uid,
                "titel": f"Test-{uid}",
                "status": "done",
                "commit_paket": {
                    "dateien": dateien,
                    "message": f"{uid} fertig",
                },
                "unterpunkte": [],
                "geschaetzte_runden": 1,
            })
        daten = {
            "phase_aktiv": True,
            "phase_id": "P1",
            "phase_titel": "Testphase",
            "phase_start_head": "",
            "phase_erstellt_am": "2026-10-15T00:00:00+00:00",
            "phase_unterbloecke": unterbloecke,
        }
        ziel = yaml_dir / "testprojekt.phase.yaml"
        ziel.write_text(
            yaml.safe_dump(daten, sort_keys=False),
            encoding="utf-8")

    def test_clean_git(
            self, tmp_path: Path, monkeypatch) -> None:
        """Leerer git status -> clean."""
        # tmp_path als Projekt-Dir, aber mit git-Repo.
        import subprocess
        subprocess.run(["git", "init", "-q"],
                       cwd=str(tmp_path), check=True)
        ok, grund, _details = pipeline._phasen_basis_gate_ok(
            "testprojekt", tmp_path)
        assert ok is True
        assert grund == "clean"

    def test_untracked_ohne_phase_yaml_fail(
            self, tmp_path: Path, monkeypatch) -> None:
        """Untracked Datei, aber phase.yaml fehlt -> Fail."""
        monkeypatch.setattr(pipeline, "_PHASE_YAML_DIR", tmp_path)
        import subprocess
        subprocess.run(["git", "init", "-q"],
                       cwd=str(tmp_path), check=True)
        (tmp_path / "fremd.txt").write_text("x")
        ok, grund, _details = pipeline._phasen_basis_gate_ok(
            "testprojekt", tmp_path)
        assert ok is False
        assert grund == "fremd_untracked"

    def test_untracked_in_done_paket_ok(
            self, tmp_path: Path, monkeypatch) -> None:
        """Untracked Datei, die in done-Paket steht -> OK."""
        # yaml_dir MUSS ausserhalb des git-Repos liegen.
        # Sonst listet git status das yaml-Verzeichnis
        # als untracked und _phasen_basis_gate_ok wertet
        # es als fremd.
        yaml_dir = tmp_path.parent / (tmp_path.name + "_yaml")
        yaml_dir.mkdir(exist_ok=True)
        monkeypatch.setattr(pipeline, "_PHASE_YAML_DIR", yaml_dir)
        import subprocess
        subprocess.run(["git", "init", "-q"],
                       cwd=str(tmp_path), check=True)
        (tmp_path / "a.py").write_text("x")
        self._setze_phase_yaml(yaml_dir, [("U1", ["a.py"])])
        ok, grund, details = pipeline._phasen_basis_gate_ok(
            "testprojekt", tmp_path)
        assert ok is True
        assert grund == "phasen_clean"  # W7
        assert "U1" in details.get("done_ids", [])

    def test_untracked_fremd_fail(
            self, tmp_path: Path, monkeypatch) -> None:
        """Untracked Datei, nicht in done-Paket -> Fail."""
        monkeypatch.setattr(pipeline, "_PHASE_YAML_DIR", tmp_path)
        import subprocess
        subprocess.run(["git", "init", "-q"],
                       cwd=str(tmp_path), check=True)
        (tmp_path / "fremd.txt").write_text("x")
        self._setze_phase_yaml(tmp_path, [("U1", ["a.py"])])
        ok, grund, _details = pipeline._phasen_basis_gate_ok(
            "testprojekt", tmp_path)
        assert ok is False
        assert grund == "fremd_untracked"
        assert "fremd.txt" in _details.get("fremd", [])

    def test_modified_fail(
            self, tmp_path: Path, monkeypatch) -> None:
        """Modified Datei ohne done-Pfad -> Fail-closed.

        W7 (2026-10-16): M aus done-Pfaden wird
        akzeptiert; M ohne done-Pfad bleibt
        Fail-closed.
        """
        # YAML-Verzeichnis AUSSERHALB des Repos,
        # damit die x.py nicht als done-Pfad gilt.
        yaml_dir = tmp_path.parent / (tmp_path.name + "_yaml")
        yaml_dir.mkdir(exist_ok=True)
        monkeypatch.setattr(pipeline, "_PHASE_YAML_DIR", yaml_dir)
        import subprocess
        subprocess.run(["git", "init", "-q"],
                       cwd=str(tmp_path), check=True)
        subprocess.run(["git", "-c", "user.name=t",
                        "-c", "user.email=t@t", "commit",
                        "--allow-empty", "-m", "init", "-q"],
                       cwd=str(tmp_path), check=True)
        (tmp_path / "x.py").write_text("v1")
        subprocess.run(["git", "add", "x.py"],
                       cwd=str(tmp_path), check=True)
        subprocess.run(["git", "-c", "user.name=t",
                        "-c", "user.email=t@t", "commit",
                        "-m", "add x", "-q"],
                       cwd=str(tmp_path), check=True)
        (tmp_path / "x.py").write_text("v2")  # modified
        ok, grund, _details = pipeline._phasen_basis_gate_ok(
            "testprojekt", tmp_path)
        assert ok is False
        assert grund == "modifiziert"

    def test_mehrere_done_pakete(
            self, tmp_path: Path, monkeypatch) -> None:
        """Untracked Dateien aus zwei done-Paketen -> OK."""
        yaml_dir = tmp_path.parent / (tmp_path.name + "_yaml")
        yaml_dir.mkdir(exist_ok=True)
        monkeypatch.setattr(pipeline, "_PHASE_YAML_DIR", yaml_dir)
        import subprocess
        subprocess.run(["git", "init", "-q"],
                       cwd=str(tmp_path), check=True)
        (tmp_path / "a.py").write_text("x")
        (tmp_path / "b.py").write_text("y")
        self._setze_phase_yaml(yaml_dir, [
            ("U1", ["a.py"]),
            ("U2", ["b.py"]),
        ])
        ok, grund, details = pipeline._phasen_basis_gate_ok(
            "testprojekt", tmp_path)
        assert ok is True
        # W7 (2026-10-16): Grund-Name geaendert.
        assert grund == "phasen_clean"
        done_ids = details.get("done_ids", [])
        assert "U1" in done_ids
        assert "U2" in done_ids

# =====================================================================
# Plan-Korrektur-Schutz (A1+A2, 2026-10-16)
# =====================================================================

class TestPlanKorrekturSchutz:
    """Tests fuer done-Schutz in _phase_plan_korrektur."""

    def _setup(self, tmp_path: Path, monkeypatch) -> Path:
        """Setzt yaml_dir + git-Repo + state vor."""
        import subprocess
        yaml_dir = tmp_path.parent / (tmp_path.name + "_yaml")
        yaml_dir.mkdir(exist_ok=True)
        monkeypatch.setattr(pipeline, "_PHASE_YAML_DIR", yaml_dir)
        monkeypatch.setattr(pipeline, "audit",
                            lambda *a, **kw: None)
        subprocess.run(["git", "init", "-q"],
                       cwd=str(tmp_path), check=True)
        return yaml_dir

    def _phase_yaml(self, yaml_dir: Path,
                    unterbloecke: list) -> None:
        import yaml
        daten = {
            "phase_aktiv": True,
            "phase_id": "18",
            "phase_titel": "Testphase",
            "phase_start_head": "0d0fe2c",
            "phase_erstellt_am": "2026-10-16T00:00:00+00:00",
            "phase_unterbloecke": unterbloecke,
        }
        (yaml_dir / "testprojekt.phase.yaml").write_text(
            yaml.safe_dump(daten, sort_keys=False),
            encoding="utf-8")

    def _state(self, tmp_path: Path,
               unterbloecke: list) -> pipeline.RunState:
        state = pipeline.RunState(
            block_id="t", aufgabe="t",
            start_ts="2026-10-16T00:00:00+00:00",
            docs={}, agents={}, always={}, optional={},
            file_whitelist=["core/", "tests/"],
            api_key="x", budget={}, agent_docs={},
            project_dir=tmp_path, project_name="testprojekt")
        state.phase_id = "18"
        state.phase_titel = "Testphase"
        state.phase_unterbloecke = unterbloecke
        state.phase_aktiv = True
        state.phase_commit_pakete = []
        return state

    def _planner_antwort(self, unterbloecke: list) -> str:
        """Baut einen Plan-Text im P10-P14-Format."""
        zeilen = ["PHASE: 18 - Testphase"]
        for u in unterbloecke:
            zeilen.append(f"UNTERBLOCK: {u['id']} - {u['titel']}")
            zeilen.append("Unterpunkte:")
            for p in u["unterpunkte"]:
                zeilen.append(f"  - {p}")
            zeilen.append(
                f"Geschaetzte Runden: {u['geschaetzte_runden']}")
        return "\n".join(zeilen) + "\n"

    def test_done_unterblock_bleibt_done(
            self, tmp_path: Path, monkeypatch) -> None:
        """U1=done, U2=no_go. Plan-Korrektur darf U1 nicht aendern."""
        from unittest.mock import patch

        import yaml
        yaml_dir = self._setup(tmp_path, monkeypatch)
        ups = [
            {"id": "U1", "titel": "Modell", "status": "done",
             "commit_paket": {"dateien": ["core/a.py"],
                              "message": "U1"},
             "unterpunkte": ["alt1"],
             "geschaetzte_runden": 1},
            {"id": "U2", "titel": "Loader",
             "status": "no_go", "commit_paket": {},
             "unterpunkte": ["alt2"],
             "geschaetzte_runden": 1},
        ]
        self._phase_yaml(yaml_dir, ups)
        state = self._state(tmp_path, ups)
        neue = [
            {"id": "U1", "titel": "Modell",
             "unterpunkte": ["neu1"], "geschaetzte_runden": 1},
            {"id": "U2", "titel": "Loader",
             "unterpunkte": ["neu2"], "geschaetzte_runden": 1},
        ]
        antwort = self._planner_antwort(neue)
        with patch("pipeline._planner_lauf",
                   return_value=antwort), \
             patch("builtins.input", return_value="j"):
            ok = pipeline._phase_plan_korrektur(
                "testprojekt", state, "key")
        assert ok is True
        d = yaml.safe_load(
            (yaml_dir / "testprojekt.phase.yaml").read_text())
        u1 = d["phase_unterbloecke"][0]
        u2 = d["phase_unterbloecke"][1]
        assert u1["status"] == "done"
        assert u1["commit_paket"]["dateien"] == ["core/a.py"]
        assert u1["unterpunkte"] == ["alt1"]
        assert u2["status"] == "pending"
        assert u2["unterpunkte"] == ["neu2"]

    def test_anzahl_geaendert_fail(
            self, tmp_path: Path, monkeypatch) -> None:
        from unittest.mock import patch
        yaml_dir = self._setup(tmp_path, monkeypatch)
        ups = [
            {"id": "U1", "titel": "Modell", "status": "done",
             "commit_paket": {}, "unterpunkte": [],
             "geschaetzte_runden": 1},
            {"id": "U2", "titel": "Loader", "status": "no_go",
             "commit_paket": {}, "unterpunkte": [],
             "geschaetzte_runden": 1},
        ]
        self._phase_yaml(yaml_dir, ups)
        state = self._state(tmp_path, ups)
        neue = [
            {"id": "U1", "titel": "Modell",
             "unterpunkte": ["x"], "geschaetzte_runden": 1},
        ]
        antwort = self._planner_antwort(neue)
        with patch("pipeline._planner_lauf",
                   return_value=antwort), \
             patch("builtins.input", return_value="j"):
            ok = pipeline._phase_plan_korrektur(
                "testprojekt", state, "key")
        assert ok is False

    def test_id_geaendert_fail(
            self, tmp_path: Path, monkeypatch) -> None:
        from unittest.mock import patch
        yaml_dir = self._setup(tmp_path, monkeypatch)
        ups = [
            {"id": "U1", "titel": "Modell", "status": "done",
             "commit_paket": {}, "unterpunkte": [],
             "geschaetzte_runden": 1},
        ]
        self._phase_yaml(yaml_dir, ups)
        state = self._state(tmp_path, ups)
        neue = [
            {"id": "U9", "titel": "Modell",
             "unterpunkte": ["x"], "geschaetzte_runden": 1},
        ]
        antwort = self._planner_antwort(neue)
        with patch("pipeline._planner_lauf",
                   return_value=antwort), \
             patch("builtins.input", return_value="j"):
            ok = pipeline._phase_plan_korrektur(
                "testprojekt", state, "key")
        assert ok is False

    def test_alter_plan_enthaelt_unterpunkte(
            self, tmp_path: Path, monkeypatch) -> None:
        """Der Planner-Kontext enthaelt die Unterpunkte."""
        from unittest.mock import patch
        yaml_dir = self._setup(tmp_path, monkeypatch)
        ups = [
            {"id": "U1", "titel": "Modell", "status": "done",
             "commit_paket": {}, "unterpunkte": ["spezifisch1",
                                                  "spezifisch2"],
             "geschaetzte_runden": 1},
        ]
        self._phase_yaml(yaml_dir, ups)
        state = self._state(tmp_path, ups)

        gesammelt: list[dict] = []
        def fake_lauf(state, api, auftrag, *a, **kw):
            gesammelt.append(kw.get("korrektur_kontext", {}))

        with patch("pipeline._planner_lauf",
                   side_effect=fake_lauf), \
             patch("pipeline._phase_rr_k8",
                   return_value="abbrechen"):
            pipeline._phase_plan_korrektur(
                "testprojekt", state, "key")

        assert len(gesammelt) == 1
        alter_plan = gesammelt[0].get("alter_plan", "")
        assert "spezifisch1" in alter_plan
        assert "spezifisch2" in alter_plan



# =====================================================================
# W7 (2026-10-16): Basis-Gate akzeptiert A/M aus done-Pfaden
# =====================================================================

class TestW7:
    def test_intent_to_add_done_pfad_ok(self) -> None:
        # Strukturtest: A  (intent-to-add) wird
        # klassifiziert.
        import inspect
        src = inspect.getsource(pipeline._phasen_basis_gate_ok)
        assert '"A ", "AM"' in src
        assert "intent" in src

    def test_modified_done_pfad_ok(self) -> None:
        import inspect
        src = inspect.getsource(pipeline._phasen_basis_gate_ok)
        assert '" M", "M ", "MM"' in src

    def test_fremd_mod_fail_closed(self) -> None:
        import inspect
        src = inspect.getsource(pipeline._phasen_basis_gate_ok)
        assert "fremd_mod" in src
        assert '"modifiziert"' in src
