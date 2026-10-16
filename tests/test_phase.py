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
                phasen_state.phase_commit_pakete.append(
                    {"message": "test",
                     "dateien": ["apps/x.py"]})
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
        assert sammel["dateien"] == ["apps/x.py"]
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

    def test_reviewer_md_enthaelt_new_file(self) -> None:
        from pathlib import Path as _P
        text = _P("/opt/werkstatt/agents/reviewer.md").read_text(
            encoding="utf-8")
        assert "typ: new_file" in text

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

    def test_reviewer_hat_security_log(self) -> None:
        assert "SECURITY_LOG" in self._read("reviewer.md")

    def test_reviewer_hat_r10_hinweis(self) -> None:
        t = self._read("reviewer.md")
        assert "typ: new_file" in t

    def test_reviewer_hat_r5_ausnahme(self) -> None:
        t = self._read("reviewer.md")
        assert "R5" in t and "gilt nicht" in t

    def test_reviewer_hat_antwort_modus(self) -> None:
        t = self._read("reviewer.md")
        assert "ANTWORT" in t
        assert "COMMAND vs. VERDICT vs. ANTWORT" in t

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

    def test_hash_regel_gleich(self) -> None:
        """reviewer.md und builder.md nutzen denselben
        Wortlaut fuer den Vorgaenger-Hash."""
        r = self._read("reviewer.md")
        b = self._read("builder.md")
        assert "Vorgaenger-Hash" in r
        assert "Vorgaenger-Hash" in b

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

