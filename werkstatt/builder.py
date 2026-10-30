"""Builder-Agent (Phase 6, 2026-10-23).

Eigenstaendiger Builder. Liest Plan + Code,
ruft ask_llm auf, generiert Patch (str_replace).
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from werkstatt.agent import ask_llm
from werkstatt.audit import audit
from werkstatt.state import RunState

_REVIEWER_SCHNITTSTELLE = """## DER REVIEWER (Schnittstelle)
- Prueft: bricht der Code? Task erfuellt? Bestehende Aufrufe erhalten?
- HIGH-Bug wenn: bestehender Aufruf entfernt, Funktion ueberschrieben, API erfunden.
"""


BUILDER_SYSTEM = """Du bist ein Editor.
Du bekommst eine ZIELDATEI und eine ARCHITECT-BESCHREIBUNG.

Deine Aufgabe: Setze die Architect-Beschreibung in search/replace-Patches um.

## Format (NUR search/replace)

Antworte mit JSON:
{
  "patches": [
    {"action": "update", "file": "zieldatei.py",
     "old_string": "<exakter Text aus der Datei>",
     "new_string": "<neuer Text>"},
    {"action": "create", "file": "neue_datei.py",
     "content": "<kompletter Datei-Inhalt>"}
  ]
}

Regeln:
  - old_string MUSS zeichengenau aus dem AKTUELLEN DATEI-INHALT
    stammen (siehe "AKTUELLER DATEI-INHALT" unten). NICHT aus dem
    Gedaechtnis erfinden, NICHT aus vorherigen Runden.
  - Wenn du unsicher bist, ob old_string noch stimmt: waehle einen
    kuerzeren, eindeutigen old_string (5-10 Zeilen) aus dem aktuellen
    Inhalt.
  - old_string != new_string.
  - LOESCHE KEINE ZEILEN, die nicht in old_string stehen. Wenn die
    Task "entferne X" sagt, dann entferne NUR X, nicht den Rest
    der Datei. old_string muss genau die zu entfernenden Zeilen
    enthalten, nicht mehr und nicht weniger. Bei Doku-Aufgaben
    (z.B. "entferne Punkt 1 aus docs/STATUS.md"): old_string =
    die exakten Zeilen von Punkt 1, new_string = "" (leer).
  - KEIN Aider-Format. KEIN "context" + "old" + "new".
    Nur "old_string" + "new_string".

  - Fuer NEUE Dateien: action="create" mit "content"
    (kompletter Datei-Inhalt, kein old_string).
    Nutze "create", wenn der Task eine neue Datei anlegen soll.
  - KEIN write_file. KEINE Tools.
  - Aendere NUR die ZIELDATEI.
  - Code MUSS ruff-konform sein (__all__ sortiert, kein except Exception).
  - Halte dich EXAKT an den Architect-Text.
  - Keine API-Aenderungen (keine Umbenennungen).

## GOLD: Erweitern statt Ueberschreiben (STRIKT)

Wenn du eine BESTEHENDE Funktion/Methode/Klasse erweiterst:
  - ERHALTE ALLE bestehenden Zeilen.
  - FUEGE NUR die neuen Zeilen hinzu.
  - old_string MUSS nur den ERWEITERUNGSPUNKT enthalten, NICHT
    die ganze Funktion.
  - new_string MUSS den alten Inhalt PLUS die Erweiterung enthalten.

Beispiel GUT (erweitern):
  old_string:
    def dashboard_state():
        body = {"timestamp": ...}
        body["devices"] = _section_devices()
  new_string:
    def dashboard_state():
        body = {"timestamp": ...}
        body["devices"] = _section_devices()
        body["timeline"] = _section_timeline()

Beispiel SCHLECHT (ueberschreiben — VERBOTEN):
  old_string:
    def dashboard_state():
        body = {"timestamp": ...}
        body["devices"] = _section_devices()
  new_string:
    def dashboard_state():
        body = {"timeline": _section_timeline()}

Regel: body["x"] = ... ist OK (dict erweitern).
       body = {...} ist VERBOTEN (dict ersetzen).

Wenn du eine Funktion erweiterst: das alte body-Dict MUSS im
new_string vollstaendig enthalten sein. Sonst sind bestehende
Sektionen weg.

## FUNKTION-WAHL (verbindlich)
- Wenn die Task eine Funktion/Klasse X namentlich nennt: waehle X.
  Nicht die "aehnlichste", nicht die kuerzere.
- Bei Namens-Aehnlichkeit (z.B. `_section_timeline` vs.
  `_section_timeline_entries`): pruefe, welche die Task nennt,
  und nutze genau diese.
- Wenn du unsicher bist: Task failen lassen, nicht raten.

## RUFF-GRUNDREGELN (verbindlich)

Der Verify-Schritt faehrt `ruff check` auf den geaenderten Dateien.
Wenn du eine dieser Regeln verletzt, wird der Patch verworfen.

- **PLR0124 (self-comparison):** Kein `value != value` oder `x == x`.
  NaN-Check via `math.isnan(value)` (Import `math` ergaenzen) oder
  `value != value  # noqa: PLR0124` direkt an der Zeile.
  Kein `# noqa: PLR0124` an einer anderen Zeile als der Verletzung.
- **F821 (undefined name):** `Mapping` erfordert
  `from collections.abc import Mapping`. Pruefe VOR dem Patch, ob
  das Symbol importiert ist; wenn nicht, Import im selben Patch
  ergaenzen.
- **F401 (unused import):** Keinen Import hinzufuegen, der nicht
  benutzt wird. Wenn du einen Import entfernst, pruefe mit Grep,
  ob er noch gebraucht wird.
- **E501 (line too long):** Zeilen <= 100 Zeichen. Lange Ausdruecke
  auf mehrere Zeilen umbrechen.
- **S110 (try/except/pass):** Kein `except: pass` ohne Logging.
  Wenn noetig: `except Exception as _e:  # noqa: BLE001` + `audit(...)`
  oder `logger.warning(...)`.
- **Allgemein:** Wenn ein Ruff-Fix (`ruff check --fix`) etwas
  entfernt, was inhaltlich gebraucht wird (z.B. `noqa` an einer
  berechtigten Stelle), pruefe danach erneut mit `ruff check`.
  Kein Fix ohne Nachkontrolle.

