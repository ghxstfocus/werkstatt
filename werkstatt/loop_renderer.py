"""Deprecation-Proxy — siehe werkstatt/render/ (OP-138).

werkstatt.loop_renderer und werkstatt.render sind ab hier DASSELBE
Modul-Objekt (via sys.modules-Alias). Grund:

- Tests patchen private Attribute (monkeypatch.setattr(
  loop_renderer, "_publish", ...)). Mit 'from werkstatt.render
  import *' wirken solche Patches nur auf dem Proxy, nicht im
  echten Modul — Tests wuerden gruen laufen, aber tote Mocks
  einbauen.

- conftest.py rebindet Modul-Globals (_PROGRESS_OPEN = False,
  _TEE_STREAM = None). Rebind auf Proxy wuerde das echte Modul
  nicht zuruecksetzen.

Beide Probleme verschwinden, wenn beide Namen auf dasselbe
Modul-Objekt zeigen. Neue Aufrufer sollten trotzdem direkt aus
werkstatt.render.* importieren.
"""
import sys as _sys

import werkstatt.render as _render_mod

_sys.modules[__name__] = _render_mod
