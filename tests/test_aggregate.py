"""Tests fuer werkstatt_aggregate.py (A1 projekt_stand)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, "/opt/werkstatt")

import werkstatt_aggregate as wa


class TestIstWerkstattCommit:
    def test_test_workbench(self) -> None:
        assert wa._ist_werkstatt_commit(
            "test(workbench): notify_ntfy") is True

    def test_fix_workbench(self) -> None:
        assert wa._ist_werkstatt_commit(
            "fix(workbench): whois") is True

    def test_docs_workbench(self) -> None:
        assert wa._ist_werkstatt_commit(
            "docs(workbench): Handoff") is True

    def test_menschlicher_commit(self) -> None:
        assert wa._ist_werkstatt_commit(
            "feat: neues Feature") is False

    def test_workbench_im_body(self) -> None:
        # "workbench" ohne Scope-Klammer: menschlich.
        assert wa._ist_werkstatt_commit(
            "docs: workbench Handbuch") is False


class TestSammleProjektStand:
    def test_pfad_existiert_nicht(self, tmp_path: Path) -> None:
        fehlt = tmp_path / "gibtsnicht"
        stand = wa.sammle_projekt_stand(fehlt)
        assert stand["basis"] == "git-log"
        assert stand["letzte_commits"] == []

    def test_mit_commits(self) -> None:
        stand = wa.sammle_projekt_stand(Path("/opt/security-ai"),
                                        max_commits=3)
        assert stand["basis"] == "git-log"
        assert len(stand["letzte_commits"]) <= 3
        for c in stand["letzte_commits"]:
            assert "hash" in c
            assert "datum" in c
            assert "message" in c
            assert c["quelle"] in ("werkstatt", "mensch")
            assert isinstance(c["dateien"], list)

    def test_quelle_werkstatt(self) -> None:
        stand = wa.sammle_projekt_stand(Path("/opt/security-ai"),
                                        max_commits=5)
        # Mindestens die letzten 5 sind Werkstatt-Commits.
        quellen = [c["quelle"] for c in stand["letzte_commits"]]
        assert "werkstatt" in quellen


class TestYamlQuote:
    def test_einfacher_string(self) -> None:
        assert wa._yaml_quote("hello") == "hello"

    def test_mit_doppelpunkt(self) -> None:
        assert wa._yaml_quote("test(workbench): x") == \
            '"test(workbench): x"'

    def test_mit_newline(self) -> None:
        ergebnis = wa._yaml_quote("a\nb")
        assert ergebnis.startswith('"')
        assert ergebnis.endswith('"')
        assert "\n" in ergebnis
