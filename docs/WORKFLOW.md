# Werkstatt — Workflow

Regeln fuer die Entwicklung der Werkstatt selbst.
Nicht zu verwechseln mit den HR-Regeln der Agenten
(die stehen in pipeline.py als HARD_RULES_BASE
und rollenspezifische HARD_RULES_<ROLLE>).

## Anti-Patterns

### Anker in Dekorator-Kette

Bei Patch-Ankern auf Klassen mit Dekorator
(@dataclass, @functools.*, @app.route) muss der
Dekorator in den Anker aufgenommen werden.

Falsch:

    "class Measurement:"

    -> Patch kann zwischen Dekorator und Klasse
       eingefuegt werden.

Richtig:

    "@dataclass(frozen=True)
     class Measurement:"

    -> Patch kann nicht mitten in die
       Dekorator-Kette greifen.

Anlass: Werkstatt-Auflage 2086, 2026-10-12.

### Patch-Anker ohne Semantik-Pruefung

Ein Anker kann syntaktisch eindeutig (count == 1)
und semantisch falsch sein.

Regel: Bei jedem Anker pruefen, ob er semantisch
zusammenhangende Einheiten trifft. Bei Klassen mit
Dekorator gehoert der Dekorator dazu. Bei
Funktionsbloecken gehoeren Docstring und Signatur
zusammen.

Anlass: Werkstatt-Auflage 2086, 2026-10-12.

## Patch-Konventionen

### Anker-Wahl

- Anker muessen syntaktisch eindeutig (count == 1)
  UND semantisch zusammenhaengend sein.
- Bei mehrzeiligen Ankern: die volle Struktur
  aufnehmen (Dekorator, Signatur, Docstring-Anfang).
- Kein Anker, der nur zufaellig eindeutig ist.

### Patch-Skripte

- Patch-Skripte immer in /tmp/ schreiben.
- Anker im Skript messen (`text.count(alt)`),
  nie im Chat aus grep/wc ableiten.
- Bei `count != 1`: Skript bricht ab, keine
  Schreiboperation.
- Nach jedem Patch: py_compile, ruff, mypy,
  pytest.

### Tests gegen pipeline.py

Merkposten 2183-B3-1:
  Vor dem Schreiben neuer Test-Funktionen den
  Import-Stil der bestehenden Tests messen:
    grep -n '^import pipeline\|^from pipeline' \
      tests/test_pipeline.py
  tests/test_pipeline.py nutzt 'import pipeline'
  und qualifizierte Aufrufe (z.B.
  pipeline.build_system_prompt), keine
  Direkt-Importe. Unqualifizierte Aufrufe
  fuehren zu F821 (ruff), bevor pytest sie
  faengt.
  Erkannt in 2183 Block 3 (Commit d706e66),
  durch ruff gefangen, vor Commit korrigiert.

### Commit-Konventionen

- Ein Commit pro Auflage, ausser thematisch
  verwandte Auflagen (Gruppen).
- Kategorie 3 (Auth, RBAC, Secrets, Parser,
  Kern-Services): Reviewer-Block vor Commit.
- Commit-Autor: ghxstfocus <ghxst.focus@gmail.com>.

## Kategorien

- Kategorie 1: Doku/Config. Kein Reviewer-Block
  vor Commit.
- Kategorie 2: Code-Hygiene, Tests, Robustheit.
  Kein Reviewer-Block noetig, aber Tests Pflicht.
- Kategorie 3: Auth, RBAC, CSP, Secrets, SQL,
  Input-Validierung, Output-Escaping, DB-Schema,
  Audit, Kern-Services, Parser. Reviewer-Block
  vor Commit.

## Feature + Prompt

Ein Werkstatt-Feature ist erst wirksam, wenn der
Agent es kennt. Code allein reicht nicht.

