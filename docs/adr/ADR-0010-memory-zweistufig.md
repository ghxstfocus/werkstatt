# ADR-0010: Memory zweistufig — project + global mit Promotion

- **Datum:** 2026-11-04
- **Status:** superseded by ADR-0032
- **Hinweis:** Die Provenance-, Unabhaengigkeits-, Sanitization- und
  Widerlegungsregeln wurden in ADR-0032 uebernommen. Das dort beschriebene
  getrennte Zwei-Datenbank-Design ist durch einen gemeinsamen logischen
  Memory-Store mit Project-/Global-Scope ersetzt; OP-382 bleibt Voraussetzung
  fuer Aktivierung.
- **Kontext:** OP-220 legt eine projektlokale SQLite-DB
  (`.werkstatt/erfahrung.db`) an. Viele Erfahrungen sind aber
  universell: `# type: ignore` ohne Kommentar, `|| true` in Shell-
  Skripten, geschwaechte Assertions, fehlende Imports nach Refactor,
  Scope-Creep im Plan. Wuerde jede Projekt-DB diese Erkenntnisse neu
  lernen, entstuende Redundanz und Drift. Gleichzeitig sind manche
  Fakten projektspezifisch (DB-Typ, Test-Runner, Migrationspfad) und
  gehoeren *nicht* in eine globale DB.

**Fragestellung:** Eine globale DB, eine projektlokale, oder beides
mit Promotion?

**Optionen:**

A) Nur projektlokal (OP-220 wie geplant). Universelle Antipatterns
   werden pro Projekt neu gelernt.
B) Nur global. Projekt-Fakten muessen draussen bleiben — hoher
   Verlust an Nuance.
C) Zweistufig: projektlokal + global, mit Promotion-Regeln und
   Sanitization beim Aufstieg.

## Entscheidung

**Option C — zweistufig mit Promotion.**

- Beide Tabellen (`erfahrung`, `regeln`, `semantic_memory`) bekommen
  eine `scope TEXT NOT NULL DEFAULT 'project'`-Spalte.
- OP-220a fuehrt diese Spalte sofort ein (Voraussetzung fuer
  spaetere Promotion).
- `promote_to_global(regel_id)` prueft, ob dieselbe problem_klasse
  in **≥2 anderen Projekt-DBs** `confirmed` ist → legt globalen
  `candidate` an.
- **Sanitization beim Aufstieg:** Pfade generalisieren
  (`/opt/projekt/...` → `<project>/...`), IPs maskieren (wie
  `redaction.py`), Projekt-Namen durch `<project>` ersetzen.
  Sonst wandert "security-ai"-Spezifisches in die globale DB.
- **`gehirn-global.db`-Pfad:** `~/.werkstatt/gehirn-global.db`
  (User-Home, mehrere Projekte teilen ihn), taegliches Backup nach
  `.backups/`. Nicht git-getrackt (Binaerdatei, Konflikte).
- **`match_erfahrung`-Prioritaet:** Projekt-Treffer zuerst, dann
  global auffuellen, dann kanonische Regeln immer injizieren.
  Bei Widerspruch: Projekt gewinnt.

**Begruendung:** Zweistufig loest beide Probleme (Redundanz-
Vermeidung *und* Projekt-Spezifitaet). Ohne Sanitization wird die
globale DB unweigerlich mit Projekt-Muell kontaminiert — das ist
der Preis fuer "uebergreifend". Die `scope`-Spalte in OP-220a
sofort einzufuehren ist billiger als eine spaetere Migration.

## Konsequenzen

Positiv:
- Universelle Antipatterns werden einmal gelernt, nicht pro Projekt.
- Projekt-Fakten bleiben projektlokal (Datenhygiene).
- Promotion ist explizit (Tool-Aufruf, nicht automatisch) →
  User behaelt Kontrolle.

Negativ:
- Zwei DBs, zwei Ladepfade, doppelte Query-Logik.
- Sanitization muss getestet werden (Pfad-/IP-/Namens-Muster).
- Backup-Strategie fuer `~/.werkstatt/` ist neue Infrastruktur.

Neutral:
- Bestehende OP-220-Akzeptanzkriterien werden erweitert (in
  OP-221 dokumentiert).

## Nachtrag 2026-11-07 (Punkt 6 aus externem Review)

### Provenance-Pflicht — Wiederholungen != unabhaengige Bestaetigungen

**Problem:** Die Trust-Stufen `candidate -> confirmed -> canonical`
in OP-221 basieren auf "2-3 erfolgreicher Anwendung" bzw. "5+
Beobachtungen". Wenn derselbe Loop-Lauf 5x denselben Fehler macht,
sind das 5 Wiederholungen, aber **keine 5 unabhaengigen
Beobachtungen**. Die Vertrauensstufe waere kuenstlich aufgeblaeht.

**Konsequenz:** Jeder Erfahrungs-Eintrag MUSS Provenance tragen:

    erfahrung:
      run_id           — welcher Loop-Lauf
      kontext_hash     — Hash aus (aufgabe + state.tasks + version)
      regel_version    — Version der angewendeten Regel (falls vorhanden)
      projekt          — security-ai, werkstatt, ...
      komponente       — z.B. "planner.py:_zerlege_in_sub_tasks"
      problem_klasse   — z.B. "mypy_attr_defined"
      ursache_tag      — code_bug|test_bug|spec_bug|infra
      beobachtung      — was der Loop gesehen hat (roher Fehler)
      hypothese        — vorgeschlagene Ursache
      loesung          — angewendeter Fix
      verifikation     — erfolgreich|fehlgeschlagen|unbekannt
      spaetere_widerlegung — wann+warum widerlegt
      quellen          — Liste von run_ids, die zu diesem Cluster gehoeren

### Trust-Aufstieg nur bei unabhaengigen Quellen

- `candidate`: 3+ Episoden, aber alle aus demselben `kontext_hash`
  -> nur `candidate` (nicht `confirmed`)
- `confirmed`: 2+ **unabhaengige** `kontext_hash`-Werte ODER
  2+ erfolgreiche Anwendungen aus verschiedenen `run_id`s
- `canonical`: 5+ unabhaengige `run_id`s, mind. 1 erfolgreiche
  Anwendung, keine Widerlegung

**Zaehl-Regel:** Der Trust-Aufstieg zaehlt **eindeutige
`kontext_hash`-Werte**, nicht Episoden. Zwei Loops mit derselben
Aufgabe und derselben Fehlerstelle = 1 Beobachtung, nicht 2.

### Widerlegung

Jede Regel kann `widerlegt` markiert werden (durch Mensch oder
durch widersprechende Beobachtung). Eine widerlegte Regel verliert
ihre Trust-Stufe:
- `confirmed` -> `candidate`
- `canonical` -> `confirmed`
- `candidate` -> geloescht

Widerlegungen werden im `memory_ledger` dokumentiert.

### Neue Spalten in erfahrung/regeln

- `run_id TEXT`
- `kontext_hash TEXT`
- `regel_version INT`
- `widerlegt_am TEXT`
- `widerlegt_grund TEXT`

### Migration

OP-220a erweitert nicht nur um `scope`, sondern um diese 5 Spalten
(alle NULLABLE, keine Breaking-Changes fuer Bestandsdaten).

**Neue OP:** OP-220a-AK erweitert (Provenance-Spalten).

