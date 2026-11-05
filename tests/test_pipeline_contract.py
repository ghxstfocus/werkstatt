"""OP-136a: Contract-Validierung in der Pipeline (fail-loud)."""
from __future__ import annotations

import sys

sys.path.insert(0, "/opt/werkstatt")

from werkstatt.state import RunState


def _state(project_dir, **kw):
    defaults = {
        "block_id": "t", "aufgabe": "t", "start_ts": "t",
        "docs": {}, "agents": {}, "always": {}, "optional": {},
        "file_whitelist": [], "api_key": "x", "budget": {},
        "agent_docs": {}, "project_dir": project_dir,
        "project_name": "t",
    }
    defaults.update(kw)
    return RunState(**defaults)


def test_validate_contract_safe_ok(tmp_path):
    """Gefuellter explorer_context -> True, kein Audit."""
    from unittest.mock import patch

    from werkstatt import pipeline_phases as pp
    st = _state(tmp_path)
    st.explorer_context = {
        "findings": "x",
        "key_files": [{"file": "a.py", "why": "y", "confidence": "high"}],
        "next_reads": ["a.py"],
    }
    audited = []
    with patch("werkstatt.phases._common.audit",
                      side_effect=lambda k, p, pd, pn: audited.append(k)):
        ok = pp._validate_contract_safe("explorer", "scout", st, tmp_path, "t")
    assert ok is True
    assert "state_contract_violation" not in audited


def test_validate_contract_safe_leer(tmp_path):
    """Leerer explorer_context -> False + Audit-Event."""
    from unittest.mock import patch

    from werkstatt import pipeline_phases as pp
    st = _state(tmp_path)
    audited = []
    with patch("werkstatt.phases._common.audit",
                      side_effect=lambda k, p, pd, pn: audited.append((k, p))):
        ok = pp._validate_contract_safe("explorer", "scout", st, tmp_path, "t")
    assert ok is False
    assert any(k == "state_contract_violation" for k, _ in audited)
    payload = next(p for k, p in audited if k == "state_contract_violation")
    assert "explorer" in payload.get("transition", "")
    assert payload.get("felder")


def test_validate_contract_safe_unbekannter_uebergang(tmp_path):
    """Unbekannter Uebergang -> Noop -> True."""
    from unittest.mock import patch

    from werkstatt import pipeline_phases as pp
    st = _state(tmp_path)
    audited = []
    with patch("werkstatt.phases._common.audit",
                      side_effect=lambda k, p, pd, pn: audited.append(k)):
        ok = pp._validate_contract_safe("foo", "bar", st, tmp_path, "t")
    assert ok is True
    assert not audited
