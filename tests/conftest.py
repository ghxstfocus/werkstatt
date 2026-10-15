"""Globale pytest-Fixtures fuer /opt/werkstatt/tests/.

Audit-Isolierung: kein Test schreibt ins echte
/opt/werkstatt/audit-logs/. Ursache 2026-10-15 (siehe Handoff).
"""
from __future__ import annotations

import sys

import pytest

sys.path.insert(0, "/opt/werkstatt")


@pytest.fixture(autouse=True)
def _isolate_audit(tmp_path, monkeypatch):
    """Audit-Isolierung: kein Test schreibt ins echte Log.

    Ursache 2026-10-15: TestApplyCodePatches hat mehrere Tests,
    die apply_code_patches aufrufen, ohne audit zu mocken.
    Als root ausgefuehrt, entstand /opt/werkstatt/audit-logs/
    agent-pipeline-<tag>.jsonl als root:root, und der naechste
    builder-Lauf konnte nicht schreiben.

    Diese Fixture lenkt _werkstatt_home auf tmp_path um.
    """
    import pipeline
    monkeypatch.setattr(pipeline, "_werkstatt_home",
                        lambda: tmp_path)
