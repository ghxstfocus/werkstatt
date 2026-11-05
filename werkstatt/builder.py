"""Deprecation-Proxy — siehe werkstatt/roles/builder/ (OP-140 Phase 1).

werkstatt.builder und werkstatt.roles.builder sind ab hier
DASSELBE Modul-Objekt (via sys.modules-Alias). Grund:

- 26 Files importieren 'from werkstatt.builder import X'.
- Tests patchen Modul-Attribute (patch.object(builder, "...")).

Mit 'from werkstatt.roles.builder import *' waeren Patches auf
werkstatt.builder stumm tot. Der Alias macht beide Namen zum
selben Objekt.

Nach OP-143 wird dieser Alias entfernt und Aufrufer importieren
direkt aus werkstatt.roles.builder.*.
"""
import sys as _sys

import werkstatt.roles.builder as _new_mod

_sys.modules[__name__] = _new_mod
