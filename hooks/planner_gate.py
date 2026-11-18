"""Planner-Gate-Hook (M-349 + M-350 + M-349e).

Deterministische Pruefung des Plans nach dem Planner.
Der Hook ist die Wahrheit — nicht der Prompt.

Checks:
  1. DOKU_TASK: task_files matcht Doku-Regex.
  2. ACTION: action muss read/create/update/delete sein.
  3. TASK_FILE: task_files muss Datei mit Suffix sein.
  4. (entfernt K5.2) PHASEN_PFLICHT — Phasen sind optional.
  5. PHASE_ID: phase_id muss in phasen existieren.

Output: {"allow": bool, "reason": str, "info": {...}}
"""
from __future__ import annotations

import json
import re
import sys

_DOKU_PATTERNS = [
    re.compile(r"^docs/.*\.md$"),
    re.compile(r"^CHANGELOG\.md$"),
    re.compile(r"^PROGRESS\.md$"),
    re.compile(r"^README\.md$"),
    re.compile(r"^docs/STATUS\.md$"),
    # GOLD 2026-10-30: Alle .md/.rst/.txt-Dateien im docs/-Ordner
    # oder als Top-Level. Live-Beleg: SECURITY_LOG.md wurde als
    # Pfad erkannt, aber nicht als Doku-Pattern -> _prosa_nur_doku
    # = False -> DOKU_TASK abgelehnt.
    re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*\.(?:md|rst|txt)$"),
]
_VALID_ACTIONS = {"read", "create", "update", "delete", "verify"}
_VALID_SUFFIXES = (
    # Code
    ".py", ".sql", ".sh", ".bash",
    # Config
    ".yaml", ".yml", ".toml", ".cfg", ".ini", ".json",
    # Frontend
    ".html", ".css", ".js", ".ts",
    # Doku (GOLD 2026-10-30: Doku-Aufgaben sind legitim)
    ".md", ".rst", ".txt",
    # FIX Y 2026-10-31: Config-Example-Dateien. Live-Beleg: DeepSeek-
    # Aufgabe plante t5=...env.example, Gate lehnte ab, Loop exit 1.
    # .example, .template, .sample, .dist sind uebliche Endungen.
    ".example", ".template", ".sample", ".dist",
)
# K2026-11-07: Dotfiles ohne klassisches Suffix. `.gitignore` endet
# auf kein erlaubtes Suffix (der Punkt ist Praefix, keine Extension)
# und ist auch keine Doku-Datei. TASK_FILE lehnte ab -> Loop-Abbruch
# ohne Reflection (TASK_FILE ist strukturell). Whitelist fuer die
# ueblichen Dotfiles.
_DOTFILES = frozenset({
    ".gitignore", ".gitattributes", ".dockerignore",
    ".editorconfig", ".gitkeep",
})

def _deny(regel: str, task_id: str, datei: str,
          erklaerung: str, details: str) -> dict:
    """M-349e: info als Fakt (kein 'plane neu')."""
    if task_id and datei:
        fakt = f"Task {task_id} aendert {datei}"
    elif task_id:
        fakt = f"Task {task_id} verletzt Regel {regel}"
    elif datei:
        fakt = f"Datei {datei} verletzt Regel {regel}"
    else:
        fakt = f"Regel {regel} verletzt"
    return {
        "allow": False,
        "reason": f"{regel}: {fakt}",
        "info": {
            "regel": regel,
            "fakt": fakt,
            "erklaerung": erklaerung,
            "details": details,
            "verbotene_datei": datei,
        },
    }


