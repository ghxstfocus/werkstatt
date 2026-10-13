# Bau-Handoff — Werkstatt

Stand: 2026-10-13 (nach Probebetrieb 45)
Werkstatt-HEAD: 7eaad9f (Tag probebetrieb-45)
Letzter Commit in security-ai: 3ccb883
Branch: main
Tests: 270 passed
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
Doku: /opt/werkstatt/docs/
  - WORKFLOW.md (Regeln, Anti-Patterns, Merkposten)
  - ROADMAP.md (offene Architektur-Ideen)
  - PROTOKOLL-29-40.md (Beobachtungs-Protokoll der
    Probebetriebe 29 bis 40)

Rollen (5):
  - reviewer (LLM, deepseek-reasoner): prueft Patches
    und Commit-Paket, entscheidet GO/NO-GO/ESKALATION.
  - builder (LLM, deepseek-chat): liefert strukturierte
    Code-Patches (PATCH-BEGINN/ENDE) und das Commit-Paket.
  - test_generator (LLM): liefert Test-Vorschlaege.
  - coverage (No-LLM): misst Coverage.
  - chaos (No-LLM): fuzzt Extremwerte.

================================================================
2. AKTUELLER ZUSTAND
================================================================

Werkstatt-Repo:
  HEAD 7eaad9f (probebetrieb-45)
  Tests: 270 passed
  ruff: 0, mypy: 0, git status sauber
  Remote: github.com/ghxstfocus/werkstatt.git (privat)

Ziel-Projekt security-ai:
  HEAD 3ccb883 (Traceroute-Binary-Fehler-Fall)
  Vorgaenger dd3048b (PingError-Fall, erster Werkstatt-Commit)
  git status sauber

Werkstatt-Tags (auf /opt/werkstatt):
  probebetrieb-7, -17, -29 bis -45

Ziel-Projekt-Tags (auf /opt/security-ai):
  probebetrieb-1 bis -28 (historisch, vor dieser Session)
  Der zweite Commit (3ccb883) hat keinen Tag bekommen
  (Werkstatt-Konvention: nur Werkstatt-Repo wird getaggt).

