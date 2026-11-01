"""OP-058: ADR-Mini-Phase."""
from __future__ import annotations
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, "/opt/werkstatt")

from werkstatt.gates import (
    _adr_mini_aktiv,
    _naechste_adr_nummer,
    _adr_template,
    _adr_index_append,
)


def test_adr_aktiv_aus(monkeypatch):
    monkeypatch.delenv("WERKSTATT_ADR_MINI", raising=False)
    assert _adr_mini_aktiv() is False


def test_adr_aktiv_an(monkeypatch):
    monkeypatch.setenv("WERKSTATT_ADR_MINI", "1")
    assert _adr_mini_aktiv() is True


def test_naechste_adr_nummer_leer(tmp_path):
    assert _naechste_adr_nummer(tmp_path) == 1


def test_naechste_adr_nummer_hoechste(tmp_path):
    (tmp_path / "ADR-0001-a.md").write_text("x", encoding="utf-8")
    (tmp_path / "ADR-0005-b.md").write_text("x", encoding="utf-8")
    (tmp_path / "README.md").write_text("x", encoding="utf-8")
    assert _naechste_adr_nummer(tmp_path) == 6


def test_adr_template_hat_marker(tmp_path):
    t = _adr_template(7, "mein-slug", "Aufgabe OP-999 X", tmp_path)
    assert "ADR-0007" in t
    assert "mein-slug" in t
    assert "<!-- Vom Menschen zu fuellen" in t


def test_adr_index_append_erfolg(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text(
        "# Index\n\n| Nr | Titel | Datei |\n|---|---|---|\n"
        "| 0001 | Alt | [ADR-0001-a.md](ADR-0001-a.md) |\n",
        encoding="utf-8",
    )
    ok = _adr_index_append(tmp_path, 2, "neu", "ADR-0002-neu.md")
    assert ok
    txt = readme.read_text(encoding="utf-8")
    assert "ADR-0002-neu.md" in txt


def test_adr_index_append_kein_readme(tmp_path):
    assert _adr_index_append(tmp_path, 1, "x", "ADR-0001-x.md") is False
