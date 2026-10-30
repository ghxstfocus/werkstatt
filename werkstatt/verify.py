"""Grounding/Verify (Phase 2 / Gate 18, 2026-10-19).

Aus pipeline.py extrahiert (Reviewer-Gate 18,
verify.py letztes Phase-2-Modul). Enthaelt:
- verify_code (92 Z.) — AST-Grounding.
- verify_code_kwargs (49 Z.) — inspect.signature.
- verify_values (109 Z.) — Enum-Werte.
- _api_signaturen (34 Z.).
- _projekt_symbol_index (27 Z.).

Modul: ~311 Z. (Ausnahme von der 200er-Grenze
aus Gate 4-neu C, wie apply.py). Zerlegung
gehoert in Phase 3.

Gate 4-neu C: verify_code + verify_code_kwargs +
verify_values bleiben funktional bis Phase 3
(nicht geloescht, nur verschoben).

Konsumenten:
- pipeline.py: verify_code (Z. 6614).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from werkstatt.state import RunState


def _projekt_symbol_index(project_dir: Path) -> dict[str, set[str]]:
    """W61-Pro: Baut einen Symbol-Index ueber das ganze Projekt.

    Sammelt alle definierten Funktions-, Klassen- und Methoden-
    Namen aus .py-Dateien. Wird von verify_code genutzt, um
    erfundene APIs zu erkennen.
    """
    import ast as _ast
    index: dict[str, set[str]] = {}
    for py in project_dir.rglob("*.py"):
        # Ignoriere .venv, __pycache__, .git.
        if any(t in py.parts for t in (".venv", "__pycache__",
                                       ".git", "node_modules")):
            continue
        try:
            tree = _ast.parse(py.read_text(encoding="utf-8",
                                          errors="replace"))
        except (SyntaxError, OSError):
            continue
        for node in _ast.walk(tree):
            if isinstance(node, (_ast.FunctionDef,
                                  _ast.AsyncFunctionDef,
                                  _ast.ClassDef)):
                index.setdefault(node.name, set()).add(str(py))
    return index


def verify_code(patches: list[dict[str, str]],
                project_dir: Path,
                state: RunState | None = None) -> list[str]:
    """W61-Pro: Prueft Patch-Anker/Ersatz auf erfundene APIs.

    AgentSeed-Ansatz: AST-Walk ueber den Ersatz-Code. Jeder
    Funktionsaufruf `foo(...)` oder `obj.meth(...)` wird
    gegen den Projekt-Symbol-Index geprueft. Wenn `foo`
    nirgends definiert ist -> Halluzination (suspect).

    Rueckgabe: Liste von Befunden (leer = ok).
    """
    import ast as _ast
    index = _projekt_symbol_index(project_dir)
    befunde: list[str] = []
    # W61-Pro: Kwarg-Check gegen echte Signaturen.
    befunde.extend(verify_code_kwargs(patches, project_dir))
    # W61-Pro: Enum-Werte in Assertions pruefen.
    befunde.extend(verify_values(patches, project_dir))
    # W61-Pro: Test-Bezug pruefen. Wenn letzter_test_fehler
    # failed_test_ids nennt, muss der Patch-Anker zu einem
    # davon passen.
    _ltf = getattr(state, "letzter_test_fehler", "") if state else ""
    if _ltf and "failed_test_ids:" in _ltf:
        import re as _re
        # W61-Pro: Nur echte Test-IDs aus failed_test_ids.
        # Format: tests/...::Klasse::test_name.
        _ids = _re.findall(
            r"::(test_[a-zA-Z_0-9]+)", _ltf)
        if not _ids:
            _ids = _re.findall(
                r"\b(test_[a-zA-Z_0-9]{4,})\b", _ltf)
        for p in patches:
            # GOLD 2026-10-30: akzeptiere beide Patch-Formate.
            anker = p.get("old_string") or p.get("anker", "")
            ersatz = p.get("new_string") or p.get("ersatz", "")
            if "def test_" in anker or "def test_" in ersatz:
                _im_patch = _re.findall(
                    r"def (test_[a-z_0-9]+)", anker + p.get("ersatz", ""))
                if _ids and _im_patch:
                    if not any(t in _ids for t in _im_patch):
                        befunde.append(
                            f"Patch am falschen Test: {_im_patch}, "
                            f"rot ist: {_ids[:3]}")
    for p in patches:
        if p.get("typ") == "new_file":
            continue
        ersatz = p.get("ersatz", "")
        if not ersatz.strip():
            continue
        # Ersatz ist Code-Fragment, kein vollstaendiges Modul.
        # Wir parsen ihn als Modul (Einrueckung normalisieren).
        try:
            tree = _ast.parse(ersatz)
        except SyntaxError:
            # Fragment (z.B. nur ein Block). Kein AST-Check.
            continue
        for node in _ast.walk(tree):
            if not isinstance(node, _ast.Call):
                continue
            # Funktionsname extrahieren.
            fname = None
            if isinstance(node.func, _ast.Name):
                fname = node.func.id
            elif isinstance(node.func, _ast.Attribute):
                fname = node.func.attr
            if not fname:
                continue
            # Eingebaute und bekannte Namen ignorieren.
            if fname in dir(__builtins__):
                continue
            if fname in index:
                continue
            # W61-Pro: unittest/mock-Methoden ignorieren.
            if fname in ("assertEqual", "assertFalse",
                          "assertTrue", "assertIn", "assertIs",
                          "assertIsNone", "assertIsNotNone",
                          "assert_called_once", "assert_called",
                          "assert_called_with", "assert_not_called",
                          "exists", "Mock", "MockWriter",
                          "TemporaryDirectory", "cleanup",
                          "mkdir", "write_text", "read_text",
                          "call_args", "called"):
                continue
            # Modul-Attribut (obj.meth): nur meth pruefen.
            # Wenn meth nirgends im Projekt definiert ist,
            # koennte es eine externe API sein. Wir warnen
            # nur, blocken nicht.
            befunde.append(
                f"unbekanntes Symbol: {fname}() "
                f"(nicht im Projekt definiert)")
    return befunde


def _api_signaturen(project_dir: Path) -> dict[str, str]:
    """W61-Pro: Liest echte API-Signaturen aus dem Projekt.

    Fuer die wichtigsten Klassen (AuditWriter, Change,
    ChangeApplier). Wird von verify_code fuer den
    Kwarg-Check genutzt.
    """
    import inspect as _insp
    import sys as _sys
    sigs: dict[str, str] = {}
    # Projekt in den Pfad.
    if str(project_dir) not in _sys.path:
        _sys.path.insert(0, str(project_dir))
    try:
        from harness.audit.writer import AuditWriter
        sigs["AuditWriter.log"] = str(
            _insp.signature(AuditWriter.log))
    except (ImportError, ValueError):
        pass
    try:
        from core.changeapplier.models import Change
        sigs["Change.__init__"] = str(
            _insp.signature(Change))
    except (ImportError, ValueError):
        pass
    try:
        from core.changeapplier.applier import ChangeApplier
        sigs["ChangeApplier.__init__"] = str(
            _insp.signature(ChangeApplier.__init__))
    except (ImportError, ValueError):
        pass
    return sigs


def verify_code_kwargs(patches: list[dict[str, str]],
                       project_dir: Path) -> list[str]:
    """W61-Pro: Prueft Kwargs in Patches gegen echte Signaturen.

    Findet z.B. log(status=...) wenn AuditWriter.log kein
    status-Kwarg hat.
    """
    import ast as _ast
    sigs = _api_signaturen(project_dir)
    if not sigs:
        return []
    # Mapping: Methodenname -> (klasse, signatur).
    methode_zu_sig: dict[str, str] = {}
    for key, sig in sigs.items():
        name = key.split(".")[-1]
        methode_zu_sig[name] = sig
    befunde: list[str] = []
    for p in patches:
        if p.get("typ") == "new_file":
            continue
        ersatz = p.get("ersatz", "")
        if not ersatz.strip():
            continue
        try:
            tree = _ast.parse(ersatz)
        except SyntaxError:
            continue
        for node in _ast.walk(tree):
            if not isinstance(node, _ast.Call):
                continue
            fname = None
            if isinstance(node.func, _ast.Attribute):
                fname = node.func.attr
            elif isinstance(node.func, _ast.Name):
                fname = node.func.id
            if not fname or fname not in methode_zu_sig:
                continue
            sig_text = methode_zu_sig[fname]
            # Kwargs des Calls.
            for kw in node.keywords:
                if kw.arg is None:
                    continue
                if kw.arg not in sig_text:
                    befunde.append(
                        f"{fname}() kennt kein Kwarg "
                        f"{kw.arg!r} (Signatur: {sig_text[:100]})")
    return befunde


def verify_values(patches: list[dict[str, str]],
                   project_dir: Path) -> list[str]:
    """W61-Pro: Prueft Assertion-Werte gegen echte Enums.

    Findet z.B. assertEqual(..., "applied") wenn der
    echte Enum-Wert "APPLIED" (name) oder "applied"
    (value) ist. Der Builder muss wissen, ob name oder
    value verglichen wird.
    """
    import ast as _ast
    import sys as _sys
    if str(project_dir) not in _sys.path:
        _sys.path.insert(0, str(project_dir))
    try:
        from core.changeapplier.models import ChangeState
    except ImportError:
        return []
    # Erlaubte Werte: name (APPLIED) und value (applied).
    erlaubt = set()
    for cs in ChangeState:
        erlaubt.add(cs.name)
        erlaubt.add(str(cs.value))
    # W61-Pro: execution_status-Werte aus dem Applier-Code
    # lesen. Der Applier schreibt "OK"/"FAILED", nicht Enum.
    _exec_status_werte = set()
    try:
        _applier_src = (project_dir / "core/changeapplier/applier.py"
                        ).read_text(encoding="utf-8")
        import re as _re2
        for m in _re2.finditer(
                r"execution_status=[\"']([^\"']+)[\"']",
                _applier_src):
            _exec_status_werte.add(m.group(1))
    except OSError:
        pass
    befunde: list[str] = []
    for p in patches:
        ersatz = p.get("ersatz", "")
        if not ersatz.strip():
            continue
        # execution_status-Assertion pruefen.
        if _exec_status_werte:
            import re as _re3
            # W61-Pro: Regex praezise. Nur String-Literale,
            # die direkt nach dem execution_status-Zugriff
            # stehen (z.B. assertEqual(..., "OK")).
            for m in _re3.finditer(
                    r"assertEqual\([^,]*execution_status[^,]*,\s*"
                    r"[\"']([^\"']+)[\"']",
                    ersatz):
                val = m.group(1)
                if val not in _exec_status_werte:
                    befunde.append(
                        f"execution_status {val!r}: Applier "
                        f"schreibt {sorted(_exec_status_werte)}")
        # W61-Pro: Fragment-Handling. Ersatz ist oft
        # eingerueckter Code, kein vollstaendiges Modul.
        tree = None
        for _variant in (ersatz,
                         "if True:\n" + "\n".join(
                             "    " + z for z in ersatz.splitlines())):
            try:
                tree = _ast.parse(_variant)
                break
            except SyntaxError:
                continue
        if tree is None:
            # Letzter Versuch: Zeilenweise nach
            # assertEqual(..., "wert") suchen.
            import re as _re
            for m in _re.finditer(
                    r"assert(?:Equal|In)\([^,]+,\s*[\"']([^\"']+)[\"']",
                    ersatz):
                val = m.group(1)
                if val not in erlaubt and val.upper() in {
                        e.upper() for e in erlaubt}:
                    befunde.append(
                        f"assertEqual(..., {val!r}): erlaubt "
                        f"sind {sorted(erlaubt)[:5]}")
            continue
        for node in _ast.walk(tree):
            if not isinstance(node, _ast.Call):
                continue
            fname = None
            if isinstance(node.func, _ast.Attribute):
                fname = node.func.attr
            elif isinstance(node.func, _ast.Name):
                fname = node.func.id
            if fname not in ("assertEqual", "assertIn"):
                continue
            # Zweites Argument pruefen (String-Literal).
            if len(node.args) < 2:
                continue
            arg2 = node.args[1]
            if not isinstance(arg2, _ast.Constant):
                continue
            val = arg2.value
            if not isinstance(val, str):
                continue
            if val in erlaubt:
                continue
            # String, der wie ein Enum-Wert aussieht.
            if val.upper() in {e.upper() for e in erlaubt}:
                befunde.append(
                    f"{fname}(..., {val!r}): erlaubt sind "
                    f"{sorted(erlaubt)[:5]}")
    return befunde


