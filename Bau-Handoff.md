# Bau-Handoff — Werkstatt

Stand: 2026-10-12
Letzter Commit: 6db3c4a
Branch: main
Tests: 94 passed
ruff: 0
mypy: 0

Dieses Dokument ist der Einstiegspunkt fuer einen neuen
Bau-Chat. Es enthaelt alles zum Weiterbauen. Es ist ein
Arbeitsdokument und wird bei jedem Meilenstein aktualisiert.

================================================================
1. WAS DIE WERKSTATT IST
================================================================

Die Werkstatt ist ein Agenten-System. Sie baut Projekte, ist
aber selbst kein Teil eines Projekts. Aktuell baut sie
Homelab Security AI, kann aber jedes Projekt bauen.

Verzeichnis: /opt/werkstatt/
Projekt-Konfigurationen: /opt/werkstatt/projects/
Rollen: /opt/werkstatt/agents/
Tests: /opt/werkstatt/tests/

5 Rollen:
  - reviewer (LLM): hoechster Entscheidungstraeger.
  - builder (LLM): baut Code-Entwuerfe, Commit-Paket.
  - test_generator (LLM): liefert Test-Vorschlaege.
  - coverage (No-LLM): misst Coverage.
  - chaos (No-LLM): fuzzt Extremwerte.

Ablauf pro Block:
  1. Basis-Gate (py_compile, ruff, mypy, test_count,
     git_status, git_head) laeuft immer. Hard Fail bei Rot.
  2. Auto-Repair (deterministisch): ruff --fix, ruff format.
  3. Reviewer waehlt optionale Messungen (COMMAND-Zeilen).
  4. Builder baut Code-Entwurf.
  5. Review-Schleife: GO / NO-GO / ESKALATION.
  6. Coverage, ggf. Test-Generator, Chaos.
  7. Commit-Review (zweite Reviewer-Phase).
  8. Approval-Dokument + Human-Gate.
  9. Commit (nur bei approve), Autor ghxstfocus.

================================================================
2. AKTUELLER ZUSTAND
================================================================

Commits (neueste zuerst):
  6db3c4a auflage: 2072 (IPv6-Regex erweitern)
  a58e0b7 auflage: 2062 (Tests check_tests_dir)
  e05c632 auflage: 2061 (Tests apply_commit)
  63673eb auflage: 2060 (Tests execute_commands)
  792b4b2 auflage: 2051 (Budget-Check)
  944be26 auflagen: 2048 + 2049
  b765abb auflage: 2045 (BISHERIGE RUNDEN)
  1d579f5 auflage: 2044 (Redaction-Tests)
  9d1679d auflage: 2043 (CURRENT_PROJECT)
  bcae013 auflagen: 2074 + 2075
  25c934e initial: Werkstatt aufgesetzt

Reviewer-Runden:
  Runde 1: NO-GO. 16 Auflagen (2027-2042).
  Runde 2: NO-GO. 21 Befunde, 17 Auflagen (2076-2092).
           Alle 12 kritischen Auflagen aus Runde 1
           bestaetigt. Zwei neue kritisch: 2082, 2086.

Verifikation letzter Stand:
  - ruff check: 0.
  - mypy: 0.
  - pytest tests/: 94 passed.