Dateien:
  - pipeline.py (2876 Zeilen, Stand 2191-R)
  - redaction.py (314 Zeilen, Stand 2195)
  - agents/*.md (5 Rollen)
  - projects/security-ai.yaml
  - tests/test_pipeline.py (3509 Zeilen, Stand 2191-R)
  - tests/test_redaction.py
  - docs/WORKFLOW.md
  - docs/ROADMAP.md
  - docs/PROTOKOLL-29-40.md
  - README.md

================================================================
3. WAS SEIT DEM LETZTEN HANDOFF PASSIERT IST
================================================================

Das Handoff vom 2026-10-12 (gesichert als
Bau-Handoff-2026-10-12.md.alt) ist veraltet. Es
beschreibt einen Stand vor den Auflagen 2027-2094
und vor UMB-1.

Seitdem:
  A) Auflagen 2027-2094 (16 kritische + 21 Befunde).
  B) UMB-1 (Architektur-Umbau, 4 Teile).
  C) Probebetriebe 1-28 (vor dieser Session).
  D) Auflagen 2186-2198 (diese Session).
  E) Zwei erfolgreiche Werkstatt-Commits in security-ai:
     dd3048b (PingError) und 3ccb883 (Traceroute).

================================================================
4. DIE 12 PROBEBETRIEBE DIESER SESSION (29-40)
================================================================

Ausfuehrliches Protokoll: siehe docs/PROTOKOLL-29-40.md.

Kurzfassung:
  PB-29: Fail (Anker 0x). Ausschnitt-Bug entdeckt.
  PB-30: Fail (Livelock, 5x NO-GO). COMMAND-Loop fehlt.
  PB-31: Fail (Anker 0x). Prompt einmal gebaut.
  PB-32: Fail (builder_command_deadlock).
  PB-33: Fail (Anker 0x). read_file ignoriert.
  PB-34: Fail (Anker 0x). GEMESSENER INHALT fehlt.
  PB-35: Fail (Anker 0x). GEMESSENER INHALT ignoriert.
  PB-36: Fail (Anker 0x). Automatik + GEMESSENER INHALT
         greifen nicht.
  PB-37: Fail (Anker 0x). Audit-Debug zeigt: IP-Redaction
         zerstoert Anker. WURZEL GEFUNDEN.
  PB-38: Fail (Commit-NO-GO). Anker trifft! Testzahl fehlt.
  PB-39: Fail (Commit-NO-GO). Rechte-Problem + Testzahl.
  PB-40: ERFOLG. Commit 3ccb883 in security-ai.
  PB-41: Doku. Handoff + Protokoll 29-40 neu.
  PB-42: Chore. .gitignore um *.alt ergaenzt.
  PB-43: ERFOLG. Auflage 2191-R. HEAD 87092f8.
  PB-44: Doku. Handoff auf PB-43-Stand.
  PB-45: Style. ruff I001 in tests/ behoben.

Auflagen dieser Session:
  2186: KUERZUNGS-MARKER
  2187: Builder-COMMAND-Loop
  2188: builder.md KUERZUNGS-MARKER respektieren
  2189: Pfad-Woertlichkeit + Fehler-Marker
  2190: GEMESSENER INHALT als primaere Quelle
  2191: Prompt pro Runde frisch
  2192: Werkstatt messt automatisch
  2193: zurueckgezogen (Modellwechsel)
  2194: Audit-Debug (Diagnose)
  2195: Private IPs nicht mehr redigieren (WURZEL)
  2196: collect_messwerte bevorzugt nach-apply
  2197: Fail-closed-Rollback
  2198: collect_messwerte-Regex an Kuerzung

================================================================
5. OFFENE AUFLAGEN UND MERKPOSTEN
================================================================

KRITISCH: keine.

WICHTIG (naechste Session):
  2191-R2: Phase 2 (Commit-Review) bekommt keinen
           GEMESSENER INHALT (commit_input, Zeile
           2617 ff.). Reviewer kann Anker im Commit
           nicht gegen Messung pruefen.
           Kategorie 3.

  2194-M: Audit-Debug-Felder reduzieren. Die Felder
          builder_prompt_gebaut und builder_reply_erhalten
          wachsen mit jedem Lauf. Nach der Diagnose
          reduzieren.
          Kategorie 2.

  2191-R3: agents/reviewer.md Body-Regel 2 (Zeile 30-33)
           fordert "woertlich" ohne Toleranzstufen.
           Nach PB-43 pruefen, ob Widerspruch zu R7.
           Kategorie 2.

  2191-R4: Builder-Prompt (Zeile 2344) hat GEMESSENER
           INHALT nach ZIELDATEIEN. Reviewer-Prompt
           (Zeile 2424) hat ihn jetzt davor. Inkonsistenz
           bewusst? Kategorie 2.

  2199: PB-43 messen: greift R7 tatsaechlich?
        Wenn nein, Ursache nicht Reihenfolge/Regel-
        quelle, sondern Modellverhalten -> 2193.
        Kategorie 3.

  2182b: agents/reviewer.md:193 (HR4) -> (B8). Nach
         2182 entfallen die HR2-HR6-Nummern. Der
         Verweis im Reviewer-Body zeigt auf eine
         nicht mehr existierende Nummer.
         Kategorie 1.

MITTEL (Merkposten):
  2183: Solver-Agent (neue Rolle). Uebersetzt Auftrag
        in praezisen Builder-Auftrag.
        Kategorie 3. Groesserer Umbau.
  2184: max_llm_calls 20 -> 30 (in YAML). Mit 2183.
  2185: README 6 Rollen dokumentieren. Mit 2183.
  2187b: read_file Zeilenbereich (fuer sehr grosse Dateien).
  2188a: agents/*.md konsolidieren (Widersprueche durch
         anhaengende Auflagen).
  2188c, 2189c, 2190b-M, 2191-M2, 2192-M2, 2198-M,
  2198-M2: Merkposten zum "Feature + Prompt +
         Aktualisierung"-Muster. Konsolidieren in eine
         Werkstatt-Regel.
  2190-M: Reviewer-Auswahl-Logik (Schritt 1) pruefen.
  2192-M1: execute_commands prueft, ob Pfad schon
         vollstaendig gemessen.
  2195-M2: MAC-Redaction rechtfertigen oder entfernen.
  2195-M3: Anker mit gemischten privaten/oeffentlichen IPs.

NIEDRIG:
  Audit-Log-Ausbau dauerhaft (statt Debug-Felder).
  Tag-Verwirrung: Ziel-Repo-Tags 2, 20-24 auf
  f913eac, 25-28 auf dd3048b. Werkstatt-Tags 7,
  17, 29-43. Vereinheitlichen.

================================================================
6. WIE MAN WEITERARBEITET
================================================================

Regeln fuer jeden Bau-Block:

1. Faktenlage vor Meinung. Keine Datei-Inhalte
   annehmen. Immer cat/sed/grep zum Messen.

2. Patch per Python-Skript mit assert count == 1.
   Kein sed auf Python-Code. Kein Heredoc >3 KB.

3. Nach jedem Patch: wc -l, py_compile, ruff,
   mypy, pytest.

4. Vor jedem Commit: git status --porcelain
   pruefen.

5. Commit-Autor immer ghxstfocus
   <ghxst.focus@gmail.com>.

6. Bei Kategorie 3: Reviewer-Block vor Commit.

7. Nach jedem Meilenstein: dieses Handoff
   aktualisieren.

8. Reviewer-Blocks in Codeblock.

9. Kein Scope-Creep. Jede Auflage als eigener
   Block.

10. Am Ende jeder Session: git status sauber,
    dieses Handoff aktuell.

Reviewer-Chat:
  - Der Reviewer-Chat ist ein separater
    Web-Chat (nicht der Bau-Chat).
  - Kategorie 3: Code VOR Ausfuehrung an
    den Reviewer.
  - Kein Improvisieren nach NO-GO.

================================================================
7. WERKZEUGE UND BEFEHLE
================================================================

ruff:   /opt/security-ai/.venv/bin/python3 -m ruff check ...
mypy:   /opt/security-ai/.venv/bin/python3 -m mypy ...
pytest (aus /opt/werkstatt):
        /opt/security-ai/.venv/bin/python3 -m pytest tests/ -q

Werkstatt-Lauf (aus /opt/security-ai als builder):
  set -a
  . /opt/security-ai/.env
  set +a
  cd /opt/security-ai && \
  runuser -u builder -- env DEEPSEEK_API_KEY="$DEEPSEEK_API_KEY" \
    /opt/security-ai/.venv/bin/python3 \
    /opt/werkstatt/pipeline.py \
    --project security-ai \
    "<Block-Auftrag>"
  unset DEEPSEEK_API_KEY

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

Werkstatt-Repo: /opt/werkstatt/.git
  Branch: main
  Remote: git@github.com:ghxstfocus/werkstatt.git
  .gitignore: Cache, .venv, audit-logs/,
              approvals/*.db, *.env.

Ziel-Projekt (security-ai):
  Repo: /opt/security-ai/.git
  Erster Werkstatt-Commit: dd3048b
  Zweiter Werkstatt-Commit: 3ccb883

Hinweis: Der Werkstatt-Lauf benoetigt Schreibrechte
des builder-Users im Ziel-Projekt. Nach manuellen
git-Eingriffen als root: chown builder:builder pruefen.

================================================================
9. HARD RULES (HR1-HR10)
================================================================

Seit Auflage 2182 sind die HARD_RULES rollenspezifisch
getrennt:
  - HARD_RULES_BASE (universell: HR1, HR7, HR8, HR9, HR10).
  - HARD_RULES_REVIEWER (R1-R6).
  - HARD_RULES_BUILDER (B1-B10).
  - HARD_RULES_TEST_GENERATOR (T1-T4).
build_system_prompt waehlt anhand des Agent-Namens.

HR2-HR6 sind entfallen. Ihre Inhalte stehen in B6-B9.

B4 (wichtig): "Du bist kein Messender. Die Werkstatt
ist der Messende." Wird seit Auflage 2192 durch
ensure_ziel_gemessen automatisch durchgesetzt.

================================================================
10. HARD RULES FUER DEN REVIEWER-CHAT (HR-R1 bis HR-R10)
================================================================

Unveraendert. Siehe vorherige Handoff-Version
(Bau-Handoff-2026-10-12.md.alt, Abschnitt 10).

HR-R1. Faktenlage vor Meinung.
HR-R2. Bestandsaufnahme vor Reviewer-Block.
HR-R3. Auflagen-Nummern global fortlaufend.
HR-R4. Reviewer-Blocks immer in einen Codeblock.
HR-R5. Kategorie 3 nur mit vorherigem Reviewer-Block.
HR-R6. Wenn unsicher: ESKALATION.
HR-R7. Fehler anerkennen, korrigieren, dokumentieren.
HR-R8. Kein Scope-Creep.
HR-R9. Fail-closed.
HR-R10. Kein "das haben wir schon immer so gemacht".

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
12. NAEECHSTE SCHRITTE (konkret)
================================================================

Der neue Bau-Chat soll:

1. Diesen Handoff lesen. HEAD pruefen:
     git -C /opt/werkstatt log -1 --oneline
     git -C /opt/werkstatt status --porcelain
     /opt/security-ai/.venv/bin/python3 -m pytest \
       /opt/werkstatt/tests/ -q

2. docs/PROTOKOLL-29-40.md lesen.

3. Naechsten Block waehlen:
   Empfehlung: 2191-R (Reviewer prueft gegen
   GEMESSENER INHALT). Danach 2194-M (Audit-Debug
   reduzieren). Danach 2182b (Reviewer-Body).

4. Fuer 2191-R einen Kategorie-3-Reviewer-Block
   formulieren. Vor Ausfuehrung.

5. Nach Erfolg: git tag probebetrieb-41.

6. Bei Problemen: zurueck zu diesem Handoff,
   Faktenlage pruefen, Reviewer-Chat fragen.

================================================================
ENDE DES HANDOFFS
================================================================
