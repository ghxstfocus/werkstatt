"""Reviewer-Agent (Phase 8, 2026-10-23).

Eigenstaendiger Reviewer. Bekommt Diff + Anforderung
+ Testergebnisse. Gibt strukturiertes Feedback zurueck.
Kein GO/NO_GO-Raten, sondern konkrete Bug-Funde.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from werkstatt.agent import ask_llm
from werkstatt.audit import audit
from werkstatt.loop_renderer import _with_spinner
from werkstatt.skills import load_all_skills, load_skill_by_name
from werkstatt.state import RunState


def _reviewer_history_block(state: RunState) -> str:
    """K40: Formatiert die Historie der vorherigen Reviewer-Runden.

    Verhindert, dass der Reviewer behobene Bugs erneut meldet.
    Max 3 Runden -- aeltere sind meist schon repariert.
    """
    _history = getattr(state, "reviewer_bugs_history", None) or []
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


## SEMANTIK-CHECK (HIGH-Bug)
- Wenn die Task eine Funktion X nennt, der Diff aber eine andere
  Funktion Y nutzt (z.B. `_section_timeline` statt
  `_section_timeline_entries`): HIGH-Bug, reject.
- Wenn ein bestehender Aufruf einer Funktion entfernt wird, ohne
  dass die Task das verlangt: HIGH-Bug.
- Wenn eine API erfunden wird (nicht im Import-/Code-Index):
  HIGH-Bug.


## KONSTANTEN-CHECK (HIGH-Bug, R-CHECK-1)
- Wenn die Task eine numerische Konstante nennt (z.B. `limit=10`,
  `max_retries=3`, `timeout=60`): pruefe, ob der Diff diese Zahl
  WOERTLICH enthaelt.
- Wenn der Diff eine ANDERE Zahl nutzt (`limit=5` statt `limit=10`):
  HIGH-Bug, reject. Auch wenn der Diff ansonsten korrekt aussieht.
- Wenn die Task eine Zahl nennt, der Diff sie aber NICHT setzt
  (z.B. `limit` unveraendert laesst): HIGH-Bug, reject.
- Wenn die Task KEINE Zahl nennt: ignorieren, kein Bug.
- Belege die Zahl im `description`-Feld: "Task fordert X=10,
  Diff nutzt X=5".


## SYMBOL-CHECK (HIGH-Bug, verhindert Fehltreffer)
- Bevor du einen Bug meldest ("Symbol X nicht definiert"): pruefe
  im Block `AKTUELLER DATEI-INHALT`, ob X dort definiert ist.
- Wenn X im Datei-Inhalt steht (als Zuweisung, def, class, import):
  KEIN Bug.
- Wenn X nirgends definiert ist: HIGH-Bug.
- Belege im `description`-Feld, ob du X im Datei-Inhalt gesucht
  hast: "X nicht im Datei-Inhalt (Zeilen 1-N)".
- Beispiel: `_SCORE_SENTINEL` ist im Datei-Inhalt bei Zeile 65
  als `_SCORE_SENTINEL = float("-inf")` definiert -> kein Bug.


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
"""


def _get_git_diff(
    project_dir: str | Path = "/opt/werkstatt",
    task_files: list[str] | None = None,
) -> str:
    """Holt den aktuellen Git-Diff im Zielprojekt.

    M-314: umfasst jetzt auch UNTRACKED-Dateien (git ls-files
    --others). Vorher war der Reviewer blind fuer neue Dateien,
    die der Builder mit `create` angelegt hat.

    K4: Wenn task_files uebergeben, nur diese Pfade diffen — sonst
    sieht der Reviewer kumulative Aenderungen frueherer Tasks.
    """
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


def _reviewer_system() -> str:
    """M-374: review-work IMMER laden."""
    skills = load_all_skills()
    parts = [REVIEWER_SYSTEM]
    rw = load_skill_by_name("review-work", skills)
    if rw and rw["body"]:
        parts.append("## Skill: Review-Work\n" + rw["body"])
    return "\n\n".join(parts)


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
    api_key = getattr(state, "api_key", "")
    if not api_key:
        audit("reviewer_phase_kein_key", {}, pd, pn)
        return False

    # K25: Phase-Review-Scope = Task-Dateien, nicht alle uncommitted Files.
    # Sonst sieht Reviewer alte RERUN-Reste (core/alerts/) und meldet
    # Bugs, die nicht zur Phase gehoeren.
    _phase_files: list[str] = []
    for _t in (getattr(state, "tasks", []) or []):
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
    for _t in (getattr(state, "tasks", []) or []):
        if isinstance(_t, dict):
            tasks_summary.append({
                "id": _t.get("id"), "name": _t.get("name"),
                "files": _t.get("task_files"),
                "status": _t.get("status"),
            })
    aufgabe = getattr(state, "aufgabe", "")
    akz = getattr(state, "akzeptanzkriterien", []) or []

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
                api_key, _reviewer_system(), user,
                model="deepseek-chat", temperature=0.2, max_tokens=4000,
            ),
        )
    except Exception as _exc:  # noqa: BLE001
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
        state.reviewer_bugs = _bugs  # type: ignore[attr-defined]
        return False

    audit("reviewer_phase_approved",
          {"bugs_medium": len(_medium),
           "bugs_low": len(_bugs) - len(_high) - len(_medium)},
          pd, pn)
    return True


def run_reviewer(state: RunState) -> bool:
    """Prueft den Code. Gibt True zurueck, wenn approved."""
    pd = state.project_dir
    pn = state.project_name
    api_key = getattr(state, "api_key", "")

    if not api_key:
        audit("reviewer_kein_key", {}, pd, pn)
        return False

    pd = getattr(state, "project_dir", None) or Path("/opt/werkstatt")
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
    _patches = getattr(state, "patches", None) or []
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
            _aufgabe_q = getattr(state, "aufgabe", "") or ""
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
                    if _marker_q in _aufgabe_q.lower():
                        if _marker_q not in _inhalt_q:
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
                        state.reviewer_deterministic_fail = True  # type: ignore[attr-defined]
                    except (AttributeError, TypeError):
                        pass
                    return False

    aufgabe = getattr(state, "aufgabe", "")
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
        api_key, _reviewer_system(), user_content,
        model="deepseek-chat", temperature=0.0, max_tokens=4000,
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

    audit("reviewer_result", {
        "approved": approved,
        "bugs": len(bugs),
        "summary": result.get("summary", "")[:200],
    }, pd, pn)

    if not approved:
        for bug in bugs:
            audit("reviewer_bug", bug, pd, pn)
        # M-314: bugs in State persistieren (fuer Reflection).
        state.reviewer_bugs = list(bugs)  # type: ignore[attr-defined]
    else:
        state.reviewer_bugs = []  # type: ignore[attr-defined]

    return approved
