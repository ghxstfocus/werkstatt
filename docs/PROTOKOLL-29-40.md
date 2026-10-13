# Beobachtungs-Protokoll — Probebetriebe 29 bis 40

Stand: 2026-10-13
Werkstatt-HEAD: 760f6e6 (probebetrieb-40)
Ziel-Projekt-Commits: dd3048b, 3ccb883

Dieses Protokoll dokumentiert die 12 Probebetriebe
dieser Session und die daraus abgeleiteten Auflagen.
Es dient als Lernquelle fuer kuenftige Sessions.

================================================================
UEBERSICHT
================================================================

Probebetrieb | Ergebnis | Auflage(n) | Kernbefund
-------------|----------|------------|------------
PB-29        | Fail     | 2186       | Ausschnitt gekuerzt, kein Marker
PB-30        | Fail     | 2187       | COMMAND-Loop fehlt (Livelock)
PB-31        | Fail     | 2187, 2188 | Builder ignoriert Marker
PB-32        | Fail     | 2188, 2189 | Builder rekonstruiert Pfad
PB-33        | Fail     | 2189       | Builder zitiert Pfad nicht woertlich
PB-34        | Fail     | 2190, 2191 | GEMESSENER INHALT ignoriert
PB-35        | Fail     | 2191       | Prompt einmal gebaut
PB-36        | Fail     | 2192       | Automatik fehlt
PB-37        | Fail     | 2194       | Audit-Debug zeigt: IP-Redaction
PB-38        | Fail     | 2195, 2196, 2197 | Wurzel: IP-Redaction
PB-39        | Fail     | 2196, 2197, 2198 | Rechte + Regex-Format
PB-40        | ERFOLG   | --         | Commit 3ccb883

================================================================
DETAILS
================================================================

--- PB-29 ---

Datum: 2026-10-13
Auftrag: Test fuer traceroute (test_traceroute_binary_missing)
Ergebnis: Fail. apply_code_patches Anker 0x.
Befund:
  Der ZIELDATEIEN-Ausschnitt von test_tools_net_diag.py war
  bei Zeichen 3000 abgeschnitten. Der Builder baute einen
  Anker aus dem abgeschnittenen Bereich, der count 0 ergab.

Auflage 2186:
  read_target_snippets liefert Kopf + Kuerzungs-Marker.
  Bei "GEKUERZT" folgt ein Hinweis mit COMMAND: RUN
  read_file.

--- PB-30 ---

Ergebnis: Fail. builder_command_deadlock nach 5 Runden.
Befund:
  Der Builder sendete zweimal COMMAND: RUN read_file, aber
  execute_commands wurde nur mit quelle="reviewer" aufgerufen.
  Der Builder-COMMAND-Loop fehlte.

Auflage 2187:
  Neue Funktion builder_reply_mit_command_loop.
  quelle="builder" in ERLAUBTE_QUELLEN.
  max_builder_runden=3. Exit 19.

--- PB-31 ---

Ergebnis: Fail. Anker 0x.
Befund:
  Builder-Runde 1: 1 COMMAND angefordert.
  Builder-Runde 2: Patch mit falschem Anker.
  Reviewer: Code-GO.

Auflage 2188:
  agents/builder.md: Widerspruch bei GEKUERZT-Marker
  aufloesen. KUERZUNGS-MARKER-Abschnitt.

--- PB-32 ---

Ergebnis: Fail. builder_command_deadlock nach 3 Runden.
Befund:
  Builder forderte dreimal denselben (falschen) Pfad:
  tests/unit/test_tools_traceroute.py.
  Der Pfad stand woertlich im Auftrag.

Auflage 2189:
  execute_commands markiert ok=false prominent.
  Builder-COMMAND-Loop: zweimaliger identischer Fehler
  -> sofortiger Deadlock.
  agents/builder.md: Pfad-Regel (woertliches Zitat).

--- PB-33 ---

