# Offene Bloecke — Werkstatt (Umbau)

Stand: 2026-10-19 (Umbau-Start, HEAD be0cd3f).
Vorherige Todos (vor Umbau): `OFFENE-BLOECKE-ARCHIV.md`.
Uebersicht: `ROADMAP.md`. Erledigt: `ERLEDIGT.md`.
Ziel: `NEUBAU-ZIELBILD.md`. Inventar: `NEUBAU-INVENTAR.md`.

Chronologisch nach Umbau-Phasen. Append-only pro Phase.

## Phase 3a — run_pipeline zerlegen (laufend)

| Block | Kategorie | Beschreibung | Aufwand | Status |
|---|---|---|---|---|
| 3a-1c-1-b | 3 | UNKLAR-Kette (`pipeline.py` Z. 8196/8219, rc=14). Braucht 2 Extra-Mocks (`ask_reviewer_for_recovery`, `print_recovery`). Charakterisierung in 3a-1c-1 oder spaeter. | klein | offen |
| 3a-1c-1b-Fallback | 3 | `judge_verdict_sequenz`-Fallback (Sequenz erschoepft -> starr `judge_verdict`) in 3a-1c-1a implementiert, aber nicht getestet. Test folgt in 3a-1c-1b. Fail-open-Hinweis: Fallback uebernimmt `judge_verdict`; fail-closed nur, wenn `judge_verdict` fail-closed ist. | klein | offen |
| 3a-3-b | 3 | NO-GO-Recovery + Recovery nach Loop (`pipeline.py` Z. 8460-8467). Gehoert in 3a-3 (`_phase_main_pfad`, Befund CI/CG, Deadlock-Kette). | mittel | offen |
| 3a-1c-1a-COMMAND-Solver | 3 | 3a-1c-1a-COMMAND-Test deckt Solver-Ausfuehrung NICHT ab. Solver-Ausfuehrung ist in `_handle_solver_command` zu testen — existierenden Test pruefen, sonst Merkposten fuer 3a-1c-2. Folge aus Fix C (Reviewer A7-4, Aufruf-Tiefe #17). | klein | offen |
| 3a-1c-1-b (Vorbedingung) | 3 | UNKLAR-Verhaltens-Test MUSS vor 3a-1c-2 abgeschlossen sein. Nach extract-1 sind 3 UNKLAR-Pfade (Kette, Payload-raw, Widerspruch) nur durch V2-Struktur-Tests abgesichert, die bei 3a-1c-2 brechen. 3a-1c-2 darf ohne 3a-1c-1-b-Abnahme nicht beginnen (A9-8-3a, HR-R9). | mittel | offen |
| Struktur-Tests umstellen | 2 | 15 gruene `inspect.getsource(run_pipeline)`-Tests brechen bei 3a-1c-2/3/4 (C7/C0C1C2C6/C8C9). Vor 3a-1c-2 Block einplanen. Duale Quellen-Pruefung oder Verhaltens-Test (A9-13). | gross | offen |
| 3a-1c-2-V2-Groesse | 3 | V2 = 303 Z., 13 Steuerungsstellen, 12 Parameter. Zu gross fuer 1-Rutsch. Zerlegung V2a/V2b vor 3a-1c-2 pruefen (A8-2-nach-3b). | mittel | offen |

## Phase 3b — Loop-Umbau (nach 3a)

Noch keine Merkposten. Entstehen hier, sobald 3a abgeschlossen.

## Phase 3c — NEUBAU-Abloesung (nach 3b)

Noch keine Merkposten. Entstehen hier, sobald 3b abgeschlossen.

## Phase 5 — ruff/mypy-Rest

| Block | Kategorie | Beschreibung | Aufwand | Status |
|---|---|---|---|---|
| 5-ruff | 2 | ruff 17 Fehler (Code). Phase-5, kein Runtime-Bug. | klein | offen |
| 5-mypy-code | 2 | mypy 7 Fehler / 2 Dateien (Code). 3 import-not-found (MYPYPATH), 2 R-A (`RunState.messungen_nach_apply`), 2 list/set (Annotation-only). | klein | offen |
| 5-mypy-tests | 2 | mypy `tests/` 17 Fehler / 4 Dateien (nicht in Baseline; 4 davon aus 3a-1a-Tests, `ref`-Annotation). | klein | offen |

## Session-Nachbereitung

| Block | Kategorie | Beschreibung | Aufwand | Status |
|---|---|---|---|---|
| Bau-Handoff-Refresh | 2 | `Bau-Handoff.md` nach Session-Ende auf Ist-Stand bringen (HEAD be0cd3f, Branch umbau/phase-2, 1229 Tests, ruff 17, mypy 7, AST 6, Katalog 167). | klein | offen |

## Referenz — Deadlock-Kette (dokumentiert, fuer 3a-3)

Der Phase-21-Deadlock war eine Kette:
1. Parser strippt 4 Leerzeichen nicht (min==2 only) -> Anker 0x.
2. max_tokens_judge 8192 -> reasoning-only, content leer.
3. D2-Duplikate global statt pro Paket -> Phase 20b scheitert.
4. Planner-Resume bei failed -> Planner kostet, liefert nichts.
5. Contract fehlt im Builder-Prompt -> Builder raet API.
6. Test-Fehler nicht persistiert -> Builder wiederholt.
7. verify_code fehlt -> erfundene APIs (log(status=...)).



## Verweise

- `ROADMAP.md` — Phasen-Uebersicht.
- `ERLEDIGT.md` — Erledigte Bloecke mit Commit/Tests.
- `NEUBAU-ZIELBILD.md` — Ziel-Architektur.
- `NEUBAU-INVENTAR.md` — 191 Funktionen, N1-N4, R-3.
- `NEUBAU-ENTFERNUNG.md` — Entfernungs-Register.
- `UEBERGABE-3A-2026-10-19.md` — Phase-3a-Uebergabe.
- `OFFENE-BLOECKE-ARCHIV.md` — Todos vor Umbau.
