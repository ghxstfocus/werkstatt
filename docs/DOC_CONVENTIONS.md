# DOC_CONVENTIONS.md — Golden-Standard fuer Projekt-Doku

Verbindlich fuer alle Projekte, die die Werkstatt baut. Stand: 2026-10-31,
nach Messung von `/opt/werkstatt` und `/opt/security-ai`.

## 1. Die 4 Doku-Rollen (Living Docs, nicht ueberlappend)

| Rolle | Datei | Schreiber | Leser |
|---|---|---|---|
| Constitution + Entry | `AGENTS.md` (root) | Mensch | Loop, Mensch |
| Map | `docs/ARCHITECTURE.md` | Mensch | Loop, Mensch |
| Status | `docs/STATUS.md` | Loop + Mensch | Loop |
| History | `docs/adr/` + `PROGRESS.md` | Mensch + Loop | Mensch |

Ein Fakt hat genau EINE Quelle. Nie dupliziert.

- "Wo liegt Auth?" -> `ARCHITECTURE.md`
- "Ist Auth blockiert?" -> `STATUS.md`
- "Warum wurde X entfernt?" -> `docs/adr/`
- "Was wurde gebaut?" -> `PROGRESS.md` (append-only)

## 2. Pflicht-Dateien pro Projekt

Root:
- `AGENTS.md` (Constitution + Lese-Reihenfolge, < 200 Zeilen)
- `README.md` (fuer Menschen)
- `PROGRESS.md` (append-only, Loop schreibt)
- `CHANGELOG.md` (Version-Historie)

docs/:
- `index.md` (NICHT `README.md`, NICHT `INDEX.md`)
- `STATUS.md` (offene Punkte — einziger Ort fuer "was ist zu tun")
- `ROADMAP.md` (Phasen, Milestones)
- `ARCHITECTURE.md` (Modul-Map)
- `CONVENTIONS.md` (Coding-Regeln)
- `glossary.md` (NICHT `glossary.md`)
- `adr/README.md` (ADR-Index)
- `adr/ADR-0001.md` (erste Entscheidung)

Manifest:
- `projects/<name>.yaml`
- `.werkstatt/<name>.phase.yaml` (Task-SSOT)
- `.werkstatt/verify.json`

## 3. Verbotene Dateien

| Verboten | Grund | Ersatz |
|---|---|---|
| `docs/index.md` | Diaetaxis sagt `index.md` | `docs/index.md` |
| `docs/index.md` | Kollision mit README | `docs/index.md` |
| `docs/DECISIONS.md` | nicht ADR-konform | `docs/adr/` |
| `PROGRESS.md` | dupliziert PROGRESS | `STATUS.md#delete-zone` |
| `docs/STATUS.md` | dupliziert STATUS | `STATUS.md` |
| `projects/<name>.phase.yaml` | dupliziert .werkstatt | `.werkstatt/<name>.phase.yaml` |
| `docs/glossary/` als Ordner | Overhead | `docs/glossary.md` |
| `archiv/bau-handoff-archiv.md` im Root | unuebersichtlich | `docs/archiv/` |

## 4. Sprach-Regel

Ein Projekt = eine Sprache in der Doku. Neue Projekte: Deutsch.
Migration: §7. Code-Kommentare duerfen Englisch sein.

## 5. STATUS.md-Vertrag (maschinenlesbar)

`STATUS.md` enthaelt NUR offene Punkte. Format pro Punkt:

    ### OP-NNN: Kurztitel
    - **Status:** open
    - **Betroffene Dateien:** `pfad/a.py`, `pfad/b.md`
    - **Akzeptanzkriterien:** 1-3 pruefbare Saetze
    - **Tests:** `pytest tests/...`
    - **Blockiert von:** OP-MMM | —

    ## Delete-Zone
    | Pfad | Warum entfernt | Ersetzt durch | Wiedereinfuehrung |

Erledigte Punkte werden aus STATUS.md GELOESCHT (nicht markiert).
Sie wandern nach PROGRESS.md. Loop-Historie ist Beweis.

## 6. Manifest-Vertrag

    docs:
      entry: AGENTS.md
      status: docs/STATUS.md
      roadmap: docs/ROADMAP.md
      architecture: docs/ARCHITECTURE.md
      conventions: docs/CONVENTIONS.md
      adr_index: docs/adr/README.md
      glossary: docs/glossary.md

Der Loop MUSS status, roadmap, architecture, entry lesen.

## 7. Migrations-Workflow

Schritt A (Inventory): alle Doku-Dateien + Rolle + Empfehlung
Schritt B (Bestandsaufnahme): jeden offenen Punkt gegen Code verifizieren
Schritt C (Map + ADR): ARCHITECTURE aus Code, DECISIONS -> ADRs
Schritt D (Entry + Scaffolder): AGENTS.md + Manifest §6

Nach jedem Schritt: eigener Commit + Push.

## 8. Scaffolder-Vertrag

`python3 -m werkstatt.scaffold <name> --dir /opt/<name>` legt alle
Pflicht-Dateien aus §2 an, idempotent, mit `--dry-run`.

## 9. Migrator-Vertrag

`python3 -m werkstatt.migrate <name> --dry-run` / `--apply` prueft
Pflicht/Verbotene, fuehrt §7 aus, committet NICHT (Mensch entscheidet).

## 10. Was die Golden-Spec NICHT regelt

- Wie Code strukturiert wird (CONVENTIONS.md pro Projekt)
- Welche Tests geschrieben werden (Plan pro Aufgabe)
- Wann migriert wird (Mensch)

## 11. Pruef-Kommandos

    for f in AGENTS.md README.md PROGRESS.md CHANGELOG.md \
             docs/index.md docs/STATUS.md docs/ROADMAP.md \
             docs/ARCHITECTURE.md docs/CONVENTIONS.md docs/glossary.md \
             docs/adr/README.md projects/<name>.yaml; do
      [ -f "$f" ] || echo "FEHLT: $f"
    done
