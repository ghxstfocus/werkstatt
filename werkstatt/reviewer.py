"""Reviewer-Agent (Phase 8, 2026-10-23).

Eigenstaendiger Reviewer. Bekommt Diff + Anforderung
+ Testergebnisse. Gibt strukturiertes Feedback zurueck.
Kein GO/NO_GO-Raten, sondern konkrete Bug-Funde.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from werkstatt.agent import ask_llm
from werkstatt.audit import audit
from werkstatt.render import _with_spinner
from werkstatt.skills import load_all_skills
from werkstatt.state import RunState


def extract_audit_bug_summary(bugs: list) -> list[dict]:
    """OP-114: Normalisiert eine Reviewer-Bug-Liste fuer Audit-Payloads.

    Liefert immer eine list[dict] mit genau den Keys 'severity' und
    'description'. Nicht-dict-Eintraege werden zu
    {'severity': '?', 'description': str(b)[:200]} — so geht kein Bug
    im Audit verloren. Wirft keine Exception (defensiv auf bugs or []).
    """
    _out: list[dict] = []
    for _b in (bugs or []):
        if isinstance(_b, dict):
            _sev = str(_b.get("severity", "?"))[:40]
            _desc = str(
                _b.get("description") or _b.get("beschreibung") or ""
            )[:200]
            _out.append({"severity": _sev, "description": _desc})
        else:
            _out.append({"severity": "?", "description": str(_b)[:200]})
    return _out


def _reviewer_history_block(state: RunState) -> str:
    """K40: Formatiert die Historie der vorherigen Reviewer-Runden.

    Verhindert, dass der Reviewer behobene Bugs erneut meldet.
    Max 3 Runden -- aeltere sind meist schon repariert.
    """
    _history = state.reviewer_bugs_history or []
    if not _history:
        return ""
    _lines = ["\n## REVIEWER-HISTORIE (vorherige Runden):\n"]
    for i, bugs in enumerate(_history[-3:], 1):
        _lines.append(f"\n### Runde {i} ({len(bugs)} Bugs):\n")
        for b in bugs:
            if not isinstance(b, dict):
                continue
            _sev = b.get("severity", "?")
            _file = b.get("file", "?")
            _desc = (b.get("description") or b.get("beschreibung") or "")[:200]
            _lines.append(f"- [{_sev}] {_file} - {_desc}\n")
    _lines.append(
        "\nPruefe, ob diese Bugs behoben sind. Melde NUR noch "
        "offene oder NEUE Bugs. Wenn ein Bug behoben ist: NICHT "
        "erneut melden.\n"
    )
    return "".join(_lines)

REVIEWER_SYSTEM = """Du bist ein elite Code-Reviewer.
Du bekommst einen Git-Diff und die Anforderung.

## Was du PRUEFST

Pruefe NUR auf Korrektheit:
- Bricht der Code (Syntax, TypeError, falsche Signatur, fehlende Imports)?
- Verletzt der Code die TASK-BESCHREIBUNG (explizite Anforderung nicht erfuellt)?

Ignoriere Stil, Formatierung, Kleinigkeiten, "nice to have".

## GOLD: Datei-Kontext

Du bekommst im User-Content den vollstaendigen aktuellen
Datei-Inhalt (Abschnitt "VOLLE ZIELDATEI"). Pruefe
JEDEN Patch gegen diesen Inhalt:
- Existieren alle importierten Symbole im Modul?
- Bleiben bestehende Sektionen/Funktionen erhalten?
- Wird eine Funktion erweitert (nicht ueberschrieben)?

## GOLD: Diff-Pruefung (STRIKT)

Pruefe JEDE `-`-Zeile im Diff. Was wurde ENTFERNT?

Wenn eine `-`-Zeile eine BESTEHENDE Funktionsaufruf-Zeile ist
(z.B. `updateFast(data)`, `updateSlow(data)`, `renderDevices(...)`,
`body["devices"] = ...`, `renderAlerts(...)`) und die Task-Beschreibung
verlangt NICHT explizit deren Entfernung:
  -> reviewer_bug mit severity="high":
     "Bestehender Aufruf X entfernt, nicht in Task gefordert."

Wenn eine `-`-Zeile eine bestehende Zuweisung/Funktion entfernt:
  -> reviewer_bug mit severity="high":
     "Bestehende Zuweisung/Funktion X entfernt."

NUR wenn die Task explizit sagt "entferne X", ist eine `-`-Zeile ok.

Vergleiche den Diff mit der "VOLLEN ZIELDATEI". Wenn die Datei eine
Funktion X enthaelt, die der Diff entfernt haben muesste (aber die
Datei hat sie noch) -> Patch inkonsistent -> HIGH.

Wenn der Diff eine bestehende Zeile entfernt (z.B. `updateFast(data);`),
aber die Datei diese Zeile NICHT mehr enthaelt (weil der Patch sie
entfernt hat) -> HIGH, weil bestehende Funktionalitaet verloren.

## RENAME-AUSNAHME (2026-11-05, OP-164)

Wenn die TASK-BESCHREIBUNG "umbenennen", "umbenannt", "umbenennung",
"rename", "renamed" oder "ersetzen durch" enthaelt, ist eine
`-`-Zeile mit dem alten Namen KEIN HIGH-Bug, sofern im SELBEN
Diff-Hunk (`@@ ... @@`-Block) eine `+`-Zeile mit einem anderen
Identifier steht. Alte Zeile weg + neue Zeile da = Rename, kein
Entfernen.

Nur wenn im selben Hunk KEINE `+`-Zeile mit einem anderen
Identifier steht: HIGH "Rename unvollstaendig: <alt> entfernt,
<neu> fehlt im selben Hunk."

## Severity-Level (WICHTIG)

- "high": Code BRICHT zur Laufzeit, ODER explizite Task-Anforderung
  verletzt (z.B. "nur sqlite3.Error fangen" -> Code faengt auch
  Exception -> HIGH). HIGH blockiert den Task.
