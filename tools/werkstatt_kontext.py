#!/usr/bin/env python3
"""werkstatt_kontext.py — Onboarding-Block fuer neue Chat-Sessions.

Zweck: Ein neuer Chat (LLM) bekommt mit EINEM Paste-Block alles,
um Werkstatt zu verstehen und weiterzumachen.

Aufruf:
    python3 tools/werkstatt_kontext.py            # voller Block
    python3 tools/werkstatt_kontext.py --check    # nur Zustand
    python3 tools/werkstatt_kontext.py --json     # Maschinenlesbar

Das Skript ist read-only. Es schreibt nichts. Es ruft nur git,
pytest, drift-Checks und liest Status-Dateien.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

WERKSTATT = Path(__file__).resolve().parent.parent
STATUS = WERKSTATT / "docs" / "STATUS.md"


# ============================================================
# Helpers
# ============================================================

def _run(cmd, timeout: int = 60) -> tuple[int, str]:
    """Fuehrt Befehl aus, gibt (exit_code, kombinierter_output)."""
    try:
        r = subprocess.run(
            cmd, shell=isinstance(cmd, str), cwd=WERKSTATT,
            capture_output=True, text=True, timeout=timeout,
            check=False,
        )
        return r.returncode, (r.stdout + r.stderr).strip()
    except Exception as e:  # noqa: BLE001
        return -1, f"[FEHLER: {e}]"


def _zeile(titel: str) -> str:
    return f"\n{'=' * 72}\n{titel}\n{'=' * 72}\n"


def _lies(pfad: Path) -> str:
    try:
        return pfad.read_text(encoding="utf-8")
    except Exception as e:  # noqa: BLE001
        return f"[nicht lesbar: {e}]"


# ============================================================
# Statische Abschnitte
# ============================================================

def abschnitt_identitaet() -> str:
    return _zeile("1. WAS IST WERKSTATT?") + """
Werkstatt ist ein Meta-Loop-System (Debian, Python 3.11, /opt/werkstatt).
Es baut und repariert andere Projekte durch einen LLM-getriebenen
Agenten-Loop. Rollen laufen SEQUENTIELL (kein paralleles Rollen-Spiel).

Pipeline: Explorer -> Scout -> Architect -> Planner/Split -> Builder
          -> Reviewer -> Reflection -> Verify -> Gates

Kern-Idee: Der Loop liest docs/STATUS.md (offene OPs), waehlt einen
Punkt, baut ihn, testet ihn, und committet wenn alles gruen ist.
"""


def abschnitt_rollen() -> str:
    return _zeile("2. DIE ROLLEN") + """
Explorer   — findet Dateien/Kontext zur Aufgabe. Deterministisch
             (grep, ruff, pytest, Migrationsstand) + LLM-Fallback.
             Liefert: state.explorer_context (Datei-Liste) und
                      state.explorer_findings (Diagnostics).

Scout      — prueft, ob der Auftrag bereits erfuellt ist (Content-
             Check), und liefert einen api_auszug (Symbol-Liste).
             Liefert: state.scout_api_auszug.

Architect  — baut einen Prosa-Plan. Sieht: explorer_findings,
             scout_api_auszug, api_index_cache (AST-Block).
             Sieht NICHT explorer_context (Datei-Liste) — OP-137.
             Liefert: state.architect_prosa.

Planner    — zerlegt den Plan in Tasks (id, name, task_files, action).
             Liefert: state.tasks, state.tests, state.akzeptanzkriterien.

Builder    — baut pro Task die Patches (aider-Patches, AST-validiert).
             Sieht: explorer_context + explorer_findings + api_index_cache.

Reviewer   — prueft den Diff, liefert Bugs. Approval/Reject.

Reflection — bei Reject: baut Feedback, ruft Builder erneut.
             Sieht: last_verify_errors, reviewer_bugs, patches.
             Nutzt on-demand Skill "systematic-debugging".

Verify     — fuehrt verify.json-Stages aus (post_build: py_compile,
             ruff, mypy, pytest, control_drift, ...).

Gates      — Human-Gate am Plan und am Commit. j/n/a-Prompts.
"""


def abschnitt_workflow() -> str:
    return _zeile("3. WIE WIR ARBEITEN (User <-> Chat)") + """
Der User arbeitet mit dem Chat in BLOCKEN. Jeder Block ist ein
zusammenhaengendes bash-Skript, das der User ausfuehrt und dessen
Ausgabe er zurueckpastet.