Ergebnis: Fail. Anker 0x.
Befund:
  Reviewer hat read_file erfolgreich ausgefuehrt
  (ok=true). Builder-Prompt hatte GEMESSENER INHALT
  leer (weil der Reviewer vor dem Builder gemessen hat,
  aber der Block statisch gebaut wurde).

Auflage 2190:
  OPTIONALE MESSUNGEN -> GEMESSENER INHALT (verbindlich).
  Reihenfolge: ... ZIELDATEIEN, GEMESSENER INHALT, AUFGABE.
  Konflikt-Erkennung: ZIELDATEIEN-Ausschnitt durch
  Kopf + Hinweis ersetzen, wenn der Pfad schon gemessen.

Auflage 2191:
  builder_reply_mit_command_loop nimmt user_prompt_fn
  (Callable) statt user_prompt (str). Prompt wird pro
  Runde frisch gebaut.

--- PB-34 ---

Ergebnis: Fail. Anker 0x.
Befund:
  Builder-Runde 1: 1 COMMAND (read_file, ok=true).
  Aber builder_user_prompt war einmal gebaut, GEMESSENER
  INHALT blieb "(keine)".

(Auflagen 2190 + 2191 waren in PB-33 entworfen, aber noch
nicht implementiert.)

--- PB-35 ---

Ergebnis: Fail. Anker 0x.
Befund:
  Automatik fehlt. Der Reviewer hat 1 optionale Messung
  angefordert, aber der Builder nutzte sie nicht.

Auflage 2192:
  Neue Funktion ensure_ziel_gemessen: prueft pro Zieldatei,
  ob sie im mess_protokoll vollstaendig vorliegt. Wenn
  nicht: read_file mit quelle="pipeline_auto".

--- PB-36 ---

Ergebnis: Fail. Anker 0x.
Befund:
  ensure_ziel_gemessen lief, aber der Pfad war schon
  gemessen -> keine Auto-Messung.
  Der Builder ignorierte GEMESSENER INHALT trotzdem.

--- PB-37 ---

Ergebnis: Fail. Anker 0x.
Befund:
  Audit-Debug (Auflage 2194) liefert erstmals
  builder_prompt_gebaut und builder_reply_erhalten.
  Der reply_kopf zeigt: Anker mit "[IPV4]" statt
  echter IPs.

WURZEL GEFUNDEN: redaction.redact_all ersetzt IPs
durch "[IPV4]". Der Builder baut den Anker mit
"[IPV4]", apply_code_patches prueft gegen die echte
Datei mit "192.168.x.x" -> Fail.

--- PB-38 ---

Ergebnis: Fail (Commit-NO-GO nach 2 Versuchen).
Befund:
  Der Anker trifft (Auflage 2195 wirkt). Recheck gruen.
  Commit-Review scheitert: test_anzahl "nicht gemessen".
  Der MESSWERTE-Block liest basis_protokoll (vor Patch),
  nicht basis_protokoll_nach_apply.
  Zusaetzlich: Der Patch bleibt im Arbeitsbaum stehen.

Auflage 2195 (Wurzel):
  redaction.py: private IPs (RFC 1918, Loopback,
  Link-Local, CGNAT, Dokumentation) werden nicht mehr
  redigiert. Oeffentliche IPs bleiben maskiert.

Auflage 2196:
  collect_messwerte bevorzugt basis_protokoll_nach_apply.

Auflage 2197:
  _rollback_zieldateien und _fail_closed.
  Bei Fail-closed-Abbruch im Commit-Pfad: Arbeitsbaum
  zuruecksetzen (git checkout --).

--- PB-39 ---

Ergebnis: Fail (Commit-NO-GO nach 2 Versuchen).
Befund (erster Versuch):
  apply_code_patches Schreibfehler: Permission denied.
  Die Zieldatei gehoerte root:root (durch manuelles
  git checkout als root in PB-38).
Befund (zweiter Versuch, nach chown):
  test_anzahl immer noch "nicht gemessen".
  Ursache: collect_messwerte-Regex kennt nur "STDOUT:\n",
  nicht "STDOUT (letzte Zeile):\n" (Auflage 2176).