Dateien:
  - /opt/werkstatt/pipeline.py (~1400 Zeilen)
  - /opt/werkstatt/redaction.py (~300 Zeilen)
  - /opt/werkstatt/agents/*.md (5 Rollen)
  - /opt/werkstatt/projects/security-ai.yaml
  - /opt/werkstatt/tests/test_pipeline.py (~700 Zeilen)
  - /opt/werkstatt/tests/test_redaction.py (~220 Zeilen)
  - /opt/werkstatt/README.md

================================================================
3. OFFENE AUFLAGEN
================================================================

KRITISCH (vor naechstem Werkstatt-Lauf):

  2082. apply_commit_and_doku: Rollback-Semantik fuer
        Doku-Patches. Wenn Doku-Patch erfolgreich, aber
        Datei-Liste danach fehlschlaegt, bleibt Aenderung
        im Working Tree. Kategorie 3. Befund N23.

  2086. subprocess.run erbt Env: DEEPSEEK_API_KEY landet
        in Umgebung von pytest, ruff, mypy.
        Kategorie 3. Befund N28.

WICHTIG:

  2069. agent_docs.reviewer um "context". Kategorie 1.
  2076. run_measurement + _mit_argv zusammenfuehren. K2.
  2077. classify_verdict: Sonderzeichen. Kategorie 2.
  2078. Budget-Check in Review-Schleife entdoppeln. K2.
  2079. Budget-Check vor Commit-Review: Recovery. K2.
  2081. BudgetExhausted-Recovery konsistent. K2.
  2083. Recovery-Entscheidungen auditieren. K2.
  2084. RecoveryVorschlag: frage_an_menschen. K2.
  2085. getpass.getuser() try/except. K2.
  2087. ask_llm: 1-2 Retries mit Backoff. K2.
  2089. max_len System-Prompt auf 100_000. K2.
  2090. README: Satz zu HR-Regeln korrigieren. K1.
  2092. security-ai.yaml: pre_check_stage / escalation /
        reject_path implementieren oder markieren. K1.

MITTEL:

  2046 (durch 2084), 2052 (durch 2087), 2053 (durch 2086),
  2057, 2059, 2064, 2065, 2066, 2067 (durch 2075),
  2070, 2071, 2073, 2080, 2088, 2091.

================================================================
4. NACHSTE SCHRITTE
================================================================

Empfohlene Reihenfolge:

  1. Auflage 2082 (Rollback-Semantik). Kategorie 3.
  2. Auflage 2086 (Env-Leak). Kategorie 3.
  3. Auflage 2069 (agent_docs.reviewer). Kategorie 1.
  4. Auflage 2090 (README). Kategorie 1.
  5. Auflage 2076 (run_measurement konsolidieren). K2.
  6. Auflage 2077 (classify_verdict). K2.
  ... dann die uebrigen wichtigen, dann die mittleren.

Nach jeder Auflage:
  - ruff, mypy, pytest pruefen.
  - Commit mit Beschreibung.
  - Bei Kategorie 3: Reviewer-Block vor Commit.

Nach allen kritischen und wichtigen Auflagen:
  - Neuer Reviewer-Block.
  - Bei GO: Werkstatt produktionsreif.

================================================================
5. WIE MAN WEITERARBEITET
================================================================

Regeln fuer jeden Bau-Block:

1. Faktenlage vor Meinung. Keine Datei-Inhalte annehmen.
   Immer cat/sed/grep zum Messen.

2. Patch per Python-Skript mit assert count == 1.
   Kein sed auf Python-Code. Kein Heredoc >3 KB.

3. Nach jedem Patch: wc -l, py_compile, ruff, mypy, pytest.

4. Vor jedem Commit: git status --porcelain pruefen.

5. Commit-Autor immer ghxstfocus <ghxst.focus@gmail.com>.

6. Bei Kategorie 3: Reviewer-Block vor Commit.

7. Nach jedem Meilenstein: dieses Handoff aktualisieren.

8. Reviewer-Blocks in Codeblock. Bei >30 KB aufteilen.

9. Kein scope creep. Jede Auflage als eigener Block.

10. Am Ende jeder Session: git status sauber, dieses
    Handoff aktuell.

================================================================
6. WAS DER REVIEWER ZULETZT GESAGT HAT
================================================================

Runde 2, finale Fassung:

  "12 von 12 kritischen Auflagen erfuellt."
  "21 neue Befunde, davon 2 Kategorie 3."
  "Kein Architektur-Blocker."
  "Die Werkstatt ist auf einem guten Weg, aber noch
   nicht produktionsreif."
  "Die zwei kritischen Auflagen (2082, 2086) koennen
   echten Schaden anrichten."
  "Nach den kritischen und wichtigen Fixes: erneuter
   Reviewer-Block."

Fehlalarm zurueckgezogen: Befund N25 (print_approval_
dokument). Der Code gibt die Commit-Message vollstaendig
aus. HR-R7: korrigiert, kein Befund.

================================================================
7. WERKZEUGE UND BEFEHLE
================================================================

ruff:   /opt/security-ai/.venv/bin/python3 -m ruff check ...
mypy:   /opt/security-ai/.venv/bin/python3 -m mypy ...
pytest (aus /opt/werkstatt):
        /opt/security-ai/.venv/bin/python3 -m pytest tests/ -q

Git-Commit mit Autor:
  git -c user.name="ghxstfocus" \
      -c user.email="ghxst.focus@gmail.com" \
      commit -F /tmp/msg.txt

Reviewer-Block nach Kategorie 3:
  Datei in /tmp/ schreiben, mit cat anzeigen,
  in Reviewer-Chat kopieren.

================================================================
8. GIT-STATUS
================================================================

Repo: /opt/werkstatt/.git
Branch: main
Remote: noch nicht gesetzt. Push nach GitHub offen.
.gitignore: Cache, .venv, audit, approvals/*.db, *.env.

Aktueller HEAD: 6db3c4a

================================================================
9. HARD RULES (HR1-HR10)
================================================================

Diese Regeln sind in pipeline.py als Konstante HARD_RULES
definiert. Sie werden jedem System-Prompt (Reviewer,
Builder, Test-Generator) angehaengt. Code, nicht Prompt.

HR1. Faktenlage vor Meinung.
     Keine API aus dem Gedaechtnis. Keine Datei-Inhalte
     annehmen. Keine Zahlen schaetzen. Immer messen.

HR2. Ein Ausfuehrungsblock pro logischer Einheit.
     Kein Vorab-Stapeln mehrerer unabhaengiger Bloecke.

HR3. Vor cat > auf eine angeblich neue Datei:
     git ls-files <pfad> UND git status --porcelain.

HR4. Nach jedem Patch einer bestehenden Datei:
     assert text.count(anker) == 1.
     Bei count != 1: STOP.

HR5. Nach jedem Patch, der Tests betrifft:
     pytest --collect-only -q <datei> VOR pytest -q.

HR6. git status --porcelain zeigt M bei einer Datei,
     die als "neu" angekuendigt war: STOP.

HR7. Kategorie 3 (Auth, RBAC, CSP, Secrets, SQL,
     Input-Validierung, Output-Escaping, DB-Schema,
     Audit, Kern-Services): Code VOR Ausfuehrung an
     den Reviewer. Kein Improvisieren nach NO-GO.

HR8. Doku-Pflege ist Pflicht.
     Ein Commit ohne Doku-Nachzug ist unvollstaendig.

HR9. Patch-Skripte > ~3 KB in /tmp schreiben, dort
     verifizieren, dann ausfuehren. Kein Heredoc in
     die interaktive Shell.
     Anker-Messung Pflicht: Anker IM Patch-Skript
     ermitteln, nicht im Chat aus grep/wc ableiten.

HR10. Nach jedem Block: Update an den Menschen
      (HEAD, Testzahl, was erledigt, offene Punkte).

================================================================
10. HARD RULES FUER DEN REVIEWER-CHAT (HR-R1 bis HR-R10)
================================================================

Aus dem Security-AI-Projekt uebernommen. Projektunabhaengig.

HR-R1. Faktenlage vor Meinung.
       Keine Zahl aus dem Gedaechtnis. Bei ruff/Config/
       API-Fragen: erst messen lassen, dann Auflage.

HR-R2. Bestandsaufnahme vor Reviewer-Block.
       Kein Auflagen-Paket ohne gemessene Fakten.

HR-R3. Auflagen-Nummern global fortlaufend.
       Vor jeder Runde pruefen. Kein doppeltes Vergeben.

HR-R4. Reviewer-Blocks immer in einen Codeblock.

HR-R5. Kategorie 3 nur mit vorherigem Reviewer-Block.
       Kein Code ohne GO.

HR-R6. Wenn du unsicher bist: ESKALATION. Nicht raten.

HR-R7. Fehler anerkennen, korrigieren, dokumentieren.
       Nicht relativieren.

HR-R8. Kein Scope-Creep. "Mal eben" etwas mitnehmen:
       STOP, eigener Block.

HR-R9. Fail-closed. Wenn eine Pruefung nicht moeglich
       ist: blockieren, nicht durchlassen.

HR-R10. Kein "das haben wir schon immer so gemacht".
        Jede Auflage hat einen Grund. Wenn der Grund
        nicht mehr gilt: Auflage zurueckziehen.

================================================================
11. ANTWORTFORMATE DES REVIEWERS
================================================================

GO:
    GO
    Grund: <kurz>
    Bemerkung: <optional>

NO-GO:
    NO-GO
    Grund: <konkreter Punkt>
    Empfehlung: <wie richtig>
    Verweis: <Design-Entscheidung / Doc>

ESKALATION:
    ESKALATION
    Frage: <was>
    Warum: <warum unsicher>
    Vorschlag: <was du empfiehlst>

================================================================
ENDE DES HANDOFFS
================================================================