Standard-Muster:

  1. Chat schickt MESS-BLOCK (read-only, bash).
     - Rohdaten sammeln, BEVOR Designentscheidungen fallen.
     - User fuehrt aus, pastet Ausgabe.

  2. Chat analysiert MESSUNG, stellt Design/Plan als Text vor.
     - Kein Code, nur Beschreibung.
     - User bestaetigt oder korrigiert.

  3. Chat schickt PATCH-BLOCK.
     - Enthaelt: --check-Modus zuerst (dry-run), dann apply.
     - Jeder Patch mit count==1-Assert pro Ersetzung.
     - Pre-Commit + Commit + Push im selben Block.

  4. Nach Erfolg: naechster Block oder Pause.

KRITISCHE Regeln fuer Block-Bau:

- KEIN 'exit' in bash — killt die SSH-Session. Python 'raise
  SystemExit(1)' ist OK (beendet nur Python).
- KEIN re.DOTALL + \\Z fuer Patch — nutzt str.replace mit exaktem
  mehrzeiligem Anker + count==1-Assert.
- Pre-Commit-Pflicht: py_compile, pytest, audit_drift, control_drift,
  state_inventory, ruff auf geaenderten Files.
- Loop niemals mit 'yes j | ...' oder --auto-approve starten.
- Plan-Gate: <=5 Tasks, plausible Zieldateien -> j. Sonst n + Grund.
- KEIN 'pytest | tail': $? ist tail-Exit, immer 0.
  Richtig: pytest > /tmp/pt.log 2>&1; PT=$?
- Anker mit '\\n'-Prefix bei variabler Einrueckung: sonst Substring-Match
  (12-Space-Anker matcht 16-Space-Zeile als Substring).
- Kein Heredoc in 'if/else'-Block: Shell haengt in '>'-Prompt.
- Baseline-aware Gates: 'AFTER <= BEFORE' ist OK. Nur 'AFTER > BEFORE'
  (Regress) blockt.

DREI GATES, 'n' bedeutet unterschiedlich:

  Plan-Gate        | n = Reflection mit Grund (1 Runde)
  Reflection-Gate  | n = Task fail, LOOP LAEUFT WEITER mit naechster Task
  Commit-Gate      | n = LOOP BRICHT AB (Phase-Reject, kein Commit)

Der User hat das in 5+ Sessions durch Beobachtung gelernt. Wenn du
selbst einen Block baust: schreib bei jedem 'j/n/a'-Prompt dazu, was
'n' fuer DIESEN Gate-Zustand bedeutet.

Loop-Start (manuell vom User):

  cd /opt/werkstatt
  source .venv/bin/activate
  python3 -m werkstatt.loop --project werkstatt --fresh \\
    --aufgabe "$(python3 -c \\
      \"import re; from pathlib import Path; \\
       s = Path('docs/STATUS.md').read_text(); \\
       m = re.search(r'### OP-NNN:.*?(?=\\n### OP-|\\n## |\\\\Z)', s, re.DOTALL); \\
       print(m.group(0).strip() if m else 'FEHLER')\")"
"""


def abschnitt_regeln() -> str:
    return _zeile("4. KONVENTIONEN (aus MERKPOSTEN + DOC_CONVENTIONS)") + """
Die wichtigsten Regeln:

1. ERST MESSEN, DANN DESIGNEN, DANN FIXEN.
   Kein Fix ohne reproduzierten Bug. Kein Design ohne Messung.
   Bauchgefuehl ist kein Messergebnis. Hypothesen als Hypothesen
   markieren, nicht als Fakt.

2. HANDOFF-SCHREIBEN IST AUCH MESS-AUFGABE.
   Jede Behauptung im Handoff entweder nachgemessen oder als
   Hypothese markiert. Handoff ist ein Messbericht, kein Freitext.

3. OP-CLOSE MUSS BLOCKER BEREINIGEN.
   Bei OP-Close: alle 'Blockiert von:'-Feldern pruefen, die auf
   den geschlossenen OP zeigen. Ein Durchgang, nicht iterativ.

4. PRE-COMMIT-PFLICHT:
   py_compile, pytest, audit_drift, control_drift, state_inventory,
   ruff auf geaenderten Files. Alle gruen -> commit.

5. OP-CLOSE-KONVENTION:
   - STATUS.md-Eintrag loeschen (nur offene OPs stehen dort)
   - Delete-Zone-Eintrag oben einfuegen (chronologisch absteigend)
   - PROGRESS.md-Eintrag anhaengen (append-only, Ende)

