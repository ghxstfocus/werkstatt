"""
# standalone: Chat-Onboarding-Block fuer den User. Manuell
# aufgerufen (python3 tools/werkstatt_kontext.py), NICHT aus
# dem Loop. Reines Read-only-Werkzeug.
werkstatt_kontext.py — Onboarding-Block fuer neue Chat-Sessions.

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
    except Exception as e:
        return -1, f"[FEHLER: {e}]"


def _zeile(titel: str) -> str:
    return f"\n{'=' * 72}\n{titel}\n{'=' * 72}\n"


def _lies(pfad: Path) -> str:
    try:
        return pfad.read_text(encoding="utf-8")
    except Exception as e:
        return f"[nicht lesbar: {e}]"


# ============================================================
# Statische Abschnitte
# ============================================================

def abschnitt_identitaet() -> str:
    return _zeile("1. WAS IST WERKSTATT?") + """
Werkstatt ist eine projektbezogene Agenten- und Entwicklungsumgebung.
Ein zentraler Chat untersucht das aktive Repository, erklaert Befunde,
nimmt Auftraege an und steuert den Loop nach ausdruecklicher Freigabe.

Der Loop arbeitet in spezialisierten Rollen mit deterministischen
Pruefungen. Die Rollen koennen intern nacheinander laufen; waehrenddessen
bleibt der Chat fuer Rueckfragen und lesende Diagnose ansprechbar.

Zentrale Leitplanken:
- Repo-Aussagen muessen durch konkrete Dateien, Zeilen, Tests oder Events
  belegt werden.
- Schreibende Aktionen brauchen eine eigene, klar begrenzte Freigabe.
- Das Plan-Gate und das abschliessende Ergebnis-Gate bleiben Pflicht.
- STATUS ist die kurze Queue aktueller, startbarer Arbeit; ROADMAP ist
  langfristiger Fokus; PROGRESS ist append-only Abschlussgeschichte.
- Akzeptierte Entscheidungen stehen in ADRs. Vorgeschlagene ADRs sind
  keine Implementierungsanweisung.

Einstieg: AGENTS.md, docs/ROADMAP.md, docs/STATUS.md,
docs/DOC_CONVENTIONS.md und relevante akzeptierte ADRs.
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
Der Chat ist Ansprechpartner und Kontrollpunkt fuer das Projekt. Er
prueft Repository, Status und relevante ADRs selbst, nennt waehrend
laengerer Arbeiten die laufenden Schritte und beantwortet Rueckfragen,
ohne einen aktiven Loop-Run still zu veraendern.

Arbeitsweise:
  1. Auftrag und Projektkontext klaeren; fehlende Information gezielt
     erfragen.
  2. Repo und aktuelle Dokumentation untersuchen und Belege nennen.
  3. Einen begrenzten Plan mit Dateien, Risiken und Verify-Schritten
     formulieren. Das verpflichtende Plan-Gate braucht menschliche
     Entscheidung.
  4. Aenderungen im freigegebenen Umfang ausfuehren, testen und
     dokumentieren. Vor schreibenden Chat-Aktionen ist eine konkrete
     Freigabe erforderlich.
  5. Ergebnis, Tests, Commit-Referenz und verbleibende Punkte im Chat
     zusammenfassen. Fehler selbst diagnostizieren und innerhalb des
     Auftrags beheben; bei unklarer Anforderung oder Gate-Entscheidung
     nachfragen.

Laufender Run:
- Lesende Fragen duerfen parallel beantwortet werden.
- Eine Plan-Aenderung wird als eigener Vorschlag am sicheren Checkpoint
  behandelt und braucht erneut das Plan-Gate.
- Chat-Freigabe ersetzt weder Plan-Gate noch Ergebnis-/Review-Gate.
- Keine stillen Pushes, Merges, Loeschungen oder Erweiterungen des
  freigegebenen Arbeitsumfangs.

Wenn Serverzugriff fuer einen Schritt fehlt, benenne exakt den fehlenden
Zugriff und gib einen gezielten, pruefbaren Befehl aus. Lass den Nutzer
keine bereits verfuegbaren Repo-Ausgaben manuell sammeln oder kopieren.

Shell-Regeln fuer ausgegebene Befehle:
- Kein 'pytest | tail' als Exit-Code-Beleg: Pipe kann den Fehlercode
  verdecken.
- Befehle muessen Arbeitsverzeichnis, Umgebung und erwartetes Ergebnis
  klar nennen.
- Destruktive oder externe Aktionen brauchen eine eigene Freigabe.
"""


def abschnitt_regeln() -> str:
    return _zeile("4. KONVENTIONEN") + """
1. Belege Aussagen mit aktuellem Code, Tests, ADRs oder Run-Events.
   Vermutungen klar als Hypothese kennzeichnen.

2. Lies vor Aenderungen die betroffenen ADRs, STATUS und ROADMAP.
   Akzeptierte ADRs sind bindend; proposed ADRs muessen erst entschieden
   werden.

3. docs/STATUS.md enthaelt nur offene, aktuelle und startbare OPs.
   Erledigte Arbeit nach PROGRESS.md; entfernte Pfade in die Delete-Zone
   nach docs/DOC_CONVENTIONS.md §5.

4. Aenderungen durchlaufen die im Repository konfigurierte Verify-Kette.
   Dokumentiere fachliche Aenderungen direkt in derselben Arbeitseinheit.
   Fuehre keine nicht angeforderten Tests aus; bei explizitem Verify-Auftrag
   nenne Befehle und Resultate genau.