def check_plan(payload: dict) -> dict:
    tasks = payload.get("tasks", [])
    phasen = payload.get("phasen", [])

    # 1) DOKU_TASK (Regex, nicht startswith).
    # K5.1: Nur ablehnen, wenn der Plan AUSSCHLIESSLICH Doku-Tasks
    # enthaelt (kein Code-Task). Doku-Nachzug als expliziter Task
    # neben Code-Aenderungen ist erlaubt — der Architect plant
    # STATUS/CHANGELOG/DECISIONS korrekt als Nachtrag.
    _has_code_task = False
    for t in tasks:
        if not isinstance(t, dict):
            continue
        for f in t.get("task_files", []) or []:
            if not isinstance(f, str):
                continue
            if not any(pat.match(f) for pat in _DOKU_PATTERNS):
                _has_code_task = True
                break
        if _has_code_task:
            break

    # GOLD 2026-10-30: Doku-Aufgaben erlauben.
    # Wenn die Architect-Prosa nur Doku-Dateien nennt und keinen
    # Code, ist ein Doku-Only-Plan KORREKT. Live-Beleg
    # 2026-10-30 22:17: Aufgabe 'entferne Punkt 1 aus
    # docs/STATUS.md', Planner-Split baute 1 Doku-Task, Hook
    # lehnte ab (M-349b) -> 3x Plan-Reflection -> Loop-Abbruch.
    _prosa = payload.get("architect_prosa") or ""
    _aufgabe = payload.get("aufgabe") or ""

    # GOLD 2026-10-30: Doku-Aufgabe erkennen.
    # Wenn die ORIGINAL-Aufgabe Doku-Ziele nennt (docs/, STATUS.md,
    # CHANGELOG.md, "Doku", "Dokumentation"), ist ein Doku-Only-
    # Plan korrekt. Die Prosa-Pruefung reicht nicht, weil die Prosa
    # oft auch die Code-Datei als Kontext nennt (z.B. "die Klasse
    # AuditReaderError existiert nicht mehr in
    # core/reporting/audit_reader.py").
    _aufgabe_doku = False
    if isinstance(_aufgabe, str) and _aufgabe:
        _doku_marker = (
            "docs/", "STATUS.md", "CHANGELOG.md", "README.md",
            "PROGRESS.md", "SECURITY_LOG.md", "DECISIONS.md",
            "Doku", "Dokumentation", "Markdown",
        )
        _aufgabe_doku = any(m in _aufgabe for m in _doku_marker)
        # Aber: Wenn die Aufgabe explizit "keine Doku" sagt, nicht.
        if "keine doku" in _aufgabe.lower() or "kein code" in _aufgabe.lower() and "doku" in _aufgabe.lower():
            _aufgabe_doku = True

    _prosa_nur_doku = False
    if isinstance(_prosa, str) and _prosa:
        # Pfade in der Prosa finden
        _prosa_pfade = re.findall(
            r'(?:^|\s)([a-zA-Z_][a-zA-Z0-9_/.-]+\.(?:py|md|sql|html|css|js|yaml|yml|json|toml))',
            _prosa,
        )
        if _prosa_pfade:
            _prosa_nur_doku = all(
                any(pat.match(p) for pat in _DOKU_PATTERNS)
                for p in _prosa_pfade
            )

    if not _has_code_task and not _prosa_nur_doku and not _aufgabe_doku:
        for t in tasks:
            if not isinstance(t, dict):
                continue
            for f in t.get("task_files", []) or []:
                if not isinstance(f, str):
                    continue
                for pat in _DOKU_PATTERNS:
                    if pat.match(f):
                        return _deny(
                            "DOKU_TASK",
                            t.get("id", "?"),
                            f,
                            "Doku-Only-Plan: kein Code-Task.",
                            "Der Loop schreibt Doku automatisch "
                            "(PROGRESS.md pro Task, CHANGELOG.md pro "
                            "Phase). Der Plan wird nicht gebaut, weil "
                            "er ausschliesslich Doku aendert.",
                        )

    # 2) ACTION
    for t in tasks:
        if not isinstance(t, dict):
            continue
        a = t.get("action")
        if a is not None and a not in _VALID_ACTIONS:
            return _deny(
                "ACTION",
                t.get("id", "?"),
                "",
                f"action='{a}' ist nicht erlaubt.",
                f"action='{a}' ist ungueltig. Erlaubte Werte: "
                f"{sorted(_VALID_ACTIONS)}.",
            )

    # A planned action without a concrete file scope is not executable by the
    # project-bound workers. Historically the empty-list fallback below let
    # such tasks pass, producing runs like "Zieldatei: (keine)" which invoked
    # Builder/Review but could never produce criterion-bound file evidence.
    for index, task in enumerate(tasks, 1):
        if not isinstance(task, dict):
            task_id = f"t{index}"
            files = None
        else:
            task_id = task.get("id", f"t{index}")
            files = task.get("task_files")
        if not isinstance(files, list) or not files:
            return _deny(
                "TASK_FILE",
                str(task_id),
                "",
                "Task hat keinen konkreten Dateiscope.",
                "Jeder geplante Task braucht task_files als nichtleere "
                "Liste konkreter Datei-Pfade. Ohne Dateiscope kann der "
                "Loop keine passende Rolle sicher auswaehlen oder deren "
                "Ergebnis belegen.",
            )

    # 3) TASK_FILE
    for t in tasks:
        if not isinstance(t, dict):
            continue
        for f in t.get("task_files", []) or []:
            if not isinstance(f, str):
                return _deny(
                    "TASK_FILE",
                    t.get("id", "?"),
                    repr(f),
                    "task_files enthaelt Nicht-String.",
                    "task_files: list[str] mit konkreten "
                    "Datei-Pfaden.",
                )
            if f.endswith("/"):
                return _deny(
                    "TASK_FILE",
                    t.get("id", "?"),
                    f,
                    f"'{f}' ist ein Ordner.",
                    f"Erlaubt: Datei mit Suffix "
                    f"{sorted(_VALID_SUFFIXES)}.",
                )
            if f in _DOTFILES:
                continue
            if not f.endswith(_VALID_SUFFIXES):
                # K5.1: Doku-Datei mit Code-Task daneben ist erlaubt
                # (Doku-Nachtrag vom Architect geplant).
                if _has_code_task and any(
                    pat.match(f) for pat in _DOKU_PATTERNS
                ):
                    continue
                return _deny(
                    "TASK_FILE",
                    t.get("id", "?"),
                    f,
                    f"'{f}' hat kein gueltiges Suffix.",
                    f"Erlaubt: {sorted(_VALID_SUFFIXES)}.",
                )

    # 4) PHASEN_PFLICHT (K5.2): entfernt. Phasen sind OPTIONAL.
    # Der Architect liefert phasenlose Plaene; der Loop baut sie.
    # Phasen werden nur validiert, wenn sie vorhanden sind (Check 5).

    # 5) PHASE_ID
    if phasen:
        _ids = {
            phase["id"] for phase in phasen
            if isinstance(phase, dict) and isinstance(phase.get("id"), str)
        }
        for t in tasks:
            if not isinstance(t, dict):
                continue
            pid = t.get("phase_id")
            if pid is not None and (
                not isinstance(pid, str) or pid not in _ids
            ):
                return _deny(
                    "PHASE_ID",
                    t.get("id", "?"),
                    "",
                    f"phase_id='{pid}' ist nicht erlaubt.",
                    f"Gueltig: {sorted(_ids)}.",
                )

    # 6) MIGRATIONS_KOLLISION (K17c): geplante Migrationsnummer
    #    kollidiert mit existierender Datei in data/migrations/.
    _prosa = payload.get("architect_prosa") or ""
    _projdir = payload.get("project_dir") or ""
    if isinstance(_prosa, str) and _prosa and _projdir:
        _koll = _check_migrations_kollision(_prosa, _projdir)
        if _koll:
            _nums = ", ".join(k["nummer"] for k in _koll)
            _hoechste = _koll[0].get("hoechste", "?")
            _naechste = _koll[0].get("naechste", "?")
            return _deny(
                "MIGRATIONS_KOLLISION",
                "",
                f"data/migrations/{_koll[0]['nummer']}_*.sql",
                f"Migrationsnummer(n) {_nums} existieren bereits. "
                f"Naechste freie Nummer: {_naechste}.",
                f"Hoechste vorhandene Nummer: {_hoechste}. "
                f"Verwende NUR die naechste freie Nummer {_naechste}.",
            )

    return {"allow": True, "reason": "", "info": {}}


