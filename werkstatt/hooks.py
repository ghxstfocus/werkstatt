"""Hook-Aufrufer (Fix AZ Stufe 2, 2026-10-31).

Extrahiert aus loop.py. Re-Export in loop.py erhaelt
Test-Patches auf werkstatt.loop._call_hook.
"""
from __future__ import annotations

import subprocess
from pathlib import Path


def _call_hook(hook_name: str, payload: dict) -> dict:
    """Ruft einen Hook auf und gibt das JSON-Ergebnis zurueck."""
    import json as _json
    from werkstatt.paths import werkstatt_home as _wh
    hook_path = _wh() / "hooks" / hook_name
    if not hook_path.exists():
        return {"allow": True, "reason": "Hook nicht gefunden (fail-open)"}
    try:
        res = subprocess.run(
            ["python3", str(hook_path)],
            input=_json.dumps(payload),
            cwd=str(__import__("werkstatt.paths", fromlist=["werkstatt_home"]).werkstatt_home()),
            capture_output=True, text=True, timeout=30, check=False,
        )
        if res.returncode != 0:
            return {"allow": False, "reason": f"Hook rc={res.returncode}"}
        return _json.loads(res.stdout)
    except Exception as exc:  # noqa: BLE001
        return {"allow": False, "reason": f"Hook-Fehler: {exc}"}





__all__ = ['_call_hook']
