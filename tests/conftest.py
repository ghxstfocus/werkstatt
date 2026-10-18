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

@pytest.fixture(autouse=True)
def _set_dummy_api_key(monkeypatch):
    """P2b-5: run_phase prueft DEEPSEEK_API_KEY (Fail-closed).

    Tests, die run_phase (oder Funktionen, die den Key
    brauchen) aufrufen, sollen nicht an einem fehlenden
    API-Key scheitern. Der Wert wird nicht an die
    DeepSeek-API geschickt, weil alle ask_llm-Aufrufe in
    Tests gemockt sind.
    """
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-dummy-key")



# =====================================================================
# W36-RP-b (2026-10-18): subprocess-Schutz auf gefaehrliche
# Kommandos. Schuetzt alle Tests. Legitime Kommandos
# (git, pytest, ruff, mypy, python, cat) bleiben erlaubt.
# =====================================================================

_GEFAEHRLICHE_KOMMANDOS = {
    "rm", "rmdir", "mv", "dd", "mkfs", "curl", "wget",
    "ssh", "scp", "nc", "ncat", "telnet", "chmod", "chown",
    "sudo", "su", "env", "exec",
    "bash", "sh", "zsh", "dash", "ksh",
    "xargs", "find", "eval",
}


@pytest.fixture(autouse=True)
def _no_gefaehrliche_subprocess(monkeypatch):
    """W36-RP-b: blockiert gefaehrliche subprocess-Aufrufe
    in allen Tests.

    Gefaehrliche Kommandos: rm, curl, wget, dd, mkfs, ssh,
    sudo, env, bash -c, sh -c, xargs, find -exec, etc.
    Legitime Kommandos (git, pytest, ruff, mypy, python,
    cat, ls, echo) bleiben erlaubt.

    Wrapper-Erkennung: sudo/env/xargs/find -exec werden
    rekursiv geprueft (der naechste Nicht-Flag-Token).
    """
    import os as _os
    import subprocess as _sp

    # Originale sichern (nur einmal).
    if not hasattr(_sp, "__orig_run_w36b__"):
        _sp.__orig_run_w36b__ = _sp.run
        _sp.__orig_call_w36b__ = _sp.call
        _sp.__orig_check_call_w36b__ = _sp.check_call
        _sp.__orig_check_output_w36b__ = _sp.check_output
        _sp.__orig_popen_w36b__ = _sp.Popen

    def _argv_teile(argv):
        if isinstance(argv, (list, tuple)):
            return [str(x) for x in argv]
        return str(argv).split()

    def _erstes_kommando(teile):
        """Erstes Nicht-Flag-Token."""
        for tok in teile:
            if tok and not tok.startswith("-"):
                return _os.path.basename(tok)
        return ""

    def _ist_gefaehrlich(teile):
        """Prueft das erste Kommando und Wrapper rekursiv."""
        if not teile:
            return False
        erstes = _erstes_kommando(teile)
        if not erstes:
            return False
        if erstes not in _GEFAEHRLICHE_KOMMANDOS:
            return False
        # Wrapper: rekursiv das naechste Kommando pruefen.
        if erstes in {"sudo", "env", "exec"}:
            # Naegstes Argument nach dem Wrapper.
            for i, tok in enumerate(teile):
                if _os.path.basename(tok) == erstes:
                    if i + 1 < len(teile):
                        return _ist_gefaehrlich(teile[i + 1:])
                    return True
            return True
        if erstes in {"bash", "sh", "zsh", "dash", "ksh"}:
            # bash -c "rm ..." -> naechster Token nach -c.
            # W36-RP-b-4 (2026-10-18): -c-Argument ist
            # ein String, der gesplittet werden muss.
            for i, tok in enumerate(teile):
                if tok == "-c" and i + 1 < len(teile):
                    rest_str = teile[i + 1]
                    if isinstance(rest_str, str):
                        rest = rest_str.split()
                    else:
                        rest = list(rest_str)
                    return _ist_gefaehrlich(rest)
            return True
        if erstes == "xargs":
            for i, tok in enumerate(teile):
                if _os.path.basename(tok) == "xargs":
                    if i + 1 < len(teile):
                        return _ist_gefaehrlich(teile[i + 1:])
                    return True
            return True
        if erstes == "find":
            for i, tok in enumerate(teile):
                if tok == "-exec" and i + 1 < len(teile):
                    return _ist_gefaehrlich(teile[i + 1:])
            return True
        # Direktes gefaehrliches Kommando.
        return True

    def _pruefe(argv, funktion):
        teile = _argv_teile(argv)
        if _ist_gefaehrlich(teile):
            raise AssertionError(
                f"W36-RP-b: {funktion}({argv!r}) ist ein "
                f"gefaehrliches Kommando. Blockiert. "
                f"Gefaehrliche Kommandos: rm, curl, "
                f"wget, dd, mkfs, ssh, sudo, env, "
                f"bash -c, xargs, find -exec, etc.")

    def _run(argv, *args, **kwargs):
        _pruefe(argv, "subprocess.run")
        return _sp.__orig_run_w36b__(argv, *args, **kwargs)

    def _call(argv, *args, **kwargs):
        _pruefe(argv, "subprocess.call")
        return _sp.__orig_call_w36b__(argv, *args, **kwargs)

    def _check_call(argv, *args, **kwargs):
        _pruefe(argv, "subprocess.check_call")
        return _sp.__orig_check_call_w36b__(argv, *args, **kwargs)

    def _check_output(argv, *args, **kwargs):
        _pruefe(argv, "subprocess.check_output")
        return _sp.__orig_check_output_w36b__(argv, *args, **kwargs)

    def _popen(argv, *args, **kwargs):
        _pruefe(argv, "subprocess.Popen")
        return _sp.__orig_popen_w36b__(argv, *args, **kwargs)

    monkeypatch.setattr(_sp, "run", _run)
    monkeypatch.setattr(_sp, "call", _call)
    monkeypatch.setattr(_sp, "check_call", _check_call)
    monkeypatch.setattr(_sp, "check_output", _check_output)
    monkeypatch.setattr(_sp, "Popen", _popen)
