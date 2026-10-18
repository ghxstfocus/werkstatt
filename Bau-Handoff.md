# Bau-Handoff — Werkstatt

Stand: 2026-10-18 (nach W60 Doku-Struktur)
Werkstatt-HEAD: 8ed7747 (Doku-Struktur komplett)
security-ai-HEAD: 759b9e1 (Phase 20b-U1, manuell)
Branch: main (beide Repos)
Tests (Werkstatt): 1166 passed
ruff --no-cache: 0
mypy pipeline.py: 0
Katalog (Audit-Kinds): 119
Tests (security-ai): 1452 passed

## Verweise

- `docs/OFFENE-BLOECKE.md` — Todo, priorisiert (P1/P2/P3).
- `docs/ERLEDIGT.md` — Erledigte Bloecke W1-W60 mit Commit/Tests.
- `docs/ROADMAP.md` — Uebersicht Phasen/W-Bloecke.
- `docs/ARCHITEKTUR.md` — Ziel, Rollen, Luecken.
- `docs/KONVENTION.md` — Ordnerstruktur, Datei-Namen.
- `docs/ROLLEN-AUDIT.md` — Rollen-Stand (Sektion 8, 2026-10-18).
- `docs/IDEEN.md` — Wunschliste (2101-2106).

## Aktueller Bau-Block

Phase 20b (ChangeApplier Audit-Log + Auto-Rollback) ist
blockiert. Die Pipeline deadlockt: Builder sendet Anker,
die nicht im gemessenen Inhalt stehen, 3 Runden
Wiederholung, Solver diagnostiziert falsch
("Auftrag erfuellt"), Reviewer antwortet leer.

**Naechster Block: W59 (Read-vor-Edit, Deadlock-
Mechanismus).** Patch nur nach Messung
(RunState.gelesene_dateien, mtime-Check, Loop-Schutz).
Kategorie 3. 25 bestehende Tests rufen
`apply_code_patches` direkt, muessen angepasst werden.

Danach: Phase 20b neu starten.

## Wichtige Merkposten

- W54-f: builder.md 647 Zeilen (Audit-Ziel < 300).
- W57: Prompt-Audit aller Rollen.
- W59: 25 Tests anpassen.
- W61: Rollen-Sanierung (aus ROLLEN-AUDIT Sektion 8).
- W52a-c: pipeline.py-Modularisierung groesser als
  500 Zeilen (Kern-Infrastruktur).
- W52b: On-Demand-Messung (Dateien statt String im Prompt).
  Vorbild Claude Code (Read vor Edit), Copilot (Tool Search).
- W51h-b: W51h greift nur bei parsebarem Plan.
- W51g-b2: Check-Fehler nicht in letzter_plan_fehler.

## Archiv

Der vorherige Handoff (2026-10-16, 5.567 Zeilen) ist im
`Bau-Handoff-Archiv.md` archiviert. Enthaelt: W1-W60,
PB-68-Laeufe, Anti-Pattern-Serien, Detail-Protokolle.

Fuer den taeglichen Bau-Betrieb reicht dieser Handoff
(Kopf + Verweise + aktueller Block + Merkposten).
Details bei Bedarf im Archiv.
