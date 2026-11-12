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

def test_gleiche_ereignisse_bleiben_pro_run_idempotent(tmp_path):
    assert progress.append(
        tmp_path, name="Phase abgeschlossen", status="phase_ende",
        info="rc=0 tasks_ok=1/1", run_id="run-a",
    ) is True
    assert progress.append(
        tmp_path, name="Phase abgeschlossen", status="phase_ende",
        info="rc=0 tasks_ok=1/1", run_id="run-a",
    ) is False
    assert progress.append(
        tmp_path, name="Phase abgeschlossen", status="phase_ende",
        info="rc=0 tasks_ok=1/1", run_id="run-b",
    ) is True

    content = (tmp_path / "PROGRESS.md").read_text(encoding="utf-8")
    assert content.count("-- Phase abgeschlossen") == 2
    assert content.count("- **Run-ID:** run-a") == 1
    assert content.count("- **Run-ID:** run-b") == 1


def test_eintrag_endet_ohne_leerzeile_am_dateiende(tmp_path):
    assert progress.append(tmp_path, name="x", status="done") is True
    content = (tmp_path / "PROGRESS.md").read_text(encoding="utf-8")
    assert content.endswith("\n")
    assert not content.endswith("\n\n")