5. Der Mensch entscheidet an den verpflichtenden Gates. Kein
   Auto-Approve, kein stilles Erweitern des Auftrags, keine Freigabe eines
   anderen Patches als des angezeigten.

6. Bei Queue-Bereinigung: konkrete, weiterverfolgte Ziele behalten;
   abgeschlossene oder ersetzte OPs in PROGRESS dokumentieren; spekulative
   und weit entfernte Vorhaben nicht als startbare STATUS-Eintraege fuehren.

7. STATUS, ROADMAP, PROGRESS und ADRs haben unterschiedliche Rollen:
   - STATUS: aktuelle offene Arbeitsauftraege.
   - ROADMAP: Reihenfolge, Fokus und spaetere Phasen.
   - PROGRESS: append-only Verlauf abgeschlossener oder verworfener Arbeit.
   - ADRs: begruendete Architekturentscheidungen und deren Status.

8. Bei Projekt- und Repo-Wechsel immer Pfad, Projekt und Branch/Commit
   verifizieren. Keine Annahme aus einem frueheren Projekt uebertragen.
"""


def abschnitt_merkposten(max_sektionen: int = 20) -> str:
    """Laedt die letzten N Sektionen aus docs/MERKPOSTEN.md.

    MERKPOSTEN.md ist chronologisch (append-only). Neueste Sektionen
    zuerst ausgeben — die enthalten die aktuellsten Lehren.
    Sektionen werden an '## ' oder '### M-' erkannt.
    """
    try:
        text = MERKPOSTEN.read_text(encoding="utf-8")
    except Exception as e:
        return (_zeile("8. MERKPOSTEN (nicht lesbar)")
                + f"\nMERKPOSTEN.md nicht lesbar: {e}\n")

    teile = re.split(r'\n(?=## |### M-\d)', text)
    sektionen = [s for s in teile if s.strip()]
    sektionen.reverse()
    gewaehlt = sektionen[:max_sektionen]

    out = _zeile(
        f"8. MERKPOSTEN (letzte {len(gewaehlt)} von "
        f"{len(sektionen)} Sektionen aus docs/MERKPOSTEN.md)"
    )
    out += (
        "\nQuelle: docs/MERKPOSTEN.md — chronologisch, neueste zuerst."
        "\nVollstaendig lesbar bei Bedarf mit:  less docs/MERKPOSTEN.md\n\n"
    )
    for s in gewaehlt:
        out += s.rstrip() + "\n\n"
    return out



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

    # test_shell.py laeuft komplett mit. Die 3 PTY-Tests sind
    # mit @pytest.mark.skip markiert (W36-RP-Guard) und skippen
    # sich selbst; 2 normale Tests laufen gruen. Kein --ignore
    # mehr, damit die Kontext-Zahl (1285/8) zur direkten
    # `pytest -q`-Ausgabe passt.
    rc, tests = _run(
        ["python3", "-m", "pytest", "-q"], timeout=180)
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
    except Exception as e:
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
    except Exception as e:
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
    return _zeile("9. DEINE ERSTE AUFGABE (neuer Chat)") + """
Du bist Ansprechpartner fuer das aktive Projekt und arbeitest mit dem
verfuegbaren Repository-Zugriff.

  1. Lies den Auftrag, AGENTS.md, die relevanten akzeptierten ADRs,
     docs/ROADMAP.md und docs/STATUS.md.
  2. Untersuche Repo und Belege selbst; nenne Pfade, Zeilen, Tests und
     Run-IDs statt um bereits verfuegbare Ausgaben zu bitten.
  3. Frage nur nach fehlenden Anforderungen oder einer erforderlichen
     menschlichen Gate-Entscheidung.
  4. Arbeite den bestaetigten Umfang strukturiert ab, halte den Nutzer
     ueber laengere Hintergrundarbeit informiert und beantworte neue
     Fragen parallel, sofern dadurch kein aktiver Plan veraendert wird.
  5. Vor einer schreibenden Aktion beschreibe genau den Patch-Umfang und
     hole die dafuer vorgesehene Freigabe ein.
  6. Dokumentiere fachliche Aenderungen direkt. Berichte Tests, Commit,
     ungelöste Punkte und den naechsten sinnvollen Schritt.

Belege waertliche Zitate und konkrete Zeilenangaben direkt aus dem Repo.
Wenn ein benoetigter Zugriff fehlt, sage welchen und gib einen gezielten
Befehl fuer genau diesen Schritt aus.
"""

# ============================================================
# Main
# ============================================================

def sammle_alles(nur_zustand: bool = False) -> str:
    if nur_zustand:
        return abschnitt_zustand()
    return "\n".join([
        "WERKSTATT KONTEXT-BLOCK — bitte komplett in den Chat pasten",
        "(Statischer Teil: Werkstatt, Rollen, Workflow, Konventionen)",
        "(Dynamischer Teil: Zustand, Commits, OPs, Merkposten)",
        "(dieser Block ist Startkontext; aktuelle Informationen werden",
        " anschliessend direkt aus Repo, ADRs und Status geprueft)",
        abschnitt_identitaet(),
        abschnitt_rollen(),
        abschnitt_workflow(),
        abschnitt_regeln(),
        abschnitt_zustand(),
        abschnitt_commits(10),
        abschnitt_naechste_ops(),
        abschnitt_merkposten(),
        abschnitt_erste_aufgabe(),
    ])



def sammle_json() -> dict:
    _, head = _run(["git", "log", "--oneline", "-1"])
    _, wc = _run(["git", "status", "--short"])
    ops_count = 0
    try:
        text = STATUS.read_text()
        ops_count = len(re.findall(r"^### OP-", text, re.MULTILINE))
    except Exception:
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