Regel: Jedes neue Feature wird als Paar
ausgeliefert.

  - Code: die Mechanik (z.B. KUERZUNGS-MARKER
    in pipeline.py, Auflage 2186).
  - Prompt: die Anweisung an den Agenten, die
    Mechanik zu nutzen (z.B. Abschnitt
    KUERZUNGS-MARKER in agents/builder.md,
    Auflage 2188).

Beispiele aus der Historie:
  - 2135 + 2168 (Messwerte).
  - 2146 + 2175 (Zieldatei-Ausschnitte).
  - 2178 + 2180 (MESSWERTE im Commit-Review).
  - 2186 + 2188 (KUERZUNGS-MARKER).
  - 2189a + 2189b (Pfad-Woertlichkeit:
    Mechanik markiert Fehler, Prompt
    verlangt woertliches Pfad-Zitat).

Pruefung vor jedem Feature (Auflage 2189c):

  1. Was sieht der Agent von der Mechanik?
     (Der Prompt muss den Marker enthalten.)
  2. Was tut der Agent, wenn die Mechanik
     warnt? (Der Prompt muss die Reaktion
     benennen.)
  3. Was tut der Agent bei Fehlern?
     (Der Prompt muss Fehler-Kategorien
     oder Fehler-Reaktion nennen.)

Ohne Code sieht der Agent das Feature nicht.
Ohne Prompt nutzt der Agent es nicht.
Beide Tests sind Pflicht.

## Label-Prioritaeten

Prompt-Labels koennen die Prioritaet von
Kontext-Bloecken setzen.

Beispiele:
  - "GEMESSENER INHALT (verbindlich, gewinnt
    gegen ZIELDATEIEN):"
  - "ZIELDATEIEN (Ausschnitte, Fallback):"