6. DREI STATUS-DATEIEN:
   - docs/STATUS.md      — nur offene OPs, Format nach DOC_CONVENTIONS §5
   - PROGRESS.md         — erledigt, append-only
   - docs/MERKPOSTEN.md  — Prozess-Lehren, nicht durchsuchbar

7. NEUE ARTEFAKTE (Stand 2026-11-05, Ende Session 3):
   - tools/state_inventory.py    — RunState-Inventur (read-only, --check)
   - docs/STATE-INVENTUR.md      — 104 Felder, 23 Ghosts, 47 Tote (OP-135b)
   - docs/STATE-CONTRACTS.md     — 5 Dataclasses, 5 Vertraege
   - werkstatt/state_contracts.py — Property-Views, validate_transition
   - werkstatt/rollen.py         — Rollen-Registry (7 Rollen, fail-closed)
   - docs/adr/                   — 14 ADRs, u.a. ADR-0013 (Layer),
                                    ADR-0014 (Rollen-Registry)

8. ROLLEN-REGISTRY (2026-11-05, ADR-0014):
   werkstatt/rollen.py ist Single Source of Truth fuer Skills,
   System-Prompts, Tools pro Rolle. Zentrale Regel: Rolle ohne
   skills + ohne skill_filter_rolle = KEINE Skills (fail-closed).
   M-446: Architect darf keine Skills haben (plan-crafting enthaelt
   '## Tools', triggert CoT bei deepseek-reasoner, liefert DSML).

9. GATE-EXIT-CODES EXPLIZIT (2026-11-05):
   Jeder Gate-Schritt muss explizit sys.exit(1) oder raise
   SystemExit(1) bei Fehler haben. 'python3 -c "..."' ohne
   sys.exit gibt immer 0. 'pytest | tail' gibt tail-Exit (0).
   'if AFTER == BEFORE' blockt Fortschritt (Baseline sinkt).

10. ARCHITEKTUR-DOKU IST WAHRHEIT (2026-11-05):
    Wenn Code und docs/ARCHITECTURE.md sich widersprechen, folgt
    der Code der Doku. Jeder Fix, der einen konkreten Fehler
    verhindert (M-446, K51, K52, ...), bekommt einen Test, der
    das ALTE Verhalten verbietet — nicht nur einen, der das neue
    Verhalten prueft. Ohne Test kehrt der Bug zurueck.

11. TEST-CONTRACT BEI VERHALTENS-AENDERUNG (2026-11-05):
    Vor jedem Patch, der eine Verhaltens-Aenderung durchfuehrt:
    'grep -rn '<alter_wert>' tests/'. Wenn ein Test das alte
    Verhalten prueft, im selben Patch-Block umstellen. Sonst
    ist der Pre-Commit rot ohne Kontext (PT>0, Ursache unklar).
