# Phase 1 — Audit-Kinds: Frequenzmessung + Top-20-Entscheidung

Stand: 2026-10-19
Branch: umbau/phase-1
Basis: audit-logs/agent-pipeline-*.jsonl (7 Tage, 12.-18. Okt. 2026)
Status: Messung abgeschlossen, Loeschung noch nicht ausgefuehrt.

## Messlage

| Kategorie | Anzahl | Bedeutung |
|---|---|---|
| Audit-Eintraege gesamt | 8.941 | 7 Tage |
| Kinds in Logs gesehen | 107 | reale Aktivitaet |
| Kinds statisch im Code (grep) | 153 | audit("...")-Aufrufe |
| Kinds in _KATALOG_SOLL | 166 | 13 dynamisch konstruiert |
| In beiden | 100 | aktiv + gelistet |
| Nur in Logs | 7 | dynamisch, legitim |
| Nur im Katalog (schweigend) | 53 | nie in 7 Tagen aufgetreten |

## Frequenzverteilung (kumulativ)

| Top-N | Eintraege | Anteil |
|---|---|---|
| 10 | 5.875 | 65,7 % |
| 20 | 7.365 | 82,4 % |
| 30 | 8.083 | 90,4 % |
| 50 | 8.621 | 96,4 % |
| 100 | 8.934 | 99,9 % |
| 107 | 8.941 | 100,0 % |

Top-20 erreicht 82,4 % — die 80%-Schwelle aus der Regel
ist mit 20 Kinds empirisch gedeckt.

## Top-20 nach Haeufigkeit

| Rang | Haeufig | Kind |
|---|---|---|
| 1 | 1132 | builder_prompt_gebaut |
| 2 | 1131 | builder_reply_erhalten |
| 3 | 1059 | command_executed |
| 4 | 626 | builder_command_executed |
| 5 | 463 | code_patches_apply |
| 6 | 413 | pipeline_start |
| 7 | 298 | review_round |
| 8 | 298 | anti_patterns_injiziert |
| 9 | 265 | builder_command_deadlock |
| 10 | 190 | recovery_builder_command_deadlock |
| 11 | 173 | phase_unterblock_start |
| 12 | 172 | phase_unterblock_ende |
| 13 | 167 | run_phase_ende |
| 14 | 163 | phase_start_head_gesetzt |
| 15 | 163 | run_phase_start |
| 16 | 152 | phase_resume_erkannt |
| 17 | 136 | solver_trigger |
| 18 | 126 | builder_anker_fehler |
| 19 | 125 | recovery_basis_gate_nach_apply |
| 20 | 113 | code_patches_leer |

## Befund D — 53 schweigende Kinds sind nicht 53 tote Kinds

Test-Abdeckung pro schweigendem Kind geprueft:

- 42 von 53: GETESTET. Fehlerpfade, die funktionieren,
  im Messfenster nicht ausgeloest (LLM-Timeout, YAML
  korrupt, Pipeline abgebrochen, Rollback eskaliert).
- 11 von 53: UNGETESTET.
  - 7 planner_resume_* (mehrfach_split_verboten,
    misch_zustand, order_verletzt, rename_verboten,
    split_cap_erreicht, split_depth, split_done_verboten)
  - 2 judge_command, judge_frage_antwort
  - 2 phase_budget_ende, phase_finish_warnung

Konsequenz: Die naive Loeschung "53 schweigende Kinds weg"
wuerde 42 getestete Fehlerpfade entfernen. Das ist Symptom-
Kultur in umgekehrter Richtung.

## Befund D (Kern) — 20-Ziel braucht Zusammenfassung

20 Kinds sind nicht durch Streichung erreichbar, sondern
durch Kategorie-Zusammenfassung. Beispiel: 7 planner_resume_*
-Varianten -> 1 planner_resume_fehler mit Unterfeld grund.

Ohne Zusammenfassung:
- 166 -> ~159 durch Streichung der 7 planner_resume_*
  (Charge 1a).
- 42 getestete Fehlerpfade bleiben als eigene Kinds.
- 166 -> 20 ist nicht erreichbar ohne Code-Aenderung
  an audit()-Aufrufern.

Mit Zusammenfassung (Phase 3, wenn Loop neu):
- 166 -> 20 in einem Schritt, aber mit Code-Aenderung,
  nicht nur Katalog-Kuerzung.

## Charge-1a — Loeschung der 7 planner_resume_*

Diese 7 sind ungetestet UND sterben mit Phase 3
(Planner-Resume faellt). Vorwegnahme des Rollen-Endes,
kein funktionaler Verlust.

Liste:
- planner_resume_mehrfach_split_verboten
- planner_resume_misch_zustand
- planner_resume_order_verletzt
- planner_resume_rename_verboten
- planner_resume_split_cap_erreicht
- planner_resume_split_depth
- planner_resume_split_done_verboten

_KATALOG_SOLL: 166 -> 159.

## Charge-1b — 42 getestete schweigende Kinds behalten

Begruendung: Fehlerpfade, die getestet sind, sind nicht
Ballast. Kategorie-Zusammenfassung in Phase 3.

## Charge-1c — Kategorie-Zusammenfassung (Phase 3)

Wenn Loop neu gebaut ist, Zusammenfassung auf 20 Kinds:
- planner_resume_* -> 1
- recovery_* -> 1
- timeout_* -> 1
- rollback_* -> 1
- apply_* -> 1
- judge_* -> 1
- phase_* -> wenige
- builder_* -> wenige
- command_* -> 1
- pipeline_* -> wenige

## Abhaengigkeit von Reviewer-Gates

Gate 5 (offen): 20-Ziel als Phase-1-Ziel (B) oder
  Phase-3-Endziel (A)?
Gate 6 (offen): Kategorie-Zusammenfassung als Phase-3-
  Aufgabe bestaetigt?

Bau-Empfehlung: A + Gate 6 BESTAETIGT.
