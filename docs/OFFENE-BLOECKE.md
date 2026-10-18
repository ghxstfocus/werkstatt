# Offene Bloecke — Werkstatt

Stand: 2026-10-18 (nach W52b C+D+E, W61, W58, Phase 20b)
Todo, priorisiert. Append-only.
Uebersicht in `ROADMAP.md`. Erledigt in `ERLEDIGT.md`.

## Prioritaet 1 (akut, blockiert Phase 20b)

| Block | Kategorie | Beschreibung | Aufwand |
|---|---|---|---|
| W52b C | 3 | Anker-Check gegen Datei-Inhalte statt String. `pruefe_anker_gegen_messung` (Z. 4805), `_gemessene_pfade` (Z. 8624). | mittel |
| W52b D | 3 | Prompt-Bauer auf Index. `_messwerte_fuer_prompt` (Z. 5660), `_messwerte_fuer_planner` (Z. 5646), `_build_judge_input` (Z. 6067), `_build_commit_input` (Z. 5736), `_planner_user_content` (Z. 3656), Builder-Prompt (Z. 9492, 9599, 9936, 9980). | gross |
| W61 | 3 | Rollen-Sanierung: 5 Unterbloecke a-e. Reviewer 3 Aufgaben, Judge 2, Solver nutzt Reviewer-Modell. | gross |

## Prioritaet 2 (strukturell)

| Block | Kategorie | Beschreibung | Aufwand |
|---|---|---|---|
| W52b E | 1 | `mess_protokoll` deprecated markieren, Bestandsleser dokumentieren. | klein |
| W-Resume-Fail-Kontext | 3 | Planner bekommt Fail-Kontext (Test-Output, rote Tests, letzter Patch, Recovery-Vorschlag), liefert begruendeten Plan. Neuer Skill `fail-recovery`. | gross |
| W58 | 3 | Reviewer-Leer-Antwort. `max_tokens_reviewer` 1024 zu klein, `reviewer.md` 56 Z. zu duenn. | klein |
| W59-2 | 3 | W13b-W59-Interaktion. | klein |

## Prioritaet 3 (Refactor)

| Block | Kategorie | Beschreibung | Aufwand |
|---|---|---|---|
| W36-RP-a | 2 | Helper-Wartbarkeit (nach 5 Phasen-Laeufen pruefen). | klein |
| W36-RP-b-os | 3 | os.system/os.popen (0 Treffer heute). | klein |
| W48-A16-b-2-a-b | 2 | solver_max-Co-occur-Beleg. | klein |
| W52a-1 | 2 | Planner-Funktionen nach `werkstatt/planner.py`. | mittel |
| W36-2b..6 | 3 | pipeline.py modularisieren (6 Module). | gross |
| W56 | 3 | Phasen-Apply prueft alle Zieldatei-Tests pro Unterblock. | mittel |
| W62 | 3 | README/KONVENTION Diagramm-Konsistenz. | klein |

## W52b — Detail (On-Demand-Messung)

**Ziel:** `mess_protokoll` (String) raus. `state.messungen`
(Liste von Datei-Referenzen) + `.werkstatt/<run_id>/
messungen/<sha1>.txt` + `index.json` rein.

**Gebaut:**
- `state.Messung` (dataclass).
- `state.messungen`, `state.messungen_nach_apply`,
  `state.gelesene_dateien`.
- `_schreibe_messung` (pipeline.py Z. 6320).
- `execute_commands` schreibt Datei + Liste.
- `_post_apply_messung` fuellt `messungen_nach_apply`.
- `apply_code_patches` W59-Check + mtime-Update.
- Katalog +2: `patch_ohne_messung`,
  `patch_datei_geaendert_seit_messung`.

**Erledigt (2026-10-18):**
- C: Anker-Check gegen Datei-Inhalte (e768353).
- D: Prompt-Bauer auf Index + Zieldatei-Volltext (e2b3ab3,
  3b907a9).
- E: deprecated markiert (e2b3ab3).
- `_gemessene_pfade` liest `state.messungen` (e768353).
- `state.messungen_nach_apply` in `_build_judge_input`
  (e2b3ab3).

**W52b-E — Bestandsleser:** siehe eigener Abschnitt unten.

## W61 — Detail (Rollen-Sanierung)

**Befund:**
- `reviewer.md` 56 Z.: Mess-Wahl + Commit + Recovery.
  Ziel: < 100 Z., nur Commit-Review.
- `judge.md` 90 Z.: Patch + Repair. Ziel: < 150 Z.,
  nur Patch. `_phase_judge_repair_runde` (Z. 2519)
  raus.
- `rufe_solver` (Z. 5505): `reviewer_verdict_model`.
  `solver_model` fehlt in state.py.
- `builder.md` 647 Z.: Ziel < 300.
- `planner.md` 299 Z.: Ziel < 150.

**Unterbloecke:**
- W61a: Reviewer-Sanierung (neue Rolle
  `measure_picker` oder Planner uebernimmt
  Mess-Wahl).
- W61b: Judge-Sanierung (Repair raus).
- W61c: Solver-Sanierung (`solver_model` neu).
- W61d: Prompt-Groessen (builder.md, planner.md).
- W61e: Doku (ROLLEN-AUDIT, ARCHITEKTUR,
  KONVENTION, README).

## Merkposten