"""


def abschnitt_zustand() -> str:
    out = _zeile("5. AKTUELLER ZUSTAND (gemessen gerade)")

    _, head = _run(["git", "log", "--oneline", "-1"])
    out += f"\nHEAD: {head}\n"

    rc, wc = _run(["git", "status", "--short"])
    if not wc:
        out += "Working Tree: clean\n"
    else:
        out += f"Working Tree: DIRTY\n{wc}\n"

    rc, remote = _run("git ls-remote origin main | head -1")
    if rc == 0 and remote:
        out += f"origin/main: {remote.split()[0][:7]}\n"

    rc, tests = _run(
        ["python3", "-m", "pytest", "-q",
         "--ignore=tests/test_shell.py"], timeout=180)
    last = tests.split("\n")[-1] if tests else "?"
    out += f"\nTests: {last}\n"

    for name, cmd in [
        ("audit_drift", ["python3", "tools/audit_drift.py", "--check"]),
        ("control_drift", ["python3", "tools/control_drift.py", "--check"]),
        ("state_inventory", ["python3", "tools/state_inventory.py", "--check"]),
    ]:
        rc, _ = _run(cmd)
        status = "OK" if rc == 0 else f"FAIL (exit {rc})"
        out += f"{name}: {status}\n"

    rc, ruff = _run(["python3", "-m", "ruff", "check", "werkstatt/", "tests/"])
    m = re.search(r"Found (\d+) error", ruff)
    n_err = m.group(1) if m else "0"
    out += f"ruff Baseline: {n_err} errors "
    out += "(Altzustand, nicht durch neue Commits eingefuehrt; "
    out += "jede OP darf Baseline lassen, Senkung ist Bonus)\n"

    try:
        status_text = STATUS.read_text()
        ops = re.findall(r"^### OP-", status_text, re.MULTILINE)
        out += f"Offene OPs in STATUS.md: {len(ops)}\n"
    except Exception as e:  # noqa: BLE001
        out += f"Offene OPs: [nicht lesbar: {e}]\n"

    return out


def abschnitt_commits(n: int = 10) -> str:
    out = _zeile(f"6. LETZTE {n} COMMITS")
    _, log = _run(["git", "log", "--oneline", f"-{n}"])
    return out + "\n" + log + "\n"


def abschnitt_naechste_ops(max_anzahl: int = 10) -> str:
    out = _zeile("7. NAECHSTE OFFENE OPs (nach Blocker-Status)")
    try:
        text = STATUS.read_text()
    except Exception as e:  # noqa: BLE001
        return out + f"\n[nicht lesbar: {e}]\n"

    ops = []
    for m in re.finditer(
        r"^### (OP-[\w-]+): ([^\n]+)\n(.*?)(?=^### OP-|^## |\Z)",
        text, re.MULTILINE | re.DOTALL,
    ):
        op_id, titel, body = m.group(1), m.group(2), m.group(3)
        blocker_m = re.search(
            r"^- \*\*Blockiert von:\*\*\s*(.*)$", body, re.MULTILINE)
        blocker = (blocker_m.group(1).strip() if blocker_m else "")
        typ_m = re.search(r"^- \*\*Typ:\*\*\s*(.*)$", body, re.MULTILINE)
        typ = typ_m.group(1).strip() if typ_m else "?"
        ops.append({"id": op_id, "titel": titel,
                    "blocker": blocker, "typ": typ})

    existierende = {op["id"] for op in ops}
    frei, leicht, stale = [], [], []
    for op in ops:
        b = op["blocker"]
        if b in ("—", "-", ""):
            frei.append(op)
            continue
        refs = re.findall(r"OP-\d+[ab]?", b)
        if refs and all(r not in existierende for r in refs):
            stale.append(op)
            continue
        leicht.append(op)

    if frei:
        out += f"\nFREI ({len(frei)}):\n"
        for op in frei[:max_anzahl]:
            out += f"  {op['id']:10s} [{op['typ'][:22]:22s}] {op['titel']}\n"
        if len(frei) > max_anzahl:
            out += f"  (+{len(frei) - max_anzahl} weitere)\n"

    if stale:
        out += f"\nSTALE-BLOCKER ({len(stale)}) — referenzieren geloeschte OPs:\n"
        out += "  (Hinweis: Bereinigung ist OP-146. Wenn du in einem der\n"
        out += "   folgenden OPs arbeiten willst, erst OP-146 abschliessen.\n"
        out += "   Nicht eigenmaechtig stale-Referenzen fixen.)\n"
        for op in stale[:max_anzahl]:
            out += f"  {op['id']:10s} blockiert von: {op['blocker']}\n"

    if leicht:
        out += f"\nMIT BLOCKERN ({len(leicht)}):\n"
        for op in leicht[:max_anzahl]:
            out += f"  {op['id']:10s} [{op['typ'][:22]:22s}] {op['titel']}\n"
            out += f"             blockiert von: {op['blocker']}\n"
        if len(leicht) > max_anzahl:
            out += f"  (+{len(leicht) - max_anzahl} weitere)\n"

    return out


def abschnitt_erste_aufgabe() -> str:
    return _zeile("8. DEINE ERSTE AUFGABE (neuer Chat)") + """
Du bist ein neuer Chat, der gerade den obigen Kontext-Block bekommt.

