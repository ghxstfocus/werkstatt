# ADR-0010: Memory zweistufig — project + global mit Promotion

- **Datum:** 2026-11-04
- **Status:** accepted
- **Kontext:** OP-113 legt eine projektlokale SQLite-DB
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

A) Nur projektlokal (OP-113 wie geplant). Universelle Antipatterns
   werden pro Projekt neu gelernt.
B) Nur global. Projekt-Fakten muessen draussen bleiben — hoher
   Verlust an Nuance.
C) Zweistufig: projektlokal + global, mit Promotion-Regeln und
   Sanitization beim Aufstieg.

## Entscheidung

**Option C — zweistufig mit Promotion.**

- Beide Tabellen (`erfahrung`, `regeln`, `semantic_memory`) bekommen
  eine `scope TEXT NOT NULL DEFAULT 'project'`-Spalte.
- OP-113a fuehrt diese Spalte sofort ein (Voraussetzung fuer
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
der Preis fuer "uebergreifend". Die `scope`-Spalte in OP-113a
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
- Bestehende OP-113-Akzeptanzkriterien werden erweitert (in
  OP-129 dokumentiert).