- W52b-C: Anker-Check gegen Datei-Inhalte.
- W52b-D: Prompt-Bauer auf Index.
- W52b-E: `mess_protokoll` deprecated.
- W61: Rollen-Sanierung (5 Unterbloecke).
- W-Resume-Fail-Kontext: Fail-Log + Skill
  `fail-recovery`.
- W58: Reviewer-Leer-Antwort.
- W36-RP-a: Helper-Wartbarkeit.
- W36-RP-b-os: os.system/os.popen.
- W48-A16-b-2-a-b: solver_max-Co-occur.
- W59-2: W13b-W59-Interaktion.
- W25-planner-md: ERLEDIGT (041c9a3).
- W30-fix-b: ERLEDIGT (ab0f389).

## Verweise

- `ROADMAP.md` — Uebersicht Phasen/W-Bloecke.
- `ERLEDIGT.md` — Erledigte Bloecke mit Commit/Tests.
- `ARCHITEKTUR.md` — Ziel, Rollen, Luecken.
- `KONVENTION.md` — Ordnerstruktur, Datei-Namen.
- `ROLLEN-AUDIT.md` — Rollen-Stand (Sektion 8).

## W52b-E — Bestandsleser (nach W52b C+D+E)

`mess_protokoll` und `mess_protokoll_nach_apply` sind als
DEPRECATED markiert (state.py). Neue Leser MUESSEN
`state.messungen` / `state.messungen_nach_apply` nutzen.

Bestandsleser (Stand nach W52b D+E), die noch umgestellt
werden muessen:

| Zeile | Funktion | Zweck | Umbau auf |
|---|---|---|---|
| 3656,3659 | `_planner_user_content` | Planner-Korrektur-Zweig | `_mess_index_block(state)` |
| 3769,3772 | Planner-Loop | Laengen-Tracking | `len(state.messungen)` |
| 6535,6541 | `execute_commands` | Gesamtlimit | `state.messungen` |
| 9255,9257 | `run_pipeline` | Print an Konsole | `_mess_index_block(state)` |
| 10450,10461 | Commit-Review-Gate | `bool(state.mess_protokoll)` | `bool(state.messungen)` |

`mess_protokoll_nach_apply` (String): Fallback in
`_mess_inhalt_nach_apply` (Z. 6145) bleibt bewusst, bis
alle Laeufe `messungen_nach_apply` befuellen.

**Aufwand:** klein. **Kategorie:** 2.
**Nicht in W52b D+E enthalten**, weil Scope.

## Sitzung 2026-10-18 (Fortsetzung) — erledigt

- W61-Label-Fix: Judge-Loop spricht Judge (9ead335).
- W61c: `solver_model` eigene Rolle (9ead335).
- Subagenten: explore aktiv, bash/browser vorhanden (9ead335).
- Parser-Heuristik: YAML-Block-Einrueckung (81efad8).
- `_anker_in_messung` whitespace-tolerant (81efad8).
- pytest-Measurement (65d4d07).
- W58: max_tokens_judge 8192 (e2e8b60).

## Offen (P1)

- W61a: Reviewer-Aufgaben reduzieren (Mess-Wahl + Recovery
  raus). Heute: Reviewer macht 3 Aufgaben.
- W61b: Judge-Repair raus (`_phase_judge_repair_runde`).
- W61d: `builder.md` 647 -> <300, `planner.md` 299 -> <150.
- W-Resume-Fail-Kontext: Planner bekommt Fail-Log +
  Skill `fail-recovery`.
- Tests fuer U2/U3/U4 (security-ai): Audit-Pfade
  (APPLIED, FAILED, ROLLED_BACK) sind code-seitig da,
  aber nicht getestet.

## Offen (P2)

- Planner erfindet APIs (AuditWriter.log-Signatur).
  Planner muss die API messen, bevor er den Auftrag
  schreibt.
- W52b-E Bestandsleser umstellen (siehe Abschnitt oben).

## Offen (P3)

- W36-RP-a: Helper-Wartbarkeit.
- W36-2b..6: pipeline.py modularisieren.
- W62: README/KONVENTION Diagramm-Konsistenz.
- Auftrag fuer die Werkstatt: security-ai-Doku
  nachziehen (Phase 20b in STATUS.md, ROADMAP.md,
  SECURITY_LOG.md).


## W61d — Befund 2026-10-18 (Phase-Prompts trennen)

`builder.md` wird fuer BEIDE Phasen genutzt:
- **Phase 1 (Patch-Bau):** Builder-COMMAND-Loop,
  Reply = PATCH-BEGINN/ENDE. Braucht: Anker-Regeln,
  COMMAND: RUN, MESSWERTE, KUERZUNGS-MARKER.
- **Phase 2 (Commit-Paket):** `build_commit_paket`,
  Reply = COMMIT-MESSAGE. Braucht: SELBST-REVIEW,
  COMMIT-MESSAGE, __ALL__-Pflege, REVIEWED-BLOCK.

Redundanz:
- SELBST-REVIEW (17 Z.): Phase 2, nicht Phase 1.
- COMMIT-MESSAGE (32 Z.): Phase 2, nicht Phase 1.
- COMMAND: RUN (44 Z.): Phase 1, nicht Phase 2.

**Ziel:** `builder.md` aufteilen in
- `builder_patch.md` (< 300): Phase 1.
- `builder_commit.md` (< 300): Phase 2.

`load_agents` laedt `builder.md` als System-Prompt.
Der Aufrufer (`builder_reply_mit_command_loop` vs.
`build_commit_paket`) waehlt den richtigen.

**Aufwand:** mittel. **Kategorie:** 3.