"""


_PY_IGNORE_PARTS = frozenset({
    ".venv", "venv", "__pycache__", "site-packages",
    "node_modules", ".git", ".tox", ".mypy_cache",
    ".pytest_cache", ".ruff_cache", ".eggs", "build", "dist",
})


def _sammle_projekt_py_files(project_dir: Path, limit: int = 30) -> list[Path]:
    """K10: Sammelt max `limit` .py-Dateien im Projekt, ohne Ignorier-Pfade.

    Filtert .venv, site-packages, __pycache__, node_modules etc.
    Sonst landen bei einem Projekt mit .venv die ersten N Treffer
    ausschliesslich in den venv-Paketen.
    """
    out: list[Path] = []
    for f in sorted(Path(project_dir).rglob("*.py")):
        try:
            rel_parts = set(f.relative_to(project_dir).parts)
        except ValueError:
            continue
        if rel_parts & _PY_IGNORE_PARTS:
            continue
        out.append(f)
        if len(out) >= limit:
            break
    return out


def _builder_system() -> str:
    """M-416: Editor-Modus. Nur Architect-Text + Edit-Format."""
    # GOLD: Reviewer-Schnittstelle anhaengen.
    return BUILDER_SYSTEM + "\n\n" + _REVIEWER_SCHNITTSTELLE


def _finde_modul_pfad(modul: str, project_dir: Path) -> Path | None:
    """M-444b: Findet den Pfad zu einem Modul (Datei oder Package).

    Versteht dotted paths: 'core.models' -> core/models.py
    oder core/models/__init__.py.
    """
    teile = modul.split(".")
    base = project_dir
    for teil in teile[:-1]:
        base = base / teil
        if not base.is_dir():
            return None
    letzter = teile[-1]
    datei = base / f"{letzter}.py"
    if datei.is_file():
        return datei
    pkg = base / letzter / "__init__.py"
    if pkg.is_file():
        return pkg
    return None


def _hat_symbol(modul_pfad: Path, symbol: str) -> bool:
    """M-444b: Prueft, ob ein Modul ein Symbol (class/def/var) definiert."""
    import ast as _ast
    try:
        tree = _ast.parse(modul_pfad.read_text(encoding="utf-8", errors="replace"))
    except (SyntaxError, OSError):
        return False
    for node in tree.body:
        if isinstance(node, _ast.ClassDef) and node.name == symbol:
            return True
        if isinstance(node, _ast.FunctionDef) and node.name == symbol:
            return True
        if isinstance(node, _ast.AsyncFunctionDef) and node.name == symbol:
            return True
        if isinstance(node, _ast.Assign):
            for t in node.targets:
                if isinstance(t, _ast.Name) and t.id == symbol:
                    return True
        if isinstance(node, _ast.AnnAssign):
            if isinstance(node.target, _ast.Name) and node.target.id == symbol:
                return True
    return False


def _validate_imports_in_patch(
    new_string: str, project_dir: Path,
    task_files: list[str] | None = None,
) -> list[str]:
    """M-444b: Findet unaufloesbare Imports (Modul UND Symbol).

    Prueft `import X`, `from X import Y` und `from X.Y import Z` gegen:
    - stdlib
    - Projekt-Module
    - venv-Pakete
    - Symbol-Existenz (via AST), wenn Modul im Projekt liegt und
      Symbol NICHT im selben Patch definiert wird.
    """
    import re as _re
    import sys as _sys

    fehlend: list[str] = []

    # Sammle Symbole, die im Patch selbst definiert werden (class X, def X).
    _im_patch_definiert: set[str] = set()
    for m in _re.finditer(r"^(?:class|def)\s+(\w+)", new_string, _re.MULTILINE):
        _im_patch_definiert.add(m.group(1))
    for m in _re.finditer(r"^async\s+def\s+(\w+)", new_string, _re.MULTILINE):
        _im_patch_definiert.add(m.group(1))
    for m in _re.finditer(r"^([A-Z][A-Z0-9_]*)\s*=", new_string, _re.MULTILINE):
        _im_patch_definiert.add(m.group(1))

    # Pattern 1: from X import Y, Z
    from_re = _re.compile(
        r"^\s*from\s+([\w.]+)\s+import\s+([^\n]+)", _re.MULTILINE,
    )
    from_imports: list[tuple[str, list[str]]] = []
    for m in from_re.finditer(new_string):
        modul = m.group(1)
        # Symbole: "Y, Z" oder "Y as Z, ..."
        roh = m.group(2).strip().rstrip("()")
        syms = []
        for teil in roh.split(","):
            teil = teil.strip()
            if not teil:
                continue
            # "X as Y" -> X
            if " as " in teil:
                teil = teil.split(" as ")[0].strip()
            if teil and teil != "*":
                syms.append(teil)
        from_imports.append((modul, syms))

    # Pattern 2: import X.Y
    imp_re = _re.compile(r"^\s*import\s+([\w.]+)", _re.MULTILINE)
    imp_mods: set[str] = set()
    for m in imp_re.finditer(new_string):
        imp_mods.add(m.group(1))

    # M-451: stdlib-Check auf Top-Level. sys.stdlib_module_names
    # enthaelt nur Top-Level (collections), nicht submodule
    # (collections.abc). Submodule sind aber Teil der stdlib.
    stdlib = getattr(_sys, "stdlib_module_names", set())
    venv_site_dirs: list[Path] = []
    venv_lib = project_dir / ".venv" / "lib"
    if venv_lib.is_dir():
        for site in venv_lib.iterdir():
            sp = site / "site-packages"
            if sp.is_dir():
                venv_site_dirs.append(sp)

    def _modul_existiert(modul: str) -> bool:
        # M-451: Top-Level-Check. collections.abc -> collections.
        top = modul.split(".")[0]
        if top in stdlib:
            return True
        if _finde_modul_pfad(top, project_dir):
            # Fuer submodule auch den vollen Pfad pruefen.
            if modul != top:
                sub_path = project_dir / modul.replace(".", "/")
                if sub_path.with_suffix(".py").is_file() or (sub_path / "__init__.py").is_file():
                    return True
                return False
            return True
        for sp in venv_site_dirs:
            if (sp / top).is_dir() or (sp / f"{top}.py").is_file():
                return True
        return False

    # Modulpruefung
    for mod in imp_mods:
        if not _modul_existiert(mod):
            fehlend.append(mod)
    for modul, _syms in from_imports:
        if not _modul_existiert(modul):
            fehlend.append(modul)

    # Symbolpruefung (nur fuer Projekt-Module; stdlib/venv ignorieren).
    for modul, syms in from_imports:
        if not _modul_existiert(modul):
            continue  # Modul-Fehler schon gemeldet
        if modul in stdlib:
            continue
        mod_pfad = _finde_modul_pfad(modul, project_dir)
        if mod_pfad is None:
            continue  # venv-Paket; Symbol nicht pruefbar
        # M-451: Symbole, die in anderen task_files definiert werden,
        # sind gueltig (Cross-File-Importe).
        _andere_defs: set[str] = set()
        if task_files:
            for _tf in task_files:
                _tf_path = project_dir / _tf
                if _tf_path.is_file() and _tf_path != mod_pfad:
                    for _sym in syms:
                        if _hat_symbol(_tf_path, _sym):
                            _andere_defs.add(_sym)
        for sym in syms:
            if sym in _im_patch_definiert:
                continue  # wird im selben Patch definiert
            if sym in _andere_defs:
                continue  # wird in anderer Datei definiert
            if not _hat_symbol(mod_pfad, sym):
                fehlend.append(f"{modul}.{sym}")

    return fehlend


def _normalisiere_aider_patches(
    patches: list, *, pd: Path, pn: str,
) -> list:
    """K48: Aider-Format (context+old+new) auf old_string/new_string
    normalisieren. Idempotent: Legacy-Patches laufen unveraendert durch.

    Wird von BEIDEN Builder-Pfaden aufgerufen:
      - Architect-Pfad (_build_patches_fuer_datei)
      - Klassischer Pfad (run_builder, direkter ask_llm-Call)
    """
    _out: list = []
    for _p in patches:
        if not isinstance(_p, dict):
            _out.append(_p)
            continue
        if _p.get("context") and _p.get("old") and _p.get("new") is not None:
            # K53b: Aider-Fallback. Wenn context+old nicht in Datei
            # passt, aber old allein: context verwerfen.
            _ctx_raw = _p["context"]
            _old = _p["old"]
            _new_val = _p["new"]
            _target = Path(pd) / _p.get("file", "")
            _use_context = True
            if _target.is_file():
                try:
                    _content = _target.read_text(encoding="utf-8")
                except OSError:
                    _content = ""
                if _content:
                    _candidates = (
                        _ctx_raw.rstrip() + "\n\n" + _old,
                        _ctx_raw + _old,
                    )
                    _with_ctx_ok = any(c in _content for c in _candidates)
                    _old_only_ok = _old in _content
                    if _old_only_ok and not _with_ctx_ok:
                        _use_context = False
            if _use_context:
                _ctx = _ctx_raw.rstrip() + "\n\n"
                _p = {
                    **_p,
                    "old_string": _ctx + _old,
                    "new_string": _ctx + _new_val,
                }
            else:
                _p = {
                    **_p,
                    "old_string": _old,
                    "new_string": _new_val,
                }
                audit("builder_aider_context_verworfen",
                      {"file": _p.get("file", "")}, pd, pn)
            _p.pop("context", None)
            _p.pop("old", None)
            _p.pop("new", None)
            audit("builder_aider_patch_normalisiert",
                  {"file": _p.get("file", ""),
                   "with_context": _use_context}, pd, pn)
        _out.append(_p)
    return _out


def _filtere_auf_funktionen(abschnitt: str, task_text: str) -> str:
    """GOLD: Filtert Datei-Abschnitt auf in Task genannte Funktionen.

    No-op, wenn task_text leer oder keine Kandidaten gefunden.
    """
    import re
    if not abschnitt or not task_text:
        return abschnitt
    _kandidaten = set()
    for _m in re.finditer(r"`([_a-zA-Z][_a-zA-Z0-9]{2,})`", task_text):
        _kandidaten.add(_m.group(1))
    for _m in re.finditer(r"\bdef\s+([_a-zA-Z][_a-zA-Z0-9]{2,})", task_text):
        _kandidaten.add(_m.group(1))
    for _m in re.finditer(r"\bclass\s+([_a-zA-Z][_a-zA-Z0-9]{2,})", task_text):
        _kandidaten.add(_m.group(1))
    if not _kandidaten:
        return abschnitt
    _bloecke = re.findall(r"```(?:python)?\n(.*?)```", abschnitt, re.DOTALL)
    if not _bloecke:
        return abschnitt
    _gefiltert = []
    for _block in _bloecke:
        for _name in _kandidaten:
            if re.search(rf"\bdef\s+{re.escape(_name)}\b", _block) or \
               re.search(rf"\bclass\s+{re.escape(_name)}\b", _block):
                _gefiltert.append(_block)
                break
    if not _gefiltert:
        return abschnitt
    return "\n\n".join(_gefiltert)


def _architect_abschnitt(
    beschreibung: str, zieldatei: str, task_text: str = "",
) -> str:
    """M-408c/M-450 + GOLD: Extrahiert den Abschnitt fuer eine Datei.

    Unterstuetzt ZWEI Formate:
    A) '## <pfad>'-Ueberschriften (alter Architect-Prompt):
       -> exakter Abschnitt.
    B) '## 3. Wie sieht die Loesung aus?' + darin '## <pfad>'
       (Gold-Architect-Prompt):
       -> Abschnitt ab '## <pfad>' bis zum naechsten '## '.

    Fallback: ganze Prosa.
    """
    import re
    if not beschreibung:
        return ""
    _hat_ueberschriften = bool(
        re.search(r"^##\s+\S", beschreibung, re.MULTILINE)
    )
    if not _hat_ueberschriften:
        return beschreibung
    # Format A: '## <pfad>' direkt.
    pattern_direct = rf"^##\s*{re.escape(zieldatei)}\s*$"
    m = re.search(pattern_direct, beschreibung, re.MULTILINE)
    if m:
        start = m.end()
        _next = re.search(r"^##\s+\S", beschreibung[start:], re.MULTILINE)
        if _next:
            return _filtere_auf_funktionen(beschreibung[start:start + _next.start()].strip(), task_text)
        return _filtere_auf_funktionen(beschreibung[start:].strip(), task_text)
    # Format B: '## <pfad>' innerhalb einer Sektion. Suche im
    # gesamten Text nach '## <pfad>' — auch wenn davor '## 3.' steht.
    for _m in re.finditer(
        rf"^##\s*{re.escape(zieldatei)}\s*$", beschreibung, re.MULTILINE
    ):
        start = _m.end()
        _next = re.search(r"^##\s+\S", beschreibung[start:], re.MULTILINE)
        if _next:
            return _filtere_auf_funktionen(beschreibung[start:start + _next.start()].strip(), task_text)
        return _filtere_auf_funktionen(beschreibung[start:].strip(), task_text)
    return ""  # Datei nicht in der Prosa





def _extrahiere_verbote(abschnitt: str) -> str:
    """FIX 2026-10-31: Zieht negative Anweisungen aus der Prosa.

    LLMs ignorieren Negativ-Anweisungen in langer Prosa. Wir stellen
    sie isoliert VOR die Prosa als eigenen Block.
    """
    import re as _re_v
    if not abschnitt:
        return ""
    _marker = _re_v.compile(
        r"\b(nicht|kein|keine|keiner|behalte|behalten|erhalte|erhalten|"
        r"nur|ausschliesslich|vermeide|verboten)\b",
        _re_v.IGNORECASE,
    )
    _saetze = _re_v.split(r"(?<=[.!?])\s+", abschnitt)
    _verbote: list[str] = []
    for _s in _saetze:
        _s_clean = _s.strip()
        if len(_s_clean) < 15 or len(_s_clean) > 400:
            continue
        if _marker.search(_s_clean):
            _verbote.append(_s_clean)
        if len(_verbote) >= 5:
            break
    if not _verbote:
        return ""
    return (
        "<verbote verbindlich=\"true\">\n"
        "Diese Anweisungen sind HART. Verletze sie NICHT:\n"
        + "\n".join(f"- {v}" for v in _verbote)
        + "\n</verbote>"
    )





def _pruefe_doku_patch_breite(
    patches: list, aufgabe: str, zieldatei: str, pd, pn,
) -> list:
    """FIX 2026-10-31: Reiner Loesch-Patch fuer Doku darf nicht
    mehrere nummerierte Punkte loeschen, wenn der Auftrag
    "nicht umnummerieren"/"behalte"/"unveraendert" sagt.

    Live-Beleg 2026-10-30 23:32: Builder loeschte Punkt 1+2,
    Nummerierung 2-7 rutschte auf 1-6.
    """
    import re as _re_breite
    if not patches:
        return patches
    _aufgabe_l = (aufgabe or "").lower()
    _negativ = (
        "nicht umnummerier" in _aufgabe_l
        or "keine umnummerier" in _aufgabe_l
        or "behalte" in _aufgabe_l
        or "unveraendert" in _aufgabe_l
        or "unverandert" in _aufgabe_l
        or "unverändert" in _aufgabe_l
    )
    if not _negativ:
        return patches
    _punkt_re = _re_breite.compile(r"^\s*\d+\.", _re_breite.MULTILINE)
    _ok: list = []
    for _p in patches:
        if not isinstance(_p, dict):
            _ok.append(_p)
            continue
        if _p.get("action", "update") != "update":
            _ok.append(_p)
            continue
        _new = _p.get("new_string", "") or ""
        _old = _p.get("old_string", "") or ""
        if _new.strip() != "":
            _ok.append(_p)
            continue
        _n_punkte = len(_punkt_re.findall(_old))
        if _n_punkte > 1:
            audit("builder_patch_zu_breit", {
                "zieldatei": zieldatei,
                "nummerierte_punkte_im_old": _n_punkte,
                "old_prefix": _old[:200],
            }, pd, pn)
            continue
        _ok.append(_p)
    return _ok


def _build_patches_fuer_datei(
    state: RunState,
    zieldatei: str,
    architect_beschreibung: str,
    api_key: str,
) -> list[dict]:
    """M-416b: Baut Patches fuer EINE Datei im Architect-Modus.

    Macht einen LLM-Aufruf, parst die Antwort, gibt Patches zurueck.
    Bei Fehler: leere Liste (Aufrufer entscheidet fail-closed).
    """
    import json as _json

    pd = state.project_dir
    pn = state.project_name
    _target = pd / zieldatei
    if not _target.is_file():
        return []
    try:
        _inhalt = _target.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    _task_fuer_filter = getattr(state, "aktuelle_task", None) or {}
    if isinstance(_task_fuer_filter, dict):
        _filter_text = (
            (_task_fuer_filter.get("name") or "") + "\n"
            + (_task_fuer_filter.get("description") or "")
        )
    else:
        _filter_text = ""
    _abschnitt = _architect_abschnitt(
        architect_beschreibung, zieldatei, task_text=_filter_text,
    )
    # GOLD-Fallback: Task-Description enthaelt oft nicht die
    # "## <pfad>"-Ueberschrift. Dann auf die volle Architect-Prosa
    # zurueckfallen (state.architect_prosa).
    if not _abschnitt:
        _volle = getattr(state, "architect_prosa", "") or ""
        if _volle:
            _abschnitt = _architect_abschnitt(
            _volle, zieldatei, task_text=_filter_text,
        )
    # M-450: Leerer Abschnitt -> Datei ist nicht Teil der Aufgabe.
    # Kein LLM-Aufruf, kein Patch.
    if not _abschnitt:
        audit("builder_architect_datei_nicht_beschrieben",
              {"datei": zieldatei}, pd, pn)
        return []
    # M-444b: Feedback aus vorherigem Versuch einbauen.
    _feedback = (getattr(state, "builder_feedback", None) or {}).get(zieldatei, "")
    _feedback_block = ""
    if _feedback:
        _feedback_block = (
            f"\n\n## FEEDBACK AUS VORHERIGEM VERSUCH:\n"
            f"Der letzte Patch wurde verworfen. Grund:\n{_feedback}\n"
            f"Behebe das in dieser Antwort.\n"
        )
    # M-466: Reviewer-Bugs aus letzter Runde in den Prompt.
    _reviewer_bugs = getattr(state, "reviewer_bugs", None) or []
    if _reviewer_bugs:
        _bug_lines = []
        for _b in _reviewer_bugs:
            if not isinstance(_b, dict):
                continue
            _sev = _b.get("severity", "?")
            _desc = _b.get("description", "")
            if _desc:
                _bug_lines.append(f"- [{_sev}] {_desc}")
        if _bug_lines:
            _feedback_block += (
                "\n\n## REVIEWER-FEEDBACK (aus letzter Runde):\n"
                + "\n".join(_bug_lines)
                + "\nBehebe diese Bugs in dieser Antwort.\n"
            )
    # K33: Verify-Fehler (Ruff/Compile) aus letzter Runde als Feedback.
    _verify_errs = getattr(state, "last_verify_errors", None) or []
    if _verify_errs:
        _err_lines = [str(e)[:500] for e in _verify_errs[:5]]
        _feedback_block += (
            "\n\n## VERIFY-FEHLER (aus letzter Runde):\n"
            + "\n".join(f"- {e}" for e in _err_lines)
            + "\nBehebe diese Fehler in dieser Antwort.\n"
        )
    # K47: Reflection-Historie -- was in vorherigen Runden passiert ist.
    _refl_hist = getattr(state, "reflection_history", None) or []
    if _refl_hist:
        _refl_lines = ["\n\n## VORHERIGE REFLECTION-RUNDEN (was du bereits versucht hast):\n"]
        for _r in _refl_hist[-3:]:  # max 3 Runden
            _rn = _r.get("runde", "?")
            _pa = _r.get("patches_applied", 0)
            _ve = _r.get("verify_errors", [])[:2]
            _rb = _r.get("reviewer_bugs", [])[:2]
            _refl_lines.append(f"\n### Runde {_rn}:\n")
            _refl_lines.append(f"- Patches: {_pa} angewendet\n")
            if _ve:
                _refl_lines.append("- Verify-Fehler:\n")
                for _e in _ve:
                    _refl_lines.append(f"  * {str(_e)[:200]}\n")
            if _rb:
                _refl_lines.append("- Reviewer-Bugs:\n")
                for _b in _rb:
                    _sv = _b.get("severity", "?")
                    _ds = (_b.get("description") or _b.get("beschreibung") or "")[:150]
                    _refl_lines.append(f"  * [{_sv}] {_ds}\n")
        _refl_lines.append(
            "\nWiederhole NICHT die gleichen Versuche. Pruefe den aktuellen "
            "Dateiinhalt und waehle old_string zeichengenau.\n"
        )
        _feedback_block += "".join(_refl_lines)
    # M-466: Task-Name + Beschreibung fuer Kontext.
    _task = getattr(state, "aktuelle_task", None) or {}
    _task_name = _task.get("name", "") if isinstance(_task, dict) else ""
    _task_desc = _task.get("description", "") if isinstance(_task, dict) else ""
    _verbote = _extrahiere_verbote(_abschnitt)
    _verbote_prefix = (_verbote + "\n\n") if _verbote else ""
    _user = (
        f"## ZIELDATEI: {zieldatei}\n\n"
        f"{_verbote_prefix}"
        f"## TASK: {_task_name}\n"
        f"## TASK-BESCHREIBUNG: {_task_desc}\n\n"
        f"## ARCHITECT-BESCHREIBUNG (fuer Kontext):\n{_abschnitt}\n\n"
        f"## AKTUELLER DATEI-INHALT:\n```python\n{_inhalt}\n```\n"
        f"{_feedback_block}"
    )
    reply = ask_llm(
        api_key, BUILDER_SYSTEM, _user,
        model="deepseek-chat", temperature=0.2, max_tokens=8000,
    )
    if not reply.ok:
        audit("builder_architect_llm_fehler",
              {"datei": zieldatei, "fehler": reply.error}, pd, pn)
        return []
    raw = reply.content.strip()
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start < 0 or end <= start:
        audit("builder_architect_json_fehler",
              {"datei": zieldatei, "raw": raw[:200]}, pd, pn)
        return []
    try:
        parsed = _json.loads(raw[start:end])
    except _json.JSONDecodeError:
        return []
    patches = parsed.get("patches") or []
    if not isinstance(patches, list):
        return []
    if not patches:
        # GOLD 2026-10-30: LLM hat geantwortet, aber keine Patches
        # geliefert. Das ist der "Auftrag bereits erfuellt"-Fall —
        # die Zieldatei enthaelt den Zielzustand schon (z.B.
        # _RECENT_CHANGES_LIMIT aus f69f1b2).
        # Vorher: return [] -> run_builder False -> task_failed.
        # Jetzt: Flag setzen, run_builder entscheidet.
        if isinstance(state, object) and hasattr(state, "__dict__"):
            try:
                state.auftrag_bereits_erfuellt = True  # type: ignore[attr-defined]
            except (AttributeError, TypeError):
                pass
        audit("auftrag_bereits_erfuellt",
              {"zieldatei": zieldatei,
               "grund": "llm_keine_patches"}, pd, pn)
        audit("builder_keine_patches_gold",
              {"zieldatei": zieldatei,
               "grund": "llm_keine_patches"}, pd, pn)
        return []
    for p in patches:
        if isinstance(p, dict):
            p["file"] = zieldatei
    # M-444: Import-Validierung. Patches mit unaufloesbaren Imports
    # werden verworfen — sonst bricht der Verify-Loop mit
    # ModuleNotFoundError (RERUN-54: core.changeapplier.errors).
    _gueltig: list[dict] = []
    _feedback_neu: list[str] = []
    for p in patches:
        if not isinstance(p, dict):
            continue
        # M-444c: Pruefe new_string UND old_string zusammen.
        # Sonst uebersehen wir Importe, die nur in old_string stehen
        # (und entfernt werden sollen). Verwirft den GANZEN Patch,
        # wenn ein Import ungueltig ist.
        _patch_text = (
            (p.get("old_string", "") or "")
            + "\n"
            + (p.get("new_string", "") or "")
            + "\n"
            + (p.get("context", "") or "")
            + "\n"
            + (p.get("old", "") or "")
            + "\n"
            + (p.get("new", "") or "")
        )
        _fehlend = _validate_imports_in_patch(
            _patch_text, pd,
            task_files=getattr(state, "tasks", [{}])[0].get("task_files", []) if getattr(state, "tasks", None) else None,
        )
        if _fehlend:
            audit("builder_patch_import_fehler",
                  {"datei": zieldatei, "fehlend": _fehlend}, pd, pn)
            _feedback_neu.append(
                "Import nicht aufloesbar: " + ", ".join(_fehlend)
                + ". Verwende existierende Symbole oder definiere "
                "sie im selben Patch (class/def/var)."
            )
            continue
        _gueltig.append(p)

    # M-444b: Feedback speichern, damit der naechste Aufruf es sieht.
    if _feedback_neu:
        if not getattr(state, "builder_feedback", None):
            state.builder_feedback = {}  # type: ignore[attr-defined]
        state.builder_feedback[zieldatei] = "\n".join(_feedback_neu)  # type: ignore[attr-defined]
    else:
        if getattr(state, "builder_feedback", None):
            state.builder_feedback.pop(zieldatei, None)  # type: ignore[attr-defined]

    # K48: Aider-Format auf Legacy normalisieren (zentraler Helper).
    _gueltig = _normalisiere_aider_patches(_gueltig, pd=pd, pn=pn)

    # GOLD 2026-10-30: Patches filtern, deren old_string NICHT in
    # der Datei ist, aber deren new_string SCHON in der Datei ist.
    # Das bedeutet: Auftrag bereits erfuellt. Live-Beleg 2026-10-30
    # 21:37:34: alerts.html hatte schon class="table table-alerts",
    # der Builder baute old_string='class="table"'. Apply scheiterte
    # (old_string_not_found), reviewer_kein_diff_aber_patches ->
    # fail-closed.
    _erfuellt: list[dict] = []
    for _p in _gueltig:
        if not isinstance(_p, dict):
            continue
        if _p.get("action", "update") != "update":
            _erfuellt.append(_p)
            continue
        _old = _p.get("old_string", "") or ""
        _new = _p.get("new_string", "") or ""
        if not _old or not _new:
            _erfuellt.append(_p)
            continue
        _old_in_datei = _old in _inhalt
        _new_in_datei = _new in _inhalt
        if not _old_in_datei and _new_in_datei:
            audit("auftrag_bereits_erfuellt",
                  {"zieldatei": zieldatei,
                   "grund": "old_nicht_da_aber_new_da",
                   "old_prefix": _old[:100],
                   "new_prefix": _new[:100]}, pd, pn)
            continue  # Patch verwerfen, Auftrag ist erfuellt
        _erfuellt.append(_p)

    if _gueltig and not _erfuellt:
        # Alle Patches waren "Auftrag bereits erfuellt".
        if isinstance(state, object) and hasattr(state, "__dict__"):
            try:
                state.auftrag_bereits_erfuellt = True  # type: ignore[attr-defined]
            except (AttributeError, TypeError):
                pass
        return []

    _erfuellt = _pruefe_doku_patch_breite(
        _erfuellt, getattr(state, 'aufgabe', ''), zieldatei, pd, pn,
    )
    return _erfuellt


def _korrigiere_builder_action(
    task: dict, pd: Path, pn: str,
) -> str:
    """K22b/c: Korrigiert Task-Action live gegen Dateisystem.

    - 'create' + Datei existiert -> 'update'
    - 'update' + Datei fehlt    -> 'create'

    Aendert task['action'] und gibt die (ggf. korrigierte)
    Action zurueck. Bei fehlendem task_files oder non-str:
    unveraendert.
    """
    act = task.get("action", "update")
    if act not in ("create", "update"):
        return act
    tf_list = task.get("task_files") or []
    if not tf_list or not isinstance(tf_list[0], str):
        return act
    ziel = pd / tf_list[0]
    exists = ziel.is_file()
    # K22b: NUR create->update bei existierender Datei
    # (Reflection-Runde 2: Datei ist aus Runde 1 da).
    # update->create wird NICHT korrigiert -- fail-closed bleibt.
    # Siehe test_builder_update_zieldatei_fehlt_bleibt_fail_closed.
    if act == "create" and exists:
        audit("builder_action_korrigiert",
              {"datei": tf_list[0], "von": "create", "nach": "update",
               "grund": "datei_existiert"},
              pd, pn)
        task["action"] = "update"
        return "update"
    return act


def run_builder(state: RunState) -> bool:
    """Erstellt Patches. Schreibt sie in state.patches (oder wendet sie an)."""
    pd = state.project_dir
    pn = state.project_name
    api_key = getattr(state, "api_key", "")

    if not api_key:
        audit("builder_kein_key", {}, pd, pn)
        return False

    tasks = getattr(state, "tasks", [])
    if not tasks:
        audit("builder_keine_tasks", {}, pd, pn)
        return False

    # M-306a: Read-only-Tasks. Wenn ALLE Tasks action="read" haben,
    # ist der Task eine Bestandsaufnahme. Builder ruft keinen LLM,
    # erzeugt keinen Patch. Gibt True (Task erfolgreich = Info
    # gesammelt).
    def _is_read_only(task_obj) -> bool:
        if not isinstance(task_obj, dict):
            return False
        return task_obj.get("action") == "read"

    if all(_is_read_only(t) for t in tasks):
        audit("builder_read_only", {"tasks": len(tasks)}, pd, pn)
        state.patches = []  # type: ignore[attr-defined]
        return True

    # M-317: Idempotenz-Check NUR bei action="create".
    # Bei "update" (Datei existiert + soll erweitert werden)
    # ist py_compile immer ok -> fail-open (M-317-Befund).
    # Also: bei update IMMER durch den LLM-Patch-Pfad.
    _current_action = None
    for _t_check in tasks:
        if isinstance(_t_check, dict):
            _current_action = _t_check.get("action")
            break
    # M-318: Idempotenz auch bei "update" pruefen. Wenn die Zieldatei
    # existiert und syntaktisch korrekt ist, ist "nichts zu tun" ein
    # legitimer Erfolg. M-317 hatte "nur create" — das war zu strikt:
    # ein update-Task, dessen Ziel durch einen vorherigen Task bereits
    # erfuellt wurde, wurde als Fehler gewertet.
    # Profi-Muster (Aider, Claude Code, SWE-agent): Erfuellung ist
    # Repo-Zustand nach Task, nicht "Patch nicht leer".
    # M-352: Idempotenz NUR bei create, wenn Zieldatei existiert.
    # Sonst: fail-closed (Builder muss Datei anlegen).
    if _current_action == "create":
        _task_obj = getattr(state, "aktuelle_task", None)
        if not isinstance(_task_obj, dict) or not _task_obj:
            _task_obj = next(
                (t for t in tasks if isinstance(t, dict)), {}
            )
        _files = (
            _task_obj.get("task_files", [])
            if isinstance(_task_obj, dict) else []
        )
        _any_exists = any(
            (pd / f).exists() for f in _files if isinstance(f, str)
        )
        # M-352-Fallback: task_files leer -> Dateiname aus name (M-317).
        if not _any_exists and not _files:
            import re as _re_fb
            _name_fb = (
                _task_obj.get("name", "") if isinstance(_task_obj, dict) else ""
            )
            for _m_fb in _re_fb.findall(
                r'\b([a-zA-Z_][a-zA-Z0-9_/]+\.'
                r'(?:md|py|yaml|yml|json|txt|toml|cfg|ini))\b',
                _name_fb,
            ):
                if (pd / _m_fb).exists():
                    _any_exists = True
                    break
        _allow_idempotent = _any_exists
    else:
        _allow_idempotent = False

    # M-316 (A1/A2): Idempotenz-Check (Variante iii: verify.py).
    # Wird nur bei create-Tasks verwendet (M-317).
    _target_files: list[Path] = []
    import re as _re2
    _file_pattern2 = _re2.compile(r'\b([a-zA-Z_][a-zA-Z0-9_/]+\.(?:md|py|yaml|yml|json|txt|toml|cfg|ini))\b')
    for _task_obj in tasks:
        _text2 = _task_obj if isinstance(_task_obj, str) else str(_task_obj)
        for _m2 in _file_pattern2.findall(_text2):
            _tf = pd / _m2
            if _tf.exists() and _tf.is_file() and _tf not in _target_files:
                _target_files.append(_tf)

    # M-337-c: Idempotenz-Check NUR wenn task_files leer ist.
    # Wenn task_files gesetzt: Der Planner will die Datei explizit
    # aendern. Idempotenz (M-318) wuerde den Patch ueberspringen.
    _aktuelle_task_early = getattr(state, "aktuelle_task", None)
    _hat_task_files = (
        isinstance(_aktuelle_task_early, dict)
        and bool(_aktuelle_task_early.get("task_files"))
    )

    if _target_files and _allow_idempotent and not _hat_task_files:
        _all_ok = True
        for _tf in _target_files:
            if _tf.suffix == ".py":
                _res = subprocess.run(
                    ["python3", "-m", "py_compile", str(_tf)],
                    capture_output=True, text=True, timeout=30, check=False,
                )
                if _res.returncode != 0:
                    _all_ok = False
                    audit("builder_zieldatei_inkorrekt",
                          {"file": str(_tf), "fehler": _res.stderr[:200]}, pd, pn)
                    break

        if _all_ok:
            # A2: Datei existiert UND ist korrekt -> task_ok.
            # Nur bei create-Tasks (M-317).
            audit("builder_nichts_zu_tun",
                  {"files": [str(f.name) for f in _target_files]}, pd, pn)
            state.patches = []  # type: ignore[attr-defined]
            return True

    # M-298d: On-demand Zieldatei lesen.
    # Profi-Ansatz (Aider Repo-Map, Cline read_file): Der Builder
    # liest nur die Dateien, die der Task betrifft — nicht die
    # ganze Codebase. Explorer-Report (key_files) zeigt WELCHE
    # Datei relevant ist; der Builder liest sie DANN selbst.
    #
    # Wir scannen den Task-Text nach Datei-Pfaden (typisch:
    # "README.md", "core/x.py"). Der erste Treffer wird gelesen.
    import re as _re
    _file_pattern = _re.compile(r'\b([a-zA-Z_][a-zA-Z0-9_/]+\.(?:md|py|yaml|yml|json|txt|toml|cfg|ini))\b')
    _relevant_files: list[str] = []
    for _task in tasks:
        _text = _task if isinstance(_task, str) else str(_task)
        for _m in _file_pattern.findall(_text):
            if _m not in _relevant_files:
                _relevant_files.append(_m)
    # M-335: task_files aus aktuellem Task (M-317) PRIORISIEREN.
    # Der Planner setzt explizite Datei-Pfade pro Task. Der Builder
    # hat sie bisher ignoriert — deshalb sah er oft die falsche
    # Datei (z.B. tools/port_check.py statt core/checks/).
    _aktuelle_task = getattr(state, "aktuelle_task", None)
    if isinstance(_aktuelle_task, dict):
        _task_files = _aktuelle_task.get("task_files", []) or []
        if _task_files:
            _task_files_str = [f for f in _task_files if isinstance(f, str)]
            if _task_files_str:
                # M-337-b: NUR task_files. Kein Regex, kein Explorer.
                # Der Builder soll nur die vom Planner genannten
                # Dateien sehen — nicht 6 andere.
                _relevant_files = list(_task_files_str)

    # M-337-b: Explorer-key_files NUR als Fallback, wenn
    # task_files leer war.
    _hat_task_files = (
        isinstance(_aktuelle_task, dict)
        and bool(_aktuelle_task.get("task_files"))
    )
    if not _hat_task_files:
        _expl = getattr(state, "explorer_context", {}) or {}
        for _f in _expl.get("key_files", []) or []:
            _f_str = None
            if isinstance(_f, str):
                _f_str = _f
            elif isinstance(_f, dict):
                _f_str = _f.get("file") or _f.get("path") or _f.get("name")
            if _f_str and _f_str not in _relevant_files:
                _relevant_files.append(_f_str)

    _file_context: dict[str, str] = {}
    # M-336: Ordner in _relevant_files aufloesen. Der Planner
    # setzt task_files manchmal als Ordner (z.B. "core/checks/")
    # statt als Datei ("core/checks/__init__.py"). is_file()
    # schlaegt dann fehl — der Builder sieht die Datei nicht.
    _aufgeloest: list[Path] = []
    for _rel in _relevant_files:
        if not isinstance(_rel, str):
            continue
        _target = pd / _rel
        if _target.is_dir():
            # Ordner: alle .py-Dateien darin (max 5)
            _aufgeloest.extend(sorted(_target.glob("*.py"))[:5])
        elif _target.is_file():
            _aufgeloest.append(_target)

    for _target in _aufgeloest[:5]:  # max 5, kein Kontext-Ballern
        try:
            _content = _target.read_text()
            # Nur letzte 50 Zeilen (On-Demand, nicht volle Datei)
            _tail = "\n".join(_content.splitlines()[-50:])
            _rel_str = str(_target.relative_to(pd))
            _file_context[_rel_str] = _tail
        except OSError:
            continue

    # M-333b: Bei create-Tasks (neue Dateien) gibt es keinen
    # _file_context (Datei existiert nicht). Wir sammeln die
    # Imports benachbarter .py-Dateien, damit der Builder weiss,
    # welche Module im Projekt existieren.
    _create_tasks = [
        t for t in tasks
        if isinstance(t, dict) and t.get("action") == "create"
    ]
    if _create_tasks:
        _imports_ctx: dict[str, str] = {}
        # Alle .py-Dateien im Projekt (max 30). K10: Ignorier-Pfade
        # (.venv, __pycache__, site-packages, node_modules) werden
        # in _sammle_projekt_py_files gefiltert.
        _py_files = _sammle_projekt_py_files(pd, limit=30)
        for _f in _py_files:
            if _f.is_file():
                try:
                    _lines = _f.read_text(encoding="utf-8").splitlines()
                except (OSError, UnicodeDecodeError):
                    continue
                _imports = [
                    ln for ln in _lines[:30]
                    if ln.startswith(("import ", "from "))
                ]
                if _imports:
                    _rel = str(_f.relative_to(pd))
                    _imports_ctx[_rel] = "\n".join(_imports)
        if _imports_ctx:
            _file_context["__projekt_imports__"] = (
                "\n\n".join(
                    f"--- {f} ---\n{imp}"
                    for f, imp in list(_imports_ctx.items())[:15]
                )
            )
            audit("builder_import_context",
                  {"files": list(_imports_ctx.keys())[:15]}, pd, pn)

    if _file_context:
        audit("builder_file_context", {"files": list(_file_context.keys())}, pd, pn)

    # M-337: Zieldatei deterministisch bestimmen aus task_files.
    # Der Builder bekommt KEINE freie Wahl. Er MUSS diese Datei
    # aendern (update) oder anlegen (create).
    _aktuelle_task = getattr(state, "aktuelle_task", None)
    if not isinstance(_aktuelle_task, dict):
        audit("builder_keine_aktuelle_task", {}, pd, pn)
        return False
    _task_files = _aktuelle_task.get("task_files", []) or []
    _current_action2 = _aktuelle_task.get("action", "update")
    _is_architect = _current_action2 == "architect"
    # K22b/c: Action live gegen Dateisystem korrigieren.
    # K34: NICHT in Reflection-Runde (Task-Action bleibt wie im Plan).
    if not _is_architect and not getattr(state, "reflection_phase", False):
        _current_action2 = _korrigiere_builder_action(
            _aktuelle_task, pd, pn,
        )
    _architect_beschreibung = _aktuelle_task.get("description", "") if _is_architect else ""

    # M-416b: Architect-Modus -> Editor pro Datei.
    # Wird VOR der normalen Zieldatei-Wahl ausgefuehrt.
    if _is_architect:
        _alle_dateien = [f for f in _task_files if isinstance(f, str) and f]
        if not _alle_dateien:
            audit("builder_architect_keine_dateien", {}, pd, pn)
            return False
        _alle_patches: list[dict] = []
        _dateien_ok: list[str] = []
        for _zd in _alle_dateien:
            _target = pd / _zd
            if not _target.is_file():
                audit("builder_architect_datei_fehlt",
                      {"datei": _zd}, pd, pn)
                continue
            _patches = _build_patches_fuer_datei(
                state, _zd, _architect_beschreibung, api_key,
            )
            if _patches:
                _alle_patches.extend(_patches)
                _dateien_ok.append(_zd)
        if not _alle_patches:
            audit("builder_architect_keine_patches",
                  {"dateien": _alle_dateien}, pd, pn)
            return False
        state.patches = _alle_patches
        audit("builder_architect_patches",
              {"anzahl_patches": len(_alle_patches),
               "dateien": _dateien_ok}, pd, pn)
        return True

    _zieldatei = None
    for _tf in _task_files:
        if not isinstance(_tf, str):
            continue
        _target = pd / _tf
        if _target.is_dir():
            _init = _target / "__init__.py"
            if _init.exists():
                _zieldatei = str(_init.relative_to(pd))
                break
            _py = sorted(_target.glob("*.py"))
            if _py:
                _zieldatei = str(_py[0].relative_to(pd))
                break
        elif _target.is_file():
            _zieldatei = _tf
            break

    if _zieldatei is None:
        # M-360: Bei create-Tasks ist das Fehlen der Zieldatei
        # ERWARTET (die Datei soll angelegt werden). Statt
        # fail-closed nehmen wir die erste task_file als Ziel
        # und lassen das LLM sie anlegen.
        # Bei update/read: Datei MUSS existieren -> fail-closed.
        if _current_action2 == "create":
            _erste = next(
                (f for f in _task_files if isinstance(f, str) and f),
                None,
            )
            if _erste:
                _zieldatei = _erste
                audit("builder_zieldatei_create_neu",
                      {"task_files": _task_files, "zieldatei": _zieldatei},
                      pd, pn)
            else:
                audit("builder_zieldatei_nicht_gefunden",
                      {"task_files": _task_files, "action": _current_action2},
                      pd, pn)
                return False
        else:
            audit("builder_zieldatei_nicht_gefunden",
                  {"task_files": _task_files, "action": _current_action2},
                  pd, pn)
            return False

    # Volle Zieldatei in den Prompt (nicht letzte 50 Zeilen),
    # damit old_string exakt passt.
    _zieldatei_path = pd / _zieldatei
    if _zieldatei_path.exists() and _zieldatei_path.is_file():
        try:
            _file_context[_zieldatei] = _zieldatei_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            pass

    aufgabe = getattr(state, "aufgabe", "")

    # Aktuellen Code lesen (vereinfacht: aus state.docs oder direkt)
    # Fuer Phase 6 nehmen wir einen Platzhalter, spaeter wird das aus dem Repo gelesen.

    # M-337: user_content mit Zieldatei + Aktion. KEINE Task-Liste
    # (der LLM soll nicht frei entscheiden).
    user_content = (
        f"ZIELDATEI: {_zieldatei}\n"
        f"AKTION: {_current_action2}\n\n"
        f"AUFGABE: {aufgabe}\n\n"
        f"AKTUELLER TASK: {json.dumps(_aktuelle_task, ensure_ascii=False)}"
    )

    # M-329a: Fehler-Kontext aus Reflection (_verify_patches).
    _verify_errors = getattr(state, "last_verify_errors", None)
    if _verify_errors:
        _err_text = "\n".join(str(e) for e in _verify_errors)[:3000]
        user_content += (
            f"\n\nDer letzte Patch hat die Tests zerstoert. "
            f"Hier ist der Fehler-Output:\n\n{_err_text}\n\n"
            "Behebe NUR diesen Fehler. Nutze old_string/new_string. "
            "M-383: Wenn der Fehler RUF100 (unused noqa) ist: Entferne den # noqa NICHT, wenn der Code absichtlich so ist (Negativtest, naive datetime). Behalte den # noqa. " 
            "Wenn ein Import fehlt, ergaenze ihn in der Import-Zeile."
        )

    # M-298d: Datei-Kontext als zusaetzlicher Abschnitt (on-demand).
    # Nur Dateien, die der Task betrifft — verhindert Token-Ballern.
    if "_file_context" in dir() and _file_context:
        _ctx_parts = []
        for _f, _c in _file_context.items():
            _ctx_parts.append(f"--- {_f} (letzte 50 Zeilen) ---\n{_c}")
        user_content += "\n\nAktueller Datei-Kontext:\n" + "\n\n".join(_ctx_parts)

    # GOLD: Klassischer Pfad nutzt _build_patches_fuer_datei.
    # Vorteile: voller Datei-Inhalt, relevanter Architect-Abschnitt,
    # Feedback, Reviewer-Bugs, Verify-Fehler, Reflection-History,
    # Import-Validierung.
    _arch_beschreibung = (
        _aktuelle_task.get("description", "")
        if isinstance(_aktuelle_task, dict) else ""
    )
    patches = _build_patches_fuer_datei(
        state, _zieldatei, _arch_beschreibung, api_key,
    )
    if not patches:
        # GOLD 2026-10-30: pruefen, ob der LLM-Pfad bereits das
        # auftrag_bereits_erfuellt-Flag gesetzt hat.
        if getattr(state, "auftrag_bereits_erfuellt", False):
            return True
        audit("builder_keine_patches_gold",
              {"zieldatei": _zieldatei}, pd, pn)
        return False

    # GOLD 2026-10-30: no_effect-Patches filtern (old == new).
    # Der Haupt-Pfad filtert schon, der Architect-Pfad bisher nicht.
    # Live 2026-10-30 20:46:55: builder_patch_no_effect +
    # builder_patches_erstellt + loop_patch_updated -> Patch ohne
    # Aenderung wurde angewendet.
    _effektiv: list = []
    for _p in patches:
        if not isinstance(_p, dict):
            continue
        if (_p.get("action") == "update"
                and _p.get("old_string") == _p.get("new_string")):
            audit("builder_patch_no_effect",
                  {"file": _p.get("file", "?"),
                   "grund": "old_eq_new"}, pd, pn)
            continue
        _effektiv.append(_p)
    if not _effektiv:
        # Alle Patches waren no_effect -> Auftrag ist bereits erfuellt.
        state.auftrag_bereits_erfuellt = True  # type: ignore[attr-defined]
        audit("auftrag_bereits_erfuellt",
              {"zieldatei": _zieldatei,
               "grund": "alle_patches_no_effect"}, pd, pn)
        return True
    patches = _effektiv

    # M-337: Jeder Patch MUSS die Zieldatei sein + die Aktion
    # respektieren. Der LLM darf NICHT frei entscheiden.
    for _p in patches:
        if not isinstance(_p, dict):
            continue
        _pfile = _p.get("file", "")
        if _pfile != _zieldatei:
            audit("builder_patch_invalid",
                  {"file": _pfile, "zieldatei": _zieldatei,
                   "grund": "falsche Datei"}, pd, pn)
            return False
        _paction = _p.get("action")
        if _current_action2 == "update" and _paction != "update":
            audit("builder_patch_invalid",
                  {"action": _paction, "expected": "update"}, pd, pn)
            return False
        if _current_action2 == "create" and _paction != "create":
            audit("builder_patch_invalid",
                  {"action": _paction, "expected": "create"}, pd, pn)
            return False

    # Patches in State schreiben (spaeter anwenden)
    # M-351: Patches mit identischem Inhalt (old == new) sind no_effect.
    _effective_patches = []
    for _p in patches:
        if not isinstance(_p, dict):
            continue
        if _p.get("action") == "update" and _p.get("old_string") == _p.get("new_string"):
            audit("builder_patch_no_effect",
                  {"file": _p.get("file", "?")}, pd, pn)
            continue
        _effective_patches.append(_p)
    if not _effective_patches:
        audit("builder_keine_wirksamen_patches", {}, pd, pn)
        return False
    state.patches = _effective_patches  # type: ignore[attr-defined]
    audit("builder_patches_erstellt", {"anzahl": len(_effective_patches)}, pd, pn)
    return True
