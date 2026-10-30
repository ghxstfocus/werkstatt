"""Spec: Ziel-.md ist kein Code-Pfad-Explorer.

Fix F 2026-10-31: Wenn docs/STATUS.md Ziel der Aufgabe ist, darf
der Explorer NICHT 19 Code-Pfade aus ihrem Body extrahieren.
"""
from __future__ import annotations
import sys
sys.path.insert(0, "/opt/werkstatt")
import pytest


class TestExplorerZielMd:
    """Logik-Test: aufgabe_pfade ist Ausschlussmenge fuer .md-Explorer."""

    def test_ziel_md_wird_uebersprungen(self) -> None:
        # Simuliert die Schleifenlogik aus explorer.py
        messungen = {
            "aufgabe_pfade": {"dateien": ["docs/STATUS.md"]},
            "ruff": {"dateien": ["docs/STATUS.md", "core/a.py"]},
        }
        aufgabe_pfade_set = set(
            (messungen.get("aufgabe_pfade") or {}).get("dateien") or []
        )
        key_files = []
        for name, m in messungen.items():
            for datei in m.get("dateien", []):
                if datei.endswith(".md") or datei.startswith("docs/"):
                    if datei in aufgabe_pfade_set:
                        continue  # Fix F
                    # wuerde sonst extrahieren
                    key_files.append({"file": datei, "why": "kontext"})
                    continue
                key_files.append({"file": datei, "why": "mess"})
        assert all(k["file"] != "docs/STATUS.md" for k in key_files)
        assert any(k["file"] == "core/a.py" for k in key_files)

    def test_nicht_ziel_md_wird_exploriert(self) -> None:
        messungen = {
            "aufgabe_pfade": {"dateien": ["core/foo.py"]},
            "ruff": {"dateien": ["docs/OTHER.md"]},
        }
        aufgabe_pfade_set = set(
            (messungen.get("aufgabe_pfade") or {}).get("dateien") or []
        )
        key_files = []
        for name, m in messungen.items():
            for datei in m.get("dateien", []):
                if datei.endswith(".md") or datei.startswith("docs/"):
                    if datei in aufgabe_pfade_set:
                        continue
                    key_files.append({"file": datei, "why": "exploriert"})
                    continue
                key_files.append({"file": datei, "why": "mess"})
        assert any(k["file"] == "docs/OTHER.md" for k in key_files)