- "medium": Fehlender Randfall, unvollstaendige Doku. Blockiert NICHT.
- "low": Stil, Tippfehler, Vorschlag. Blockiert NICHT.

## approved-Regel (STRIKT)

- approved=true, wenn KEIN Bug mit severity="high".
- approved=false, NUR wenn mindestens ein "high"-Bug.
- Medium/low-Bugs werden in "bugs" gemeldet, aber approved bleibt true.
- Wenn du unsicher bist, ob etwas "high" ist: setze "medium".
  Ein falscher high-Bug kostet 5 Reflection-Runden.

M-380: PROGRESS.md ist NICHT Teil deines Reviews. Bewerte NUR den
Builder-Patch.

Antworte NUR mit validem JSON:
{
  "approved": true|false,
  "bugs": [{"file": "...", "line": 0, "description": "...", "severity": "high|medium|low"}],
  "summary": "..."
}


## DATEI-CHECK (HIGH-Bug, verhindert "fehlt im Diff"-Fehltreffer)
- Wenn eine Task-Anforderung im Diff NICHT sichtbar ist (z.B. "Slice
  fehlt"), pruefe im Block `AKTUELLER DATEI-INHALT`, ob die
  Anforderung dort schon erfuellt ist.
- Wenn die Anforderung im Datei-Inhalt erfuellt ist (z.B.
  `return entries[-_RECENT_CHANGES_LIMIT:]` oder `entries[-10:]`):
  KEIN Bug. Der Diff aendert sie nur nicht, weil sie schon da ist.
- Nur wenn die Anforderung WEDER im Diff noch im Datei-Inhalt
  erfuellt ist: HIGH-Bug.
- Belege im `description`-Feld: "Anforderung X fehlt im Diff und
  im Datei-Inhalt (Zeilen 1-N geprueft)".


## AUFTRAG-TREUE-CHECK (HIGH-Bug, FIX 2026-10-31)
Der User-Auftrag enthaelt oft NEGATIVE Anweisungen ("nicht X",
"kein Y", "behalte Z", "erhalte W"). Pruefe JEDE solche Anweisung:
- Suche im GESAMTAUFGABE-Text nach "nicht", "kein", "keine",
  "behalte", "erhalte", "nur", "ausschliesslich", "vermeide".
- Pruefe fuer JEDE gefundene Anweisung, ob der Diff sie verletzt.
- Beispiel: Aufgabe sagt "nicht umnummerieren", Diff nummeriert
  Punkte um (2->1, 3->2): HIGH-Bug "Auftrag-Treue verletzt:
  Umnummerierung, obwohl Auftrag 'nicht umnummerieren' fordert".
- Beispiel: Aufgabe sagt "nur docs/STATUS.md", Diff aendert auch
  eine .py-Datei: HIGH-Bug "Auftrag-Treue: zusaetzliche Datei".
- Beispiel: Aufgabe sagt "behalte Abschnitt X", Diff entfernt
  Zeilen aus X: HIGH-Bug "Auftrag-Treue: Abschnitt X entfernt".
- Wenn keine negativen Anweisungen im Auftrag: kein Bug.
- Belege im `description`-Feld: "Auftrag sagt 'nicht umnummerieren',
  Diff nummeriert 2->1, 3->2, 4->3".


## DEAD-CODE-CHECK (HIGH, 2026-11-07, OP-181)

Pruefe, ob der Diff eine NEUE Datei anlegt, die niemand produktiv
nutzt. Eine neue Datei erkennst du am Diff-Header `new file mode`
oder an der Kombination `--- /dev/null` / `+++ b/<pfad>`.

Regel 1: Wenn der Diff eine neue .py-Datei anlegt und der
Modul-Stem (Dateiname ohne `.py`, letztes Pfad-Segment) weder in
`werkstatt/` noch in `tools/` (ausser `tests/`) referenziert wird,
ist das ein HIGH-Bug mit der Description
"Neues Modul <stem> wird nur von Tests importiert — Dead-Code-Verdacht."

Regel 2: Tests zaehlen NICHT als produktive Aufrufer. Ein Import
in `tests/test_*.py` oder `tests/*_test.py` ist KEIN Beleg fuer
Nutzung.

Regel 3: Ausnahme ist explizit deklariert: eine neue Datei unter
`tools/`, die ein Standalone-CLI mit `if __name__ == "__main__":`-Block
ist, darf nur von Tests gerufen werden — dann kein Bug.

Dieser Check ist Defense-in-Depth: der LLM-Reviewer soll das pruefen,
aber der harte Befund kommt ohnehin aus dem deterministischen
Pre-Check. Die Architect-PFLICHT (`AUFRUFER-PFLICHT` im
`ARCHITECT_SYSTEM`) verlangt, dass neue Module einen produktiven
Aufrufer haben.

"""


def _get_git_diff(
    project_dir: str | Path | None = None,
    task_files: list[str] | None = None,
) -> str:
    """Holt den aktuellen Git-Diff im Zielprojekt.

    M-314: umfasst jetzt auch UNTRACKED-Dateien (git ls-files
    --others). Vorher war der Reviewer blind fuer neue Dateien,
    die der Builder mit `create` angelegt hat.

    K4: Wenn task_files uebergeben, nur diese Pfade diffen — sonst
    sieht der Reviewer kumulative Aenderungen frueherer Tasks.
    """
    if project_dir is None:
        audit("reviewer_diff_fehler",
              {"fehler": "project_dir ist None"},
              Path("."), "?")
        return ""
    try:
        pd = Path(project_dir)
        pathspec = list(task_files) if task_files else ["."]
        res = subprocess.run(
            ["git", "diff", "HEAD", "--", *pathspec, ":!PROGRESS.md"],
            cwd=str(pd), capture_output=True, text=True, timeout=30, check=False
        )
        # K23a: fail-closed. Git-Fehler darf NICHT als "kein Diff" enden.
        # getattr defensiv -- aeltere Mocks setzen stderr nicht.
        _rc = getattr(res, "returncode", 0) or 0
        _stderr = getattr(res, "stderr", "") or ""
        _stderr_l = _stderr.lower()
        if _rc != 0 or ("dubious" in _stderr_l or "dubiose" in _stderr_l):
            raise RuntimeError(
                f"git diff fehlgeschlagen (rc={_rc}): {_stderr[:300]}"
            )
        parts = [res.stdout[:500000]] if res.stdout else []

        # M-314: untracked-Dateien als "Neue Datei"-Block anhaengen.
        untracked = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            cwd=str(pd), capture_output=True, text=True, timeout=30, check=False
        )
        if getattr(untracked, "stdout", ""):
            for rel in untracked.stdout.splitlines():
                if not rel or rel.startswith("."):
                    continue
                # K4b: nur untracked-Dateien der aktuellen Task.
                if task_files and not any(
                    rel == tf or rel.startswith(tf.rstrip("/") + "/")
                    for tf in task_files
                ):
                    continue
                f = pd / rel
                if not f.is_file():
                    continue
                try:
                    content = f.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                block = ["--- /dev/null", f"+++ b/{rel}", "@@ NEUE DATEI @@"]
                for line in content.splitlines():
                    block.append(f"+{line}")
                parts.append("\n".join(block) + "\n")

        return "\n".join(parts)[:20000]
    except (RuntimeError, subprocess.SubprocessError,
            OSError, TimeoutError) as _exc:
        # K23a: fail-closed -- Git-Fehler propagieren, nicht still leer.
        # K23a: RuntimeError aus dem returncode-Check wird NICHT
        # hier gefangen, sondern nach oben gereicht.
        if isinstance(_exc, RuntimeError):
            raise
        raise RuntimeError(f"git diff fehlgeschlagen: {_exc}") from _exc


def _pruefe_neue_module_genutzt(
    project_dir: str | Path | None, diff: str,
) -> list[dict]:
    """Dead-Code-Check: neue .py-Module, die nur von Tests importiert werden.

    Parst den Diff zeilenweise. Neue .py-Dateien werden erkannt an
    `--- /dev/null` oder `new file mode` im Datei-Block, gefolgt von
    einer `+++ b/...py`-Zeile. Fuer jede neue Datei wird geprueft, ob
    der Stem im Produktivpfad (werkstatt/, tools/) referenziert wird.
    Wenn nur Tests den Stem referenzieren: HIGH-Bug.
    Fail-closed: bei Parse-Fehlern leere Liste + audit-Event.
    """
    if not project_dir or not diff:
        return []
    _project_name = Path(project_dir).name if project_dir else ""
    try:
        _neue: list[str] = []
        _im_neuen_file = False
        for _line in diff.splitlines():
            if _line.startswith("diff --git "):
                _im_neuen_file = False
                continue
            if _line.startswith(("new file mode", "--- /dev/null")):
                _im_neuen_file = True
                continue
            if _im_neuen_file and _line.startswith("+++ b/"):
                _pfad = _line[len("+++ b/"):].strip()
                if _pfad.endswith(".py"):
                    _neue.append(_pfad)
                _im_neuen_file = False

        _basis = Path(project_dir)
        _ergebnis: list[dict] = []
        for _pfad in _neue:
            if _pfad.startswith("tests/") or "/tests/" in _pfad:
                continue
            _stem = Path(_pfad).stem
            _pat = re.compile(r"\b" + re.escape(_stem) + r"\b")

            _produktiv = False
            for _root in ("werkstatt", "tools"):
                _dir = _basis / _root
                if not _dir.is_dir():
                    continue
                for _f in _dir.rglob("*.py"):
                    try:
                        _rel = _f.relative_to(_basis).as_posix()
                    except ValueError:
                        _rel = str(_f)
                    if _rel == _pfad:
                        continue
                    if _rel.startswith("tests/") or "/tests/" in _rel:
                        continue
                    try:
                        _txt = _f.read_text(
                            encoding="utf-8", errors="replace"
                        )
                    except (OSError, UnicodeDecodeError):
                        continue
                    if _pat.search(_txt):
                        _produktiv = True
                        break
                if _produktiv:
                    break
            if _produktiv:
                continue

            _nur_tests = False
            _tdir = _basis / "tests"
            if _tdir.is_dir():
                for _f in _tdir.rglob("*.py"):
                    try:
                        _txt = _f.read_text(
                            encoding="utf-8", errors="replace"
                        )
                    except (OSError, UnicodeDecodeError):
                        continue
                    if _pat.search(_txt):
                        _nur_tests = True
                        break
            if _nur_tests:
                _ergebnis.append({
                    "severity": "high",
                    "description": (
                        f"Neues Modul {_stem} wird nur von Tests "
                        f"importiert — Dead-Code-Verdacht."
                    ),
                    "file": _pfad,
                    "quelle": "deterministic_dead_code",
                })
        return _ergebnis
    except Exception as _e:  # noqa: BLE001
        audit(
            "reviewer_dead_code_parse_fehler",
            {"fehler": str(_e)[:200], "diff_len": len(diff)},
            Path(project_dir), _project_name,
        )
        return []


def _reviewer_system(state=None, task_files=None) -> str:
    """M-374: review-work IMMER laden.

    M-Skills-Reviewer: Metadata-Block (Level 1) + Glob-Aktivierung
    (Level 2, Cursor-Stil) basierend auf task_files.
    """
    skills = load_all_skills()
    parts = []
    _akt_task = getattr(state, "aktuelle_task", None) if state is not None else None
    if isinstance(_akt_task, dict) and _akt_task.get("action") == "verify":
        parts.append(
            "## VERIFY-TASK (Diff-Erwartung: leer)\n"
            "Diese Task aendert KEINE Datei. Der Diff MUSS leer sein. "
            "Melde KEINEN Bug der Form 'Diff fehlt Datei X' oder "
            "'Task verlangt Funktion Y, Diff hat sie nicht' — das sind "
            "bei Verify-Tasks korrekte Beobachtungen, keine Bugs."
        )
    parts.append(REVIEWER_SYSTEM)
    _akt_names: list[str] = []

    from werkstatt.rollen import ROLLEN
    _tf = list(task_files) if task_files else None
    _geladen = ROLLEN["reviewer"].lade_skills(skills, task_files=_tf)
    _static_names = set(ROLLEN["reviewer"].skills)

    # Reihenfolge wie vor Migration: statische Bodies -> metadata -> dynamische.
    for _s in _geladen:
        if _s.get("name") in _static_names:
            _body = _s.get("body") or ""
            if _body:
                parts.append(
                    f"## Skill: {_s.get('name', '?')}\n" + _body
                )
                _akt_names.append(_s.get("name", "?"))

    # M-Skills-Reviewer: Metadata-Block (Level 1)
    try:
        from werkstatt.skills import skills_metadata_block
        _meta = skills_metadata_block(skills)
        if _meta:
            parts.append(_meta.rstrip())
    except Exception:
        pass

    # Dynamische Bodies (task_files-basiert)
    for _s in _geladen:
        if _s.get("name") not in _static_names:
            _body = _s.get("body") or ""
            if _body:
                parts.append(
                    f"## Skill: {_s.get('name', '?')}\n" + _body
                )
                _akt_names.append(_s.get("name", "?"))

    # M-Skills-Dedup: zentrale Merk-Funktion (dedup + audit)
    if _akt_names:
        try:
            from werkstatt.skills import _merke_geladene_skills
            _merke_geladene_skills(state, _akt_names, rolle="reviewer")
        except Exception:
            pass

    return "\n\n".join(parts)


def _verifiziere_reviewer_bugs(
    bugs: list, project_dir: Path, project_name: str,
) -> list:
    """Fix AX 2026-10-31: deterministischer Vorfilter gegen Reviewer-
    Halluzinationen.

    Konservativ: nur widerlegen, wenn der Code den behaupteten Mangel
    zweifelsfrei widerlegt. Unpruefbares bleibt unangetastet (kein
    falsch-negativ, das echte Bugs unterdrueckt).

    Heuristiken:
      1. Bug nennt "X() fehlt" / "X() fehlt in" / "X() nicht vorhanden":
         ast.parse(file) -> existiert X als FunctionDef/AsyncFunctionDef/
         ClassDef/AnnAssign irgendwo? -> Bug widerlegt.
      2. Bug nennt "Datei <path> fehlt" / "existiert nicht":
         Path(project_dir/path).exists() True -> Bug widerlegt.
      3. Sonst: Bug bleibt.

    Widerlegte Bugs werden mit audit("reviewer_bug_widerlegt") geloggt.
    """
    import ast as _ast
    import re as _re

    # Fix 2026-10-31: [^)]* statt \s* — auch "is_available(timeout)"
    # muss matchen. Vorher griff nur "method()" ohne Argumente.
    _pat_call_fehl = _re.compile(
        r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\([^)]*\)[^.]{0,80}?"
        r"(fehlt|nicht\s+vorhanden|existiert\s+nicht)",
        _re.IGNORECASE,
    )
    _pat_datei_fehlt = _re.compile(
        r"Datei\s+[`\"]?(\S+?)[`\"]?\s+"
        r"(fehlt|existiert\s+nicht)",
        _re.IGNORECASE,
    )

    out: list = []
    for b in bugs:
        if not isinstance(b, dict):
            out.append(b)
            continue
        _f = b.get("file") or ""
        _desc = b.get("description") or b.get("beschreibung") or ""
        if not _f or not _desc:
            out.append(b)
            continue

        # Heuristik 1: "X() fehlt"
        _m1 = _pat_call_fehl.search(_desc)
        if _m1 and _f.endswith(".py"):
            _target = Path(project_dir) / _f
            if _target.is_file():
                try:
                    _tree = _ast.parse(
                        _target.read_text(encoding="utf-8", errors="replace")
                    )
                except SyntaxError:
                    _tree = None
                if _tree is not None:
                    _sym = _m1.group(1)
                    _found = False
                    for _node in _ast.walk(_tree):
                        if isinstance(
                            _node, (_ast.FunctionDef, _ast.AsyncFunctionDef,
                                    _ast.ClassDef),
                        ) and _node.name == _sym:
                            _found = True
                            break
                        if isinstance(_node, _ast.AnnAssign) and \
                                isinstance(_node.target, _ast.Name) and \
                                _node.target.id == _sym:
                            _found = True
                            break
                    if _found:
                        audit("reviewer_bug_widerlegt",
                              {"grund": "symbol_existiert",
                               "symbol": _sym, "file": _f,
                               "desc": _desc[:120]},
                              project_dir, project_name)
                        continue

        # Heuristik 2: "Datei X fehlt"
        _m2 = _pat_datei_fehlt.search(_desc)
        if _m2:
            _path = _m2.group(1).strip("`\"'.,;:")
            _target = Path(project_dir) / _path
            if _target.exists():
                audit("reviewer_bug_widerlegt",
                      {"grund": "datei_existiert",
                       "pfad": _path, "file": _f,
                       "desc": _desc[:120]},
                      project_dir, project_name)
                continue

        out.append(b)
    return out


def run_phase_end_review(state: RunState) -> bool:
    """K23c: Phase-End-Review vor Human-Gate.

    Prueft ALLE uncommitted Aenderungen der Phase zusammen gegen:
    - aufgabe
    - state.tasks (Namen, Actions)
    - state.akzeptanzkriterien
    - ruff-Ergebnis + Diff

    Fail-closed bei high/medium-bugs. Bei LLM-Fehler: fail-closed.
    """
    pd = state.project_dir
    pn = state.project_name
    api_key = state.api_key
    if not api_key:
        audit("reviewer_phase_kein_key", {}, pd, pn)
        return False

    # K25: Phase-Review-Scope = Task-Dateien, nicht alle uncommitted Files.
    # Sonst sieht Reviewer alte RERUN-Reste (core/alerts/) und meldet
    # Bugs, die nicht zur Phase gehoeren.
    _phase_files: list[str] = []
    for _t in (state.tasks or []):
        if not isinstance(_t, dict):
            continue
        for _f in (_t.get("task_files") or []):
            if isinstance(_f, str) and _f not in _phase_files:
                _phase_files.append(_f)
    if not _phase_files:
        audit("reviewer_phase_keine_task_files", {}, pd, pn)
        return False

    try:
        diff = _get_git_diff(pd, task_files=_phase_files)
    except RuntimeError as _exc:
        audit("reviewer_phase_diff_fehler",
              {"fehler": str(_exc)[:300]}, pd, pn)
        return False

    if not diff:
        audit("reviewer_phase_kein_diff", {}, pd, pn)
        return False  # fail-closed: Phase ohne Diff = Bug

    tasks_summary = []
    for _t in (state.tasks or []):
        if isinstance(_t, dict):
            tasks_summary.append({
                "id": _t.get("id"), "name": _t.get("name"),
                "files": _t.get("task_files"),
                "status": _t.get("status"),
            })
    aufgabe = state.aufgabe
    akz = state.akzeptanzkriterien or []

    import json as _json
    user = (
        f"## AUFGABE DER PHASE:\n{aufgabe}\n\n"
        f"## TASKS ({len(tasks_summary)}):\n"
        f"{_json.dumps(tasks_summary, ensure_ascii=False, indent=2)}\n\n"
        f"## AKZEPTANZKRITERIEN ({len(akz)}):\n"
        f"{_json.dumps(list(akz), ensure_ascii=False, indent=2)}\n\n"
        f"## GESAMT-DIFF (alle Task-Aenderungen zusammen):\n"
        f"```diff\n{diff}\n```\n\n"
    )
    # GOLD 2026-10-30: Datei-Inhalt fuer jede Task-Datei anhaengen.
    # Vorher hatte der Phase-Review NUR den Diff — der Reviewer
    # konnte nicht pruefen, ob eine Anforderung schon im Datei-Inhalt
    # erfuellt ist (DATEI-CHECK/SYMBOL-CHECK griffen ins Leere).
    # Live-Beleg 2026-10-30 20:52:24: Reviewer meldete "Anforderung
    # weder im Diff noch im Datei-Inhalt", obwohl die Sortierung
    # in _section_timeline_entries schon da war.
    for _tf in _phase_files[:3]:
        _fp = Path(pd) / _tf
        if not _fp.is_file():
            continue
        try:
            _content = _fp.read_text(encoding="utf-8")[:30000]
        except (OSError, UnicodeDecodeError):
            continue
        user += (
            f"\n\n--- VOLLE ZIELDATEI: {_tf} ---\n"
            f"{_content}\n"
            f"--- ENDE ---"
        )
    user += (
        # K40: Historie vorheriger Reviews.
        _reviewer_history_block(state)
        + "Pruefe den Code zusammenhängend. Achte auf:\n"
        "- API-Kompatibilitaet (Signaturen unveraendert?)\n"
        "- Cross-File-Referenzen (Importe, Symbole)\n"
        "- Sicherheit (Permissions, CSRF, Input-Validierung)\n"
        "- Erfuellung der Akzeptanzkriterien\n"
        "- Semantische Kohärenz zwischen den Tasks\n\n"
        "Antworte NUR mit JSON: "
        '{"approved": true|false, "bugs": ['
        '{"severity": "high|medium|low", '
        '"file": "path/to/file.py", '
        '"description": "..."}]}\n\n'
        "Jeder Bug MUSS ein 'file'-Feld haben (relativer Pfad, "
        "exakt wie im Diff). Wenn du die Datei nicht kennst, "
        "verwende 'unknown'."
    )

    try:
        reply = _with_spinner(
            "Phase-Review",
            lambda: ask_llm(
                api_key, _reviewer_system(state, _phase_files), user,
                model="deepseek-chat", temperature=0.2, max_tokens=4000,
                redact=False,  # OP-062a: Code-Pruefung braucht Rohdaten
                aufgabe="reviewer",
            ),
        )
    except Exception as _exc:
        audit("reviewer_phase_call_failed",
              {"fehler": str(_exc)[:300]}, pd, pn)
        return False

    if not reply.ok:
        audit("reviewer_phase_call_failed",
              {"fehler": reply.error[:200]}, pd, pn)
        return False

    _raw = (reply.content or "").strip()
    _start = _raw.find("{")
    _end = _raw.rfind("}") + 1
    if _start < 0 or _end <= _start:
        audit("reviewer_phase_json_fehler",
              {"raw": _raw[:200]}, pd, pn)
        return False
    try:
        _parsed = _json.loads(_raw[_start:_end])
    except _json.JSONDecodeError:
        audit("reviewer_phase_json_fehler",
              {"raw": _raw[:200]}, pd, pn)
        return False

    _approved = bool(_parsed.get("approved"))
    _bugs = _parsed.get("bugs") or []
    if not isinstance(_bugs, list):
        _bugs = []
    # Fix AX 2026-10-31: deterministischer Vorfilter.
    _bugs = _verifiziere_reviewer_bugs(_bugs, Path(pd), pn)
    _high = [b for b in _bugs
             if isinstance(b, dict) and b.get("severity") == "high"]
    _medium = [b for b in _bugs
               if isinstance(b, dict) and b.get("severity") == "medium"]

    if not _approved or _high:
        audit("reviewer_phase_rejected",
              {"approved": _approved,
               "bugs_high": len(_high),
               "bugs_medium": len(_medium),
               "bugs": _bugs[:5]}, pd, pn)
        state.reviewer_bugs = _bugs
        return False

    audit("reviewer_phase_approved",
          {"bugs_medium": len(_medium),
           "bugs_low": len(_bugs) - len(_high) - len(_medium)},
          pd, pn)
    # OP-062c: bei Approval alte Bugs leeren, sonst zeigt das
    # Human-Gate HIGH-Bugs, die laengst behoben sind.
    state.reviewer_bugs = []
    return True

_RENAME_MARKER = (
    "umbenennen", "umbenannt", "umbenennung",
    "rename", "renamed",
    "ersetzen durch", "ersetzt durch",
)


def _filter_rename_false_positives(
    bugs: list, diff: str, task_desc: str,
) -> list:
    """OP-164: Rename-Aufgabe -> 'X entfernt'-HIGH ist kein Bug,
    wenn im selben Hunk eine +-Zeile mit anderem Identifier steht.
    """
    import re as _re

    if not isinstance(bugs, list) or not isinstance(diff, str):
        return bugs
    _desc = (task_desc or "").lower()
    if not any(_m in _desc for _m in _RENAME_MARKER):
        return bugs
    if "@@" not in diff:
        return bugs

    _pattern = _re.compile(
        r"(?:Bestehende[rs]?\s+(?:Zuweisung|Funktion)|"
        r"bestehende[rs]?\s+(?:Zuweisung|Funktion))\s+"
        r"[\"'`]?(\w+)[\"'`]?\s+entfernt",
        _re.IGNORECASE,
    )
    _hunks = _re.split(r"(?m)^@@ ", diff)
    out = []
    for bug in bugs:
        if not isinstance(bug, dict):
            out.append(bug)
            continue
        if bug.get("severity") != "high":
            out.append(bug)
            continue
        _d = bug.get("description", "") or ""
        _m = _pattern.search(_d)
        if not _m:
            out.append(bug)
            continue
        _name = _m.group(1)
        _name_re = _re.compile(r"\b" + _re.escape(_name) + r"\b")
        _found_pair = False
        for _h in _hunks[1:]:
            _lines = _h.split("\n")
            _has_minus = any(
                ln.startswith("-") and _name_re.search(ln)
                for ln in _lines
            )
            if not _has_minus:
                continue
            _has_plus = any(
                ln.startswith("+") and not ln.startswith("+++")
                and _re.search(r"[A-Za-z_]\w+", ln)
                and not _name_re.search(ln)
                for ln in _lines
            )
            if _has_plus:
                _found_pair = True
                break
        if _found_pair:
            _bug2 = dict(bug)
            _bug2["severity"] = "medium"
            _bug2["description"] = (
                _d + " [OP-164: Rename erkannt, +-Zeile im Hunk]"
            )
            out.append(_bug2)
        else:
            out.append(bug)
    return out


_WERT_KIPP_MARKER = (
    "wert geändert", "wert geaendert", "wert kippt",
    "semantik kippt", "semantik umgekehrt",
    "true->false", "false->true",
    "true -> false", "false -> true",
    "true nach false", "false nach true",
)

_TYPE_IGNORE_MARKER = (
    "type: ignore", "type:ignore", "type-ignore", "type ignore",
)

_TYP_IGNORE_STOP = frozenset({
    "ignore", "type", "feld", "hinzugef", "hinzugefuegt", "hinzugefügt",
    "erwaehnt", "erwähnt", "nicht", "attribute", "attr", "defined",
    "bool", "true", "false", "none", "zusaetzlich", "zusaetzliche",
})


def _filter_auftrag_treue_false_positives(
    bugs: list,
    diff: str,
    task_desc: str,
    task_files: list[str] | None = None,
    action: str | None = None,
) -> list:
    """OP-164b: Auftrag-Treue-Filter fuer Rename-Aufgaben."""
    import re as _re

    if not isinstance(bugs, list) or not isinstance(diff, str):
        return bugs
    if (action or "").lower() == "verify":
        _verify_patterns = (
            "diff fehlt",
            "diff hat sie nicht",
            "diff enthält nicht",
            "diff enthaelt nicht",
            "neues modul nicht genutzt",
            "neues modul wurde nicht genutzt",
        )
        _bugs_verify: list = []
        for _b in bugs:
            if isinstance(_b, dict):
                _bd = (
                    _b.get("description")
                    or _b.get("beschreibung")
                    or ""
                ).lower()
                if any(_p in _bd for _p in _verify_patterns):
                    continue
            _bugs_verify.append(_b)
        bugs = _bugs_verify
    _desc = (task_desc or "").lower()
    if not any(_m in _desc for _m in _RENAME_MARKER):
        return bugs
    if "@@" not in diff:
        return bugs

    _tf_str = " ".join(list(task_files or [])).lower()

    _hunks = _re.split(r"(?m)^@@ ", diff)
    _wert_pairs: list = []
    for _h in _hunks[1:]:
        _minus: dict = {}
        _plus: dict = {}
        for _ln in _h.split("\n"):
            _m = _re.match(
                r"^-\s*(?:state\.)?([a-z_][a-z0-9_]*)\s*=\s*(True|False)\b",
                _ln,
            )
            if _m:
                _minus[_m.group(1)] = _m.group(2)
                continue
            _m = _re.match(
                r"^\+\s*(?:state\.)?([a-z_][a-z0-9_]*(?:_bestaetigt|_neu))"
                r"\s*=\s*(True|False)\b",
                _ln,
            )
            if _m:
                _plus[_m.group(1)] = _m.group(2)
        for _alt_name, _alt_wert in _minus.items():
            for _suffix in ("_bestaetigt", "_neu"):
                _neu_name = _alt_name + _suffix
                if _plus.get(_neu_name) == _alt_wert:
                    _wert_pairs.append(
                        (_alt_name, _alt_wert, _neu_name, _alt_wert)
                    )

    _typ_ignore_identifiers: set = set()
    for _ln in diff.split("\n"):
        if not _ln.startswith("+") or _ln.startswith("+++"):
            continue
        if not any(_m in _ln.lower() for _m in _TYPE_IGNORE_MARKER):
            continue
        for _m in _re.finditer(r"[a-z_][a-z0-9_]{4,}", _ln):
            _id = _m.group(0)
            if _id in _TYP_IGNORE_STOP:
                continue
            _typ_ignore_identifiers.add(_id)

    out = []
    for bug in bugs:
        if not isinstance(bug, dict):
            out.append(bug)
            continue
        if bug.get("severity") != "high":
            out.append(bug)
            continue
        _d = bug.get("description", "") or ""
        _d_lower = _d.lower()

        _ist_wert_kipp = any(_m in _d_lower for _m in _WERT_KIPP_MARKER)
        if _ist_wert_kipp and _wert_pairs:
            _matched = False
            for _alt_name, _alt_wert, _neu_name, _neu_wert in _wert_pairs:
                if _alt_name in _d:
                    _matched = True
                    break
            if _matched:
                _bug2 = dict(bug)
                _bug2["severity"] = "medium"
                _bug2["description"] = (
                    _d + " [OP-164b: Wert-Gleichheit im Rename-Hunk]"
                )
                out.append(_bug2)
                continue

        _ist_typ_ignore = any(_m in _d_lower for _m in _TYPE_IGNORE_MARKER)
        if _ist_typ_ignore and _typ_ignore_identifiers:
            _fremdes_feld = None
            for _id in sorted(_typ_ignore_identifiers):
                if _id in _desc:
                    continue
                if _id in _tf_str:
                    continue
                if _id in _d:
                    _fremdes_feld = _id
                    break
            if _fremdes_feld:
                _bug2 = dict(bug)
                _bug2["severity"] = "medium"
                _bug2["description"] = (
                    _d + " [OP-164b: Fremdfeld-type-ignore, nicht in Task]"
                )
                out.append(_bug2)
                continue

        out.append(bug)
    return out


def run_reviewer(state: RunState) -> bool:
    """Prueft den Code. Gibt True zurueck, wenn approved."""
    pd = state.project_dir
    pn = state.project_name
    api_key = state.api_key

    if not api_key:
        audit("reviewer_kein_key", {}, pd, pn)
        return False

    from werkstatt.paths import werkstatt_home as _wh
    pd = getattr(state, "project_dir", None) or _wh()
    # K4: task_files aus aktuelle_task — Reviewer sieht nur
    # den Diff der aktuellen Task, nicht kumulativ.
    _akt_task_early = getattr(state, "aktuelle_task", None)
    _tf_early = None
    if isinstance(_akt_task_early, dict) and _akt_task_early.get("task_files"):
        _tf_early = list(_akt_task_early["task_files"])
    # K23a: _get_git_diff kann RuntimeError werfen (Git-Fehler).
    try:
        diff = _get_git_diff(pd, task_files=_tf_early)
    except RuntimeError as _exc:
        audit("reviewer_diff_fehler",
              {"fehler": str(_exc)[:300]}, pd, pn)
        return False  # fail-closed

    # K23b: fail-closed. Leerer Diff MIT vorhandenen Patches = Bug.
    # Leerer Diff OHNE Patches = legitim NUR bei action="read".
    # FIX 2026-10-31: update-Task + task_files + leerer Diff
    # ist Fake-Done. Fail-closed.
    _patches = state.patches or []
    if not diff:
        if _patches:
            audit("reviewer_kein_diff_aber_patches",
                  {"patches": len(_patches),
                   "task_files": _tf_early or []}, pd, pn)
            return False  # fail-closed: Patch da, aber Diff leer = Bug
        _akt_action = ""
        if isinstance(_akt_task_early, dict):
            _akt_action = _akt_task_early.get("action", "")
        if _akt_action == "update" and _tf_early:
            audit("reviewer_kein_diff_update_task",
                  {"task_files": _tf_early}, pd, pn)
            return False  # fail-closed: update-Task ohne Diff = Fake-Done
        audit("reviewer_kein_diff_kein_patch", {}, pd, pn)
        return True  # Nichts zu reviewen (read-only / kein task_files)

    # FIX Q 2026-10-31: Deterministischer Vollstaendigkeits-Check
    # fuer create-Tasks mit .md-Dateien. Live-Beleg 2026-10-31 08:07:
    # Datei mit 3/8 Abschnitten, Reviewer hat approved.
    _akt_early = getattr(state, "aktuelle_task", None)
    if isinstance(_akt_early, dict):
        _tf_q = _akt_early.get("task_files") or []
        _md_q = [f for f in _tf_q if isinstance(f, str) and f.endswith(".md")]
        if _md_q and _akt_early.get("action") == "create":
            # FIX Q v2 2026-10-31: Schlagwort-Check statt Abschnitt-
            # Anzahl. Der alte Parser zaehlte "ChatService.propose_action
            # (principal, action, reason)" als 3 Abschnitte.
            # Neue Regel: pruefe, ob die zentralen Konzept-Schlagworte
            # aus der Aufgabe in der Datei vorkommen.
            _aufgabe_q = state.aufgabe or ""
            _md_pfad_q = Path(pd) / _md_q[0]
            if _md_pfad_q.is_file():
                _inhalt_q = _md_pfad_q.read_text(encoding="utf-8").lower()
                # Bekannte Schlagwort-Gruppen — pro Begriff reicht EIN
                # Treffer. Reihenfolge ist nur fuer Log-Klarheit.
                _pflicht_konzepte = [
                    ("zielbild", "zielbild"),
                    ("chat_service", "chatservice"),
                    ("rbac", "rbac"),
                    ("audit", "audit"),
                    ("abgrenzung", "abgrenzung"),
                    ("akzeptanz", "akzeptanz"),
                    ("test", "test"),
                ]
                # Nur pruefen, wenn die Aufgabe diese Konzepte auch nennt
                _fehlend_q: list[str] = []
                for _label_q, _marker_q in _pflicht_konzepte:
                    if (_marker_q in _aufgabe_q.lower()
                            and _marker_q not in _inhalt_q):
                        _fehlend_q.append(_label_q)
                if _fehlend_q:
                    audit("reviewer_unvollstaendig", {
                        "datei": _md_q[0],
                        "fehlende_konzepte": _fehlend_q,
                    }, pd, pn)
                    # FIX R 2026-10-31: Deterministischer Fail darf
                    # NICHT vom Loop ignoriert werden ("pytest gruen").
                    # Flag setzen; loop.py prueft es vor task_ok.
                    try:
                        state.reviewer_deterministic_fail = True
                    except (AttributeError, TypeError):
                        pass
                    return False

    aufgabe = state.aufgabe
    tests_ok = getattr(state, "baseline_gruen", True)

    # M-459: Reviewer prueft Task-Description, nicht Gesamtaufgabe.
    _akt_task = getattr(state, "aktuelle_task", None)
    _task_name = ""
    _task_desc = ""
    _arch_desc = ""
    if isinstance(_akt_task, dict):
        _task_name = _akt_task.get("name", "")
        _task_desc = _akt_task.get("description", "")
        if _akt_task.get("action") == "architect":
            _arch_desc = _task_desc
    user_content = (
        f"## AKTUELLE TASK: {_task_name}\n"
        f"## TASK-BESCHREIBUNG: {_task_desc}\n"
        f"## GESAMTAUFGABE: {aufgabe}\n\n"
        f"Baseline gruen: {tests_ok}\n\n"
        f"Diff:\n{diff}"
        # K40: Historie der vorherigen Reviewer-Runden.
        # Reviewer soll behobene Bugs NICHT erneut melden.
        + _reviewer_history_block(state)
    )
    # Hinweis an den Reviewer: Task-Beschreibung UND Auftrag-Treue.
    # FIX 2026-10-31: Der Auftrag enthaelt Verbote ("nicht X"), die
    # auch geprueft werden muessen.
    user_content += (
        "\n\nPruefe: "
        "(a) Hat DIESE Task das getan, was ihre TASK-BESCHREIBUNG "
        "verlangt? "
        "(b) Verletzt der Diff eine NEGATIVE Anweisung aus der "
        "GESAMTAUFGABE (nicht, kein, behalte, erhalte, nur)?"
    )
    if _arch_desc:
        user_content += f"\n\nArchitect-Vorgabe:\n{_arch_desc}"

    # K16: Volle Zieldatei IMMER anhaengen (nicht nur Architect-Modus).
    # Ohne Datei-Kontext sieht der Reviewer Importe, bestehende
    # Methoden und Definitionen nicht und meldet falsche high-bugs
    # ("import re nicht sichtbar", "CATEGORY_VALUES nicht pruefbar").
    _zieldatei = _akt_task.get("task_files", []) if isinstance(_akt_task, dict) else []
    if _zieldatei:
        _fp = Path(pd) / _zieldatei[0]
        if _fp.is_file():
            try:
                _content = _fp.read_text(encoding="utf-8")[:30000]
                user_content += (
                    f"\n\n--- VOLLE ZIELDATEI: {_zieldatei[0]} ---\n"
                    f"{_content}\n"
                    f"--- ENDE ---"
                )
            except (OSError, UnicodeDecodeError):
                pass

    reply = ask_llm(
        api_key, _reviewer_system(state, _zieldatei), user_content,
        model="deepseek-chat", temperature=0.0, max_tokens=4000,
        redact=False,  # OP-062a: Code-Pruefung braucht Rohdaten
        aufgabe="reviewer",
    )

    if not reply.ok:
        audit("reviewer_llm_fehler", {"fehler": reply.error}, pd, pn)
        return False

    raw = reply.content.strip()
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start < 0 or end <= start:
        audit("reviewer_json_fehler", {"raw": raw[:200]}, pd, pn)
        return False

    try:
        result = json.loads(raw[start:end])
    except json.JSONDecodeError:
        audit("reviewer_json_fehler", {"raw": raw[:200]}, pd, pn)
        return False

    approved = result.get("approved", False)
    bugs = result.get("bugs", [])

    # OP-164: Rename-Filter (Prompt-Haertung + deterministischer Post-Proc).
    # OP-164b: Auftrag-Treue-Filter (Wert-Kipp, type-ignore Over-Delivery).
    _bugs_high_before = sum(
        1 for _b in bugs
        if isinstance(_b, dict) and _b.get("severity") == "high"
    )
    bugs = _filter_rename_false_positives(bugs, diff, _task_desc)
    bugs = _filter_auftrag_treue_false_positives(
        bugs, diff, _task_desc, task_files=_tf_early,
        action=(
            (state.aktuelle_task or {}).get("action")
            if isinstance(state.aktuelle_task, dict) else None
        ),
    )
    _bugs_high_after = sum(
        1 for _b in bugs
        if isinstance(_b, dict) and _b.get("severity") == "high"
    )
    _filtered_total = _bugs_high_before - _bugs_high_after
    if _filtered_total > 0 and _bugs_high_after == 0:
        approved = True

    # OP-181 (a): Deterministischer Dead-Code-Pre-Check.
    # Nach den LLM-Filtern gemerged, damit Prompt-Heuristiken
    # deterministische Befunde nicht wegfiltern koennen.
    # Findet neue .py-Module, die nur von Tests referenziert werden.
    _dc_bugs = _pruefe_neue_module_genutzt(pd, diff)
    if _dc_bugs:
        bugs = list(bugs) + _dc_bugs
        if any(
            isinstance(_b, dict) and _b.get("severity") == "high"
            for _b in _dc_bugs
        ):
            approved = False

    audit("reviewer_result", {
        "approved": approved,
        "bugs": len(bugs),
        "summary": result.get("summary", "")[:200],
        "filtered": _filtered_total,
    }, pd, pn)

    if not approved:
        for bug in bugs:
            audit("reviewer_bug", bug, pd, pn)
        # M-314: bugs in State persistieren (fuer Reflection).
        state.reviewer_bugs = list(bugs)
    else:
        state.reviewer_bugs = []

    return approved
