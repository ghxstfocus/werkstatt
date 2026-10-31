"""Spec: Fix AX — deterministischer Reviewer-Bug-Verifier.

Deckt die 3 Halluzinationen aus RERUN 3 (2026-10-31) gegen die echten
Bug-Beschreibungen des LLM-Reviewers ab. Konservativ: nur widerlegen,
was der Code zweifelsfrei widerlegt. Unpruefbares bleibt unangetastet.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, "/opt/werkstatt")

from werkstatt.reviewer import _verifiziere_reviewer_bugs


def _fake_file(tmp_path: Path, name: str, content: str) -> Path:
    f = tmp_path / name
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(content, encoding="utf-8")
    return f


class TestVerifierWiderlegt:
    def test_generate_text_fehlt_wird_widerlegt(self, tmp_path: Path) -> None:
        """Original-Beschreibung aus RERUN 3 gegen den echten
        deepseek_client.py-Inhalt (mit def generate_text)."""
        _fake_file(tmp_path, "ds.py", (
            "class DeepSeekClient:\n"
            "    def generate(self, request):\n"
            "        return None\n"
            "    def generate_text(self, prompt):\n"
            "        return ''\n"
        ))
        bugs = [{
            "severity": "high",
            "file": "ds.py",
            "description": "generate_text() fehlt im neuen DeepSeekClient. "
                           "Der alte OllamaClient hatte generate_text(...)",
        }]
        out = _verifiziere_reviewer_bugs(bugs, tmp_path, "test")
        assert out == []

    def test_is_available_fehlt_wird_widerlegt(self, tmp_path: Path) -> None:
        _fake_file(tmp_path, "ds.py", (
            "class DeepSeekClient:\n"
            "    def is_available(self, timeout=None):\n"
            "        return True\n"
        ))
        bugs = [{
            "severity": "high",
            "file": "ds.py",
            "description": "is_available(timeout) Health-Check fehlt im "
                           "DeepSeekClient. Der alte Client hatte is_available()",
        }]
        out = _verifiziere_reviewer_bugs(bugs, tmp_path, "test")
        assert out == []

    def test_datei_fehlt_wird_widerlegt(self, tmp_path: Path) -> None:
        _fake_file(tmp_path, "vorhanden.py", "# da\n")
        bugs = [{
            "severity": "high",
            "file": "vorhanden.py",
            "description": "Datei vorhanden.py existiert nicht.",
        }]
        out = _verifiziere_reviewer_bugs(bugs, tmp_path, "test")
        assert out == []


class TestVerifierLaesstDurch:
    def test_symbol_fehlt_wirklich_bleibt(self, tmp_path: Path) -> None:
        """Wenn das Symbol nicht existiert, muss der Bug bleiben."""
        _fake_file(tmp_path, "ds.py", (
            "class DeepSeekClient:\n"
            "    def generate(self, request):\n"
            "        return None\n"
        ))
        bugs = [{
            "severity": "high",
            "file": "ds.py",
            "description": "generate_text() fehlt im neuen DeepSeekClient.",
        }]
        out = _verifiziere_reviewer_bugs(bugs, tmp_path, "test")
        assert len(out) == 1

    def test_semantischer_bug_bleibt(self, tmp_path: Path) -> None:
        """Semantische Aussagen (kein X() fehlt) werden nicht widerlegt."""
        _fake_file(tmp_path, "ds.py", "class DeepSeekClient: pass\n")
        bugs = [{
            "severity": "medium",
            "file": "ds.py",
            "description": "HTTPError wird als LLMUnavailable gemappt; "
                           "der alte Client mappte HTTP != 2xx auf LLMError.",
        }]
        out = _verifiziere_reviewer_bugs(bugs, tmp_path, "test")
        assert len(out) == 1

    def test_bug_ohne_file_bleibt(self) -> None:
        bugs = [{"severity": "high", "description": "irgendwas kaputt"}]
        out = _verifiziere_reviewer_bugs(bugs, Path("/tmp"), "test")
        assert len(out) == 1

    def test_leere_liste(self, tmp_path: Path) -> None:
        assert _verifiziere_reviewer_bugs([], tmp_path, "test") == []


class TestVerifierAudit:
    def test_widerlegter_bug_wird_auditiert(self, tmp_path: Path) -> None:
        _fake_file(tmp_path, "ds.py", "def generate_text():\n    pass\n")
        bugs = [{
            "severity": "high",
            "file": "ds.py",
            "description": "generate_text() fehlt im DeepSeekClient.",
        }]
        with patch("werkstatt.reviewer.audit") as _aud:
            _verifiziere_reviewer_bugs(bugs, tmp_path, "test")
        kinds = [c.args[0] for c in _aud.call_args_list]
        assert "reviewer_bug_widerlegt" in kinds