Regeln:
  1. Der Agent braucht eine Rangfolge der
     Quellen. Reine Aufzaehlung mehrerer
     Bloecke ohne Prioritaet fuehrt zu
     willkuerlicher Auswahl (siehe Auflage
     2190).
  2. Der letzte Block vor der Aufgabe wird
     vom LLM am staerksten gewichtet. Die
     wichtigste Quelle gehoert deshalb an
     das Ende.
  3. "verbindlich" und "gewinnt gegen" sind
     starke Marker. Sie sind in den Bodies
     (agents/*.md) zu erklaeren, damit der
     Agent die Labels richtig interpretiert.

Merkposten 2190b-M:
  Bei jedem neuen Prompt-Block mit
  Konflikt-Potenzial: Label mit Prioritaet
  versehen und im Body erklaeren.

## Feature + Prompt + Aktualisierung

Ein Feature braucht drei Teile, nicht zwei.

  1. Mechanik (Code in pipeline.py).
  2. Prompt (Anweisung in agents/*.md).
  3. Aktualisierung pro Runde (Prompt
     wird in jeder Loop-Runde frisch
     gebaut, wenn er Zustand enthaelt).

Beispiel 2190 + 2191:
  2190 = GEMESSENER INHALT als primaere
         Quelle (Mechanik + Prompt).
  2191 = GEMESSENER INHALT pro Runde
         frisch (Aktualisierung).

Ohne Aktualisierung sieht der Agent in
Runde 2 den Zustand aus Runde 1 nicht.
Das ist ein verbreiteter Fehler bei
Loop-Agenten.

Merkposten 2191-M2:
  Bei jedem Feature pruefen, ob der
  Prompt in Schleifen frisch gebaut
  werden muss.

## Werkstatt als Messender

HR1 (Faktenlage vor Meinung) wird von der
Werkstatt ausgefuehrt, nicht vom Agenten.
Der Agent soll nicht entscheiden muessen,
ob er messen muss.

Dreischichtiges Modell:
  1. Zugriff: der Agent KANN messen
     (COMMAND: RUN read_file).
  2. Sichtbarkeit: der Agent SIEHT die
     Messung (GEMESSENER INHALT-Block).
  3. Automatik: die Werkstatt misst selbst,
     wenn die Messung fehlt.

Nur alle drei Schichten zusammen sind
robust. Ohne Schicht 3 entscheidet der
Agent selbst — und entscheidet falsch
(Auflagen 2190-2192).

Grenzen der Automatik:
  - Nur Zieldateien (aus
    extract_paths_from_aufgabe).
  - trim_output greift bei sehr grossen
    Dateien (> 10000 Zeichen).
  - Pfade ausserhalb file_whitelist werden
    abgelehnt.

Merkposten 2192-M2:
  Bei jeder neuen 'Agent soll X'-Regel:
  alle drei Schichten pruefen (Zugriff,
  Sichtbarkeit, Automatik).

## Audit-Debug (temporaer)

Waehrend der Diagnose (Auflage 2194)
protokolliert der Audit-Log:
  - builder_prompt_gebaut: Sektionen,
    Laengen, GEMESSENER INHALT-Laenge.
  - builder_reply_erhalten: Kopf und Fuss
    des Replies.

Merkposten 2194-M:
  Nach der Diagnose die Debug-Felder
  reduzieren oder entfernen. Der Audit
  waechst sonst unbegrenzt.

## Messung-Ausgabe-Formate

Die Ausgabe-Formate der Messungen sind
implizite Schnittstellen zwischen:
  - run_measurement_mit_argv (Erzeuger).
  - collect_messwerte (Konsument).

Wenn ein Format geaendert wird, muessen
alle Konsumenten mitgezogen werden.

Beispiel 2176 -> 2198:
  - 2176 kuerzte test_count auf die letzte
    Zeile mit dem Marker STDOUT (letzte
    Zeile):.
  - 2135 (collect_messwerte) wurde nicht
    mitgezogen -> test_anzahl None.
  - 2198 hat die Regex nachgezogen.

Merkposten 2198-M:
  Messung-Ausgabe-Formate zentral dokumentieren.

Merkposten 2198-M2:
  Bei Format-Aenderung Konsumenten pruefen
  (grep nach dem alten Format-String).

## Fail-closed-Prinzip

Wenn eine Pruefung nicht moeglich ist: blockieren,
nicht durchlassen. Beispiele:

- parse_commit_paket: ungueltiger Patch -> verworfen.
- require_budget: Budget erschoepft -> Stop.
- subprocess_env: Secrets werden nicht durchgereicht.
- redact_text: max_len zu klein -> ValueError.

## Block-Auftraege

Ein Block-Auftrag an die Werkstatt muss vier Angaben
enthalten:

1. Anker: exakter Text aus der Zieldatei, oder
   Messung, die den Anker liefert.
2. Zieltext: der neue Text, wortgetreu.
3. Bezug: welcher offene Punkt (Nummer), oder
   welche Fundstelle.
4. Kategorie: 1/2/3.

Ohne diese vier Angaben ist der Auftrag unterbestimmt.
Der Reviewer-Agent wird NO-GO oder ESKALATION geben.

### Wer formuliert was

- Der Mensch formuliert den Auftrag.
- Der Builder kann den Anker messen, aber den
  Zieltext nicht erfinden (HR1: Faktenlage vor
  Meinung).
- Konkret: der Mensch gibt Zieltext, Bezug,
  Kategorie. Der Builder kann den Anker liefern,
  wenn der Mensch nur "die Datei X" nennt und
  den Zieltext vorgibt.

### Beispiele

Beispiel (gut):

    Anker: letzte Zeile in docs/INCONSISTENCIES_FOUND.md
           lautet '<X>'.
    Zieltext: "## Neue Inkonsistenz\n<Text>"
    Bezug: offener Punkt 88.
    Kategorie: 1.

Beispiel (schlecht):

    "Ergaenze einen Absatz in der Datei."

    Fehlt: Anker, Zieltext, Bezug, Kategorie.
    Der Reviewer-Agent kann das nicht bewerten.

### Bugfix-Auftraege

Auch Bugfix-Auftraege fallen unter die Konvention:

- Zieltext = neuer Code-Zustand.
- Anker = problematischer Zustand.

Ausnahme: Auftraege der Kategorie 3 (Reviewer-Block
extern). Dort ist die Review-Pflicht ohnehin
vorgeschaltet.

### IP-Adressen, MACs, Secrets

Block-Auftraege enthalten KEINE konkreten
IP-Adressen, MACs oder Secrets.

Grund: Die Werkstatt schickt den Auftrag durch
die Redaction, bevor er an den Builder geht.
Die Redaction ersetzt jede IP durch [IPV4] oder
[IPV6]. Ein Auftrag mit "192.168.178.1" wuerde
im Builder-Prompt als "[IPV4]" erscheinen —
der Builder kann damit keinen gueltigen
Test-Input mehr bauen.

Statt konkreter IPs:
  - "localhost" (fuer Loopback).
  - Beispiel-IPs aus RFC 5737:
      192.0.2.1 (TEST-NET-1)
      198.51.100.1 (TEST-NET-2)
      203.0.113.1 (TEST-NET-3)
  - Platzhalter, wenn der Wert austauschbar ist.

Fuer MACs: keine konkreten MAC-Adressen.
Wenn ein MAC noetig ist: Platzhalter oder
generischer String.

Fuer Secrets (API-Keys, Tokens, Passwoerter):
nie im Auftrag. Der Auftrag beschreibt, was
gebaut werden soll, nicht den konkreten Wert.

Anlass: Werkstatt-Probebetrieb 22, 2026-10-12.
Der Auftrag verwendete "192.168.178.1" — der
Builder bekam "[IPV4]" und der Test schlug
fehl.

## Verbindlichkeits-Hierarchie

Drei Stufen. Bei Zweifel gilt die restriktivere Auslegung.

1. **Verbindlich (Hard-Rules).** Nicht abdingbar.
   Verstoss = STOP, keine Ausfuehrung. Der Bau-Chat
   prueft diese Regeln VOR jedem Ausfuehrungsblock.
2. **Pflicht (Routine).** Nach jedem Schritt.
   Verstoss = Korrektur im naechsten Block.
   Selbst-Review, Doku-Pflege, Commit-Konventionen.
3. **Empfehlung (Praxis).** Nuetzlich, aber
   situationsabhaengig. Anti-Patterns, Kontext-Hygiene.

## Fakten-Check-Takt

Pro Nachricht genau EIN Ausfuehrungsblock.
Der naechste Block kommt erst, nachdem der Nutzer
die Ausgabe des vorherigen gepastet hat.

Kein Vorab-Stapeln mehrerer Bloecke.
Mehrere Fakten sequenziell klaeren.

Grund: Scroll-Chaos beim Nutzer, doppelte Befehle,
schwer nachvollziehbare Reihenfolge.

Ausnahme: `&&`-verkettete Einheiten in einem Block
sind ok, solange sie zusammen ein Ergebnis liefern
(z. B. Backup + patch + verify).

## Selbst-Review (Pflicht vor jedem Commit)

Vor jedem Commit:

1. `git status --porcelain` pruefen.
2. `git diff` pruefen (was aendert sich wirklich?).
3. Alle Tests gruen (`pytest -q`).
4. ruff sauber (`ruff check . --no-cache`).
5. mypy sauber (rekursiv, P6-Regel).
6. Doku nachgezogen (Feature + Prompt + Aktualisierung).
7. Commit-Message vollstaendig (Ausgangslage,
   Aenderung, Tests, Verifikation, Reviewed).

Ohne diese Punkte kein Commit.

## Verifikations-Reihenfolge

Nach jedem Patch, jede Messung isoliert und in
dieser Reihenfolge:

1. `py_compile` — Syntax.
2. `ruff check --no-cache` — Lint.
3. `mypy` (rekursiv) — Typen.
4. `pytest --collect-only -q <datei>` — Sammelzahl.
5. `pytest -q <datei>` — Tests.
6. `git status --porcelain` — Sauberkeit.
7. `git diff --stat` — Umfang.

Erst wenn alle gruen sind: Commit.

## Umgang mit unklaren Zustaenden

### Abgebrochener Paste

Wenn ein Paste mitten im Befehl abbricht: nicht
weitermachen. Erst `git status --porcelain` messen,
dann entscheiden, ob der halbe Schritt rueckgaengig
gemacht werden muss.

### Widerspruch zwischen Ausgabe und Realitaet

Wenn die Ausgabe etwas anderes zeigt als erwartet:
nicht raten. `cat`, `sed`, `grep` — die Datei
sprechen lassen.

### Phantom-Dateien

Ein Paste mit Sonderzeichen erzeugt manchmal
leere Dateien (0 Byte). Nach jedem Paste:
`git status --porcelain` pruefen. Unbekannte `??`
sofort entfernen mit `rm -- 'name'`.

## Sprache und Format

- Keine Umlaute in Code-Bloecken (oe, ue, ae, ss).
  Grund: Shell-, Python- und Tool-Kompatibilitaet.
- In Kommentaren und Doku: Umlaute erlaubt, aber
  in Code-Bloecken nicht.
- Blockueberschriften mit `##`.
- Status-Icons in ROADMAP/STATUS:
  ✅ abgeschlossen, 🔨 in Arbeit, 💡 geplant,
  ❌ abgebrochen, ⏸ pausiert.

## Was nicht verhandelbar ist

- Fail closed statt Fail open.
- Gemessen statt erinnert.
- Ein Commit pro Block.
- Reviewer-Block vor Kategorie-3-Commits.
- Keine Secrets im Auftrag, in Prompts oder in
  Commit-Messages.
- Keine Phantom-Dateien im Repo.
- Am Ende jeder Session: `git status` sauber,
  Handoff aktuell.

## Kontext-Hygiene

- Pro Nachricht ein Block.
- Kein Copy-Paste aus dem Reviewer-Freitext.
- Nur Codeblock, nicht Begleittext.
- Keine Umlaute in Code.
- Keine mehrzeiligen Heredocs > ~3 KB.

Diese Regeln halten den Chat-Zustand sauber und
reproduzierbar.

## Doku-Pflege (generisch)

Doku-Pflege ist Pflicht. Ein Unterschritt gilt erst
als abgeschlossen, wenn die zugehoerige Doku
nachgezogen ist. Ein Commit ohne Doku-Nachzug ist
unvollstaendig.

Drei Ebenen:

1. **Projekt-Doku** (im Projekt): STATUS, ROADMAP,
   DECISIONS, SECURITY_LOG, CHANGELOG.
2. **Werkstatt-Doku**: WORKFLOW, ROADMAP,
   PROTOKOLL, Bau-Handoff.
3. **Rollen-Doku**: agents/*.md.

Bei Aenderungen pruefen: wer ist Konsument?
(Feature + Prompt + Aktualisierung.)

## Anti-Pattern-Katalog

Die Projekt-Anti-Patterns aus der Praxis sind im
Katalog `anti-patterns/katalog.yaml` (Werkstatt).
Sie werden rollen- und trigger-grund-spezifisch in
die Prompts injiziert. Siehe `anti-patterns/README.md`.

Der Abschnitt `## Anti-Patterns` oben (Zeile 8)
beschreibt nur die zwei Werkstatt-internen
Anti-Patterns (Anker in Dekorator-Kette,
Patch-Anker ohne Semantik-Pruefung).

## Anlass-Historie

- 2026-10-12, Auflage 2086: subprocess_env()
  versehentlich zwischen @dataclass und
  class Measurement eingefuegt. mypy-Fehler.
  Lehre: Dekorator in den Anker aufnehmen.

## Projekt-Schema

Jede Projekt-Konfiguration (projects/<name>.yaml) wird gegen
schemas/projekt.yaml geprueft. Der Validator heisst
pruefe_projekt_yaml in pipeline.py und laeuft beim Laden der
Projekt-Konfiguration.

### Kategorien

  K    = Kern (Pflicht).
  O    = Optional (Default greift).
  P    = Projektspezifisch.
  W+O  = Werkstatt-Default, Projekt-YAML darf ueberschreiben.

### docs vs. agent_docs

  docs.*       sind Doku-Bausteine (Zweck).
  agent_docs.* sind Rollensichten (wer sieht was).

Ein Doku-Baustein kann von mehreren Rollen gesehen werden.
Eine Rolle kann mehrere Bausteine sehen.

Die alte Trennung context vs. handoff stammt aus der
Zwei-Webchat-Aera und ist keine feste Zweistufigkeit.
docs/CONTEXT_PROMPT.md und docs/REVIEWER_HANDOFF.md sind
Uebergangsnamen und werden langfristig durch generierte
Rollen-Prompts ersetzt.

### Alias-Mechanik (Uebergangsphase)

Schluessel-Ebene:
  docs.handoff        -> docs.reviewer
  docs.context_prompt -> docs.context
  agents_dir          -> project_agents_dir

Datei-Ebene (nur Hinweis, nicht erzwungen):
  docs/CONTEXT_PROMPT.md   -> bevorzugt docs/CONTEXT.md
  docs/REVIEWER_HANDOFF.md -> bevorzugt docs/REVIEWER.md

### Modus

Der Validator kennt zwei Modi:
  warn (Default): Meldungen werden gedruckt, die Pipeline laeuft.
  fail: Meldungen fuehren zu sys.exit(2).

Steuerung: Umgebungsvariable WERKSTATT_SCHEMA_MODUS.

Phase 1 ist Warn-Modus. Der Default wird auf fail gestellt,
sobald PB-67 (2026-10-15, Warn-Modus ohne Warnung durchlaufen)
als stabile Basis bestaetigt ist (Phase 1b).

## Phasen-Modus und Planner

Der Phasen-Modus ist die Antwort auf grosse Auftraege, die
sonst in Deadlock oder Livelock enden (P1-Live-Test
2026-10-15). Er zerlegt eine Phase in Unterbloecke, fuehrt
sie sequenziell aus, sammelt die Commit-Pakete und macht
am Ende EINEN Sammel-Commit.

Aufruf:
  pipeline.py --project <name> --phase "<Auftrag>"

Ablauf:
  1. Planner Stufe 2 liefert einen Plan (P10-P14-Format):
     phase_id, phase_titel, phase_unterbloecke
     (mit id, titel, unterpunkte, geschaetzte_runden).
  2. Bestaetigung [j]/[n]/[e]. Bei [j]: Plan wird
     atomar nach projects/<name>.phase.yaml geschrieben
     (mode 0600, owner builder:builder).
  3. run_phase fuehrt die Unterbloecke sequenziell aus.
     Pro Unterblock: run_pipeline mit phasen_state.
     Status: pending -> running -> done | no_go | failed.
  4. Gesamt-Review (deterministisch) + Approval [j]/[n].
     Bei [j]: Sammel-Commit via apply_commit_and_doku.
  5. phase_aktiv wird auf false gesetzt.

Rollback (RR-K1/K2/K3):
  Bei Exception oder Phase-NO-GO: _phase_rollback setzt
  den Working Tree auf phase_start_head zurueck. Best-
  Effort (faengt Exception, gibt bool).

Plan-Korrektur (P2b-5):
  Bei Phase-NO-GO: Planner liefert einen korrigierten
  Plan. Max 1 Korrektur-Zyklus pro Phase
  (state.phase_korrektur_zyklus).

Planner-Rolle (Stufe 1 vs. Stufe 2):
  Stufe 1 (P1): uebersetzt den Rohauftrag in einen
    konkreten Bau-Auftrag. --planner-Pfad.
  Stufe 2 (P2a): liefert den Phasenplan (P10-P14).
    --phase-Pfad.
  HARD_RULES_PLANNER_STUFE1/_STUFE2.

Audit-Kinds (Auswahl):
  planner_start, planner_vorschlag,
  phase_plan_erstellt, phase_plan_parse_failed,
  phase_plan_verworfen, phase_plan_editiert,
  run_phase_start, run_phase_ende,
  phase_unterblock_start, phase_unterblock_ende,
  phase_commit_paket_gesammelt,
  phase_commit_paket_leer,
  phase_gesamt_review, phase_rollback,
  phase_start_head_gesetzt,
  phase_budget_ende,
  phase_plan_korrektur_start,
  phase_plan_korrektur_failed,
  phase_abgebrochen.

## Post-Apply-Recovery

Nach einem Patch-Apply fuehrt die Werkstatt ein
Basis-Gate aus (ruff + py_compile + Tests). Wenn das
Basis-Gate nach dem Apply rot ist, wird der Builder
zurueckgeholt — statt terminal zu enden.

Signal-Kette:
  apply_and_recheck gibt rc=19 zurueck, wenn das
  Basis-Gate nach dem Apply rot ist
  (pipeline.py, ca. Z. 5157).
  run_pipeline prueft rc_apply == 19 und ruft
  _post_apply_korrektur_loop (ca. Z. 6617).
  _post_apply_korrektur_loop laeuft max 2 Runden
  (max_korrektur_runden=2). Bei erschoepften Runden
  gibt sie rc=18 zurueck (generischer Fail-closed).

rc-Semantik:
  18 = generischer Fail-closed (unveraendert).
  19 = spezifisches Signal: Post-Apply-Basis-Gate rot,
       Korrektur noetig.
  Nur 3 Fundstellen fuer 19: apply_and_recheck,
  Korrektur-Loop, run_pipeline.

Builder-Recovery-Prompt:
  _bauer_recovery_prompt baut den Prompt fuer die
  Korrektur-Runde. Enthaelt die Diagnose aus
  state.letzter_recovery_vorschlag.

Audit-Kind: builder_recovery_nach_apply.

## Git-Konventionen (Werkstatt-Repo)

- core.fileMode = false.
  Grund: chmod 750 sieht Git als 100755; die
  Restriktion "others keine Rechte" kann Git nicht
  abbilden. Mode-Differenzen erscheinen deshalb
  nicht in git status und werden nicht committet.

- post-checkout-Hook (.git/hooks/post-checkout):
  chown -R builder:builder /opt/werkstatt/projects/
  Grund: git checkout als root setzt Owner auf root
  zurueck. Der Hook laeuft nach jedem checkout/reset
  und stellt den richtigen Owner wieder her.

- Beide Einstellungen sind lokal, nicht im Repo.
  Bei einem Clone auf einem neuen Rechner muessen
  sie reproduziert werden.

- projects/ gehoert builder:builder 750.
  projects/*.phase.yaml: builder:builder 600.
  projects/*.memory.yaml: builder:builder 750.

Anlass: 2026-10-16, Reviewer-Auflage Owner-Mode-A1.

## Messtechnik

### ruff mit --no-cache messen

Bei der Auswertung von ruff IMMER --no-cache verwenden.

Anlass: 2026-10-15, Phase 1 Projekt-Schema.
Der erste ruff-Aufruf meldete 2 Fehler (I001), der zweite
Aufruf ohne Aenderung 0 Fehler. Der .ruff_cache war stale.
Erst --no-cache lieferte das reproduzierbare Ergebnis.

### mypy rekursiv messen

mypy ab jetzt rekursiv ueber das gesamte Werkstatt-Verzeichnis:
  mypy /opt/werkstatt/
Nicht nur pipeline.py. Anlass: PB-63, siehe Handoff-Regel P6.
