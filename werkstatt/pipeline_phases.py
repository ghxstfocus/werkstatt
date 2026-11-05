"""Deprecation-Proxy — siehe werkstatt/phases/ (OP-139 Phase 1).

werkstatt.pipeline_phases und werkstatt.phases sind ab hier DASSELBE
Modul-Objekt (via sys.modules-Alias). Grund:

- Tests patchen private Attribute (monkeypatch.setattr(
  pipeline_phases, "_validate_contract_safe", ...), patch.object(
  pp, "_with_spinner", ...)). Mit 'from werkstatt.phases import *'
  wirken solche Patches nur auf dem Proxy, nicht im echten Modul.

- Tests rufen 'pp._validate_contract_safe(...)' direkt auf und
  erwarten, dass Modul-Globals (audit, _with_spinner) mitgepatcht
  werden. Beide muessen dasselbe Objekt sein.

Nach OP-143 wird dieser Alias entfernt und Aufrufer importieren
direkt aus werkstatt.phases.*.
"""
import sys as _sys

import werkstatt.phases as _phases_mod

_sys.modules[__name__] = _phases_mod
