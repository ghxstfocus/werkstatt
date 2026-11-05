"""Smoke-Tests fuer tools/state_flow.py."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.state_flow import (
    _aggregat,
    _read_baseline,
    baue_flow_index,
)


def test_index_enthaelt_alle_deklarierten_felder():
    from tools.state_inventory import deklarierte_felder
    index = baue_flow_index()
    deklariert = set(deklarierte_felder().keys())
    assert deklariert <= set(index.keys())


def test_ghost_felder_im_index():
    index = baue_flow_index()
    ghosts = [n for n, i in index.items() if i["kategorie"] == "ghost"]
    assert len(ghosts) > 0
    assert "auftrag_bereits_erfuellt" in ghosts


def test_contract_bezug_fuer_tasks():
    index = baue_flow_index()
    assert "tasks" in index
    assert "planner_output" in index["tasks"]["contracts"]
    assert "planner->builder" in index["tasks"]["transitions"]


def test_risiko_hoch_fuer_multi_writer_ohne_contract():
    index = baue_flow_index()
    assert "last_verify_errors" in index
    info = index["last_verify_errors"]
    assert info["risiko"] == "HOCH"
    assert any("ohne Contract" in g for g in info["gruende"])


def test_baseline_deckt_aktuelle_multi_writer():
    index = baue_flow_index()
    baseline = _read_baseline()
    aktuell = set(_aggregat(index)["multi_writer"])
    assert aktuell <= baseline["multi_writer"]


def test_check_baseline_ist_aktuell():
    index = baue_flow_index()
    agg = _aggregat(index)
    baseline = _read_baseline()
    assert set(agg["ghost_active"]) <= baseline["ghost_active"]
    assert set(agg["tote"]) <= baseline["tote"]