Auflage 2198:
  Regex akzeptiert beide Formate:
  STDOUT(?: \(letzte Zeile\))?:\n

--- PB-40 ---

Ergebnis: ERFOLG.
Commit 3ccb883 in security-ai:
  test(workbench): Traceroute-Binary-Fehler-Fall ergaenzt
  Autor: ghxstfocus <ghxst.focus@gmail.com>

Ablauf:
  Basis-Gate: gruen.
  Builder: Patch mit korrektem Anker.
  apply_code_patches: ok.
  Recheck: gruen.
  Commit-Paket: MESSWERTE mit test_anzahl 1314.
  Commit-Review: COMMIT-GO.
  Human-Gate: approve.

================================================================
DIE 12 AUFLAGEN — ZUSAMMENFASSUNG
================================================================

2186  KUERZUNGS-MARKER
      read_target_snippets und format_doc_snippets liefern
      Kopf mit Zeichen-Bereich + Zustand (vollstaendig/
      GEKUERZT). Bei Kuerzung Marker mit COMMAND-Hinweis.

2187  Builder-COMMAND-Loop
      builder_reply_mit_command_loop. Builder darf
      COMMAND: RUN liefern. Max 3 Runden. Exit 19.

2188  builder.md KUERZUNGS-MARKER respektieren
      Widerspruch in builder.md aufgeloest. Bei GEKUERZT:
      COMMAND fordern, nicht patchen.

2189  Pfad-Woertlichkeit + Fehler-Marker
      execute_commands markiert ok=false. Builder-Loop
      bricht bei wiederholtem Fehler ab. Pfad-Regel in
      builder.md.

2190  GEMESSENER INHALT als primaere Quelle
      Reihenfolge im Prompt. Konflikt-Erkennung.

2191  Prompt pro Runde frisch
      user_prompt_fn (Callable). GEMESSENER INHALT in
      jeder Runde aktuell.

2192  Werkstatt messt automatisch
      ensure_ziel_gemessen. quelle="pipeline_auto".

2193  (zurueckgezogen)
      Modellwechsel. Wurzel lag woanders.

2194  Audit-Debug (Diagnose)
      builder_prompt_gebaut, builder_reply_erhalten.
      Ermaeglichte die Diagnose von 2195.

2195  Private IPs nicht mehr redigieren (WURZEL)
      RFC 1918, Loopback, Link-Local, CGNAT, Doku-IPs
      bleiben unredigiert.

2196  collect_messwerte bevorzugt nach-apply
      basis_protokoll_nach_apply als primaere Quelle.

2197  Fail-closed-Rollback
      _rollback_zieldateien und _fail_closed.

2198  collect_messwerte-Regex an Kuerzung
      STDOUT (letzte Zeile) wird akzeptiert.

================================================================
DIE 5 LEHREN
================================================================

1. Erst Diagnose-Werkzeuge, dann fixen.
   Ohne 2194 (Audit-Debug) haetten wir 2195
   (IP-Redaction) nicht gefunden. Die ersten 8
   Auflagen behandelten Symptome.

2. Feature + Prompt + Aktualisierung.
   Jedes neue Feature braucht drei Teile:
     - Mechanik (Code).
     - Prompt (Anweisung an den Agenten).
     - Aktualisierung (Prompt pro Runde, wenn
       er Zustand enthaelt).
   Fehlt eine Schicht, ignoriert der Agent das
   Feature.

3. Werkstatt ist der Messende.
   HARD_RULES_BUILDER B4: Der Builder ist kein
   Messender. Die Werkstatt messt. Umgesetzt in
   2192 (ensure_ziel_gemessen).

4. Fail-closed braucht Rollback.
   Ein Fail-closed-Abbruch ohne Rollback laesst
   den Arbeitsbaum schmutzig. Umgesetzt in 2197.

5. Konsumenten von Format-Aenderungen pruefen.
   2176 aenderte das test_count-Format, 2135
   (collect_messwerte) wurde nicht mitgezogen.
   Folge: PB-39. Umgesetzt in 2198.

================================================================
ENDE DES PROTOKOLLS
================================================================