def _check_migrations_kollision(prosa: str, project_dir: str) -> list[dict]:
    """K17c: Prueft geplante Migrationsnummern gegen data/migrations/.

    Sucht 'data/migrations/NNNN_*.sql' in der Prosa. Kollidiert
    NNNN mit existierender Datei -> Eintrag. Max 20 Treffer
    als Schutz gegen Endlos-Parsing.
    """
    try:
        from pathlib import Path as _P
        mdir = _P(project_dir) / "data" / "migrations"
        if not mdir.is_dir():
            return []
        existierend: set[str] = set()
        for f in mdir.glob("*.sql"):
            head = f.name.split("_", 1)[0]
            if head.isdigit():
                existierend.add(head)
        if not existierend:
            return []
        hoechste = max(existierend)
        naechste = f"{int(hoechste) + 1:04d}"
        # K29: Nur Header-Zeilen "## data/migrations/NNNN_..." pruefen.
        # Vorher: alle "data/migrations/NNNN_" in der Prosa -- fuehrte
        # zu False-Positives, wenn Architect eine existierende Datei
        # als Muster referenziert ("folgt Muster von 0008_x.sql").
        geplant = re.findall(
            r"^##\s+data/migrations/(\d+)_", prosa, re.MULTILINE,
        )
        koll: list[dict] = []
        for n in sorted(set(geplant)):
            if n in existierend:
                koll.append({
                    "nummer": n,
                    "hoechste": hoechste,
                    "naechste": naechste,
                })
            if len(koll) >= 20:
                break
        return koll
    except Exception:
        return []


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        print(json.dumps({
            "allow": False,
            "reason": "PAYLOAD: ungueltiges JSON",
            "info": {"regel": "PAYLOAD", "fakt": "JSON ungueltig",
                     "erklaerung": "Payload ist kein JSON.",
                     "details": "Der Plan wird nicht gebaut.",
                     "verbotene_datei": ""},
        }))
        return 0
    print(json.dumps(check_plan(payload), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
