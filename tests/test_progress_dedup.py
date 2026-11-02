"""OP-036: progress.append unterdrueckt Duplikate."""
from __future__ import annotations

import sys

sys.path.insert(0, "/opt/werkstatt")

from werkstatt import progress


def test_erst_eintrag_angelegt(tmp_path):
    ok = progress.append(tmp_path, name="x", status="done")
    assert ok is True
    text = (tmp_path / "PROGRESS.md").read_text(encoding="utf-8")
    assert text.count("-- x") == 1


def test_duplikat_wird_uebersprungen(tmp_path):
    progress.append(tmp_path, name="x", status="failed", info="patch_write_failed")
    ok = progress.append(tmp_path, name="x", status="failed", info="patch_write_failed")
    assert ok is False
    text = (tmp_path / "PROGRESS.md").read_text(encoding="utf-8")
    assert text.count("-- x") == 1
    assert text.count("patch_write_failed") == 1


def test_unterschiedliche_info_zaehlt_als_neu(tmp_path):
    progress.append(tmp_path, name="x", status="failed", info="patch_write_failed")
    ok = progress.append(tmp_path, name="x", status="failed", info="reviewer_rejected_no_patch")
    assert ok is True
    text = (tmp_path / "PROGRESS.md").read_text(encoding="utf-8")
    assert text.count("-- x") == 2
    assert "patch_write_failed" in text
    assert "reviewer_rejected_no_patch" in text


def test_unterschiedlicher_name_zaehlt_als_neu(tmp_path):
    progress.append(tmp_path, name="t1", status="done")
    ok = progress.append(tmp_path, name="t2", status="done")
    assert ok is True
    text = (tmp_path / "PROGRESS.md").read_text(encoding="utf-8")
    assert text.count("-- t1") == 1
    assert text.count("-- t2") == 1


def test_unterschiedlicher_status_zaehlt_als_neu(tmp_path):
    progress.append(tmp_path, name="x", status="failed", info="i")
    ok = progress.append(tmp_path, name="x", status="done", info="i")
    assert ok is True
    text = (tmp_path / "PROGRESS.md").read_text(encoding="utf-8")
    assert text.count("-- x") == 2