DEINE ERSTE AUFGABE:

  1. Lies alle Abschnitte 1-7.
  1b. Lies docs/MERKPOSTEN.md — mindestens die letzten 10 Sektionen.
      Prozess-Lehren aus OP-134..165, u.a.: Gate-Exit-Codes,
      CoT-Trigger (Self-Check-Block auf Reasoning-Modellen),
      Anker mit \\n-Prefix, Heredoc in if/else, Test-Contract,
      Doku-ist-Wahrheit.
  1c. Lies docs/adr/README.md — 14 Architecture Decision Records.
      Besonders ADR-0013 (Layer-Architektur) + ADR-0014
      (Rollen-Registry) fuer das aktuelle Weltbild.
  2. Frage den User EINE Frage: 'Was ist die Session-Aufgabe?'
     Optionen (aus Abschnitt 7 ableitbar):
       - Naechster freier OP
       - Ein bestimmter OP aus der Liste
       - Etwas anderes (Bugfix, Doku, ...)
  3. Wenn die Aufgabe klar ist:
       - Beginne mit einem MESS-BLOCK (read-only).
       - KEIN Code, KEINE Aenderung, keine Datei anfassen.
       - Erst messen, dann designen, dann fixen.
  4. Bei Unklarheit: User fragen. Nicht raten.

DIE 4 HAEUFIGSTEN FEHLER DER LETZTEN SESSIONS (2026-11-05):

1. 'pytest | tail' -> Exit-Code von tail, nicht pytest. 3x passiert
   in einer Session. Nutze 'pytest > /tmp/pt.log 2>&1; PT=$?'.
2. Anker ohne '\\n'-Prefix -> Substring-Match bei variabler
   Einrueckung (12-Space matcht 16-Space).
3. Architektur-Doku ignorieren -> M-446-Regress: Architect lud
   plan-crafting (mit '## Tools'), deepseek-reasoner lieferte DSML.
4. Tests bei Verhaltens-Aenderung nicht nachziehen -> PT>0 nach
   Commit. Immer 'grep tests/' vor dem Patch.

WICHTIG:
- Du hast KEINEN direkten Shell-/Datei-Zugriff.
- Du arbeitest nur mit dem, was der User pastet.
- Nichts anfassen, was du nicht gemessen hast.
- Wenn der User sagt 'wie empfohlen' oder 'ja', bestaetigt er deine
  Empfehlung aus der letzten Nachricht.

WENN DU UNSICHER BIST:
Der Block ist reproduzierbar. Bitte den User:

  python3 tools/werkstatt_kontext.py

Das Skript liegt in tools/ und ist read-only. Es ruft git, pytest,
Drift-Checks und liest docs/STATUS.md. Wenn der Zustand sich waehrend
der Session aendert, kann es jederzeit erneut laufen.

SKRIPT-VARIANTEN:
- `--check`  nur der Zustands-Abschnitt (5), fuer schnelles Re-Check.
- `--json`   Maschinenlesbar (head, working_tree_clean, ops_open),
             fuer Skripte oder gezielte Abfragen.
- (ohne Flag) der volle Block wie hier.

VIEL ERFOLG.
"""


# ============================================================
# Main
# ============================================================

def sammle_alles(nur_zustand: bool = False) -> str:
    if nur_zustand:
        return abschnitt_zustand()
    return "\n".join([
        "WERKSTATT KONTEXT-BLOCK — bitte komplett in den Chat pasten",
        "(alle Abschnitte read-only, HEAD und Tests gerade gemessen)",
        "(dieser Block ist der EINZIGE Input des neuen Chats; er hat",
        " keinen Shell-/Datei-Zugriff und arbeitet nur mit dem, was",
        " der User zurueckpastet)",
        abschnitt_identitaet(),
        abschnitt_rollen(),
        abschnitt_workflow(),
        abschnitt_regeln(),
        abschnitt_zustand(),
        abschnitt_commits(10),
        abschnitt_naechste_ops(),
        abschnitt_erste_aufgabe(),
    ])


def sammle_json() -> dict:
    _, head = _run(["git", "log", "--oneline", "-1"])
    _, wc = _run(["git", "status", "--short"])
    ops_count = 0
    try:
        text = STATUS.read_text()
        ops_count = len(re.findall(r"^### OP-", text, re.MULTILINE))
    except Exception:  # noqa: BLE001, S110
        pass
    return {
        "head": head,
        "working_tree_clean": not wc,
        "ops_open": ops_count,
    }


def main() -> int:
    p = argparse.ArgumentParser(
        description="Werkstatt-Kontext-Block fuer neue Chat-Sessions.")
    p.add_argument("--check", action="store_true",
                   help="nur den dynamischen Zustand ausgeben")
    p.add_argument("--json", action="store_true",
                   help="Maschinenlesbare Kurzform")
    args = p.parse_args()

    if args.json:
        print(json.dumps(sammle_json(), indent=2))
        return 0

    print(sammle_alles(nur_zustand=args.check))
    return 0


if __name__ == "__main__":
    sys.exit(main())
