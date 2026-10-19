# Neubau — Entfernungs-Register

Stand: 2026-10-19
Status: laufend. Wird bei jeder Modul-Extraktion ergaenzt.
Zweck: Festhalten, was im Zielsystem NICHT mehr existiert.
Verhindert, dass wir den Ueberblick verlieren (Befund BK).

## Format

Pro Eintrag:
- Was: Funktion / Konstante / Modul / Audit-Kind.
- Wo jetzt: Datei:Zeile.
- Warum entfernen: Grund (Explore, Hooks, AGENTS.md,
  state.json, etc.).
- Wann entfernen: Phase 3a / 3b / 3c / 5 / 6 / 7.
- Ersatz: was uebernimmt die Aufgabe.

## Register

### Anti-Patterns-Komplex (Befund BK, 2026-10-19)

Was jetzt in pipeline.py liegt, aber im Zielsystem nicht mehr
gebraucht wird:

| Was | Wo jetzt | Warum entfernen | Wann | Ersatz |
|---|---|---|---|---|
| _anti_pattern_block (43 Z.) | pipeline.py:1303-1345 | Prompt-Blockade durch Hooks (PreToolUse) ersetzt | Phase 3b | hooks.py (mypy/ruff-Gate blockiert) |
| anti_patterns_fuer (51 Z.) | pipeline.py:1215-1266 | Rolle+Trigger-Filter: mit Hooks nicht mehr noetig | Phase 3b | AGENTS.md (deklarative Regeln) |
| lade_anti_patterns (34 Z.) | pipeline.py:1179-1212 | Liest katalog.yaml. Wird zu incidents.py (append-only) | Phase 3c | incidents.py (wenn Incident-Log) |
| _ap_kuerzen (4 Z.) | pipeline.py | Hilfsfunktion fuer _anti_pattern_block | Phase 3b | entfaellt mit _anti_pattern_block |
| _AP_BESCHREIBUNG_MAX (1 Z.) | pipeline.py | Konstante fuer _anti_pattern_block | Phase 3b | entfaellt mit _anti_pattern_block |
| build_system_prompt (45 Z.) | pipeline.py | Ruft _anti_pattern_block. Wird zu prompts.py (Phase 3) | Phase 3b | prompts.py (ohne Anti-Pattern-Block) |

**Nicht entfernen, sondern verschieben (Phase 3):**
- gegenstand_gleich (50 Z.): ruft jaccard, tokenisiere. Kein
  Anti-Pattern-Komplex, sondern Objekt-Vergleich. Bleibt,
  evtl. eigene Datei.

**Was bleibt trotz Anti-Pattern-Bezug:**
- _ap_audit_haeufigkeit: liegt in audit.py, zaehlt
  Audit-Haeufigkeiten. Wird fuer incidents.py gebraucht
  (Sortierung). Bleibt.

### Was das fuer die Extraktion bedeutet

build_system_prompt bleibt in pipeline.py bis Phase 3b,
weil es _anti_pattern_block ruft. prompts.py enthaelt
die anderen 7 Prompt-Funktionen (Befund BK).

Nach Phase 3b (Hooks eingebaut):
- _anti_pattern_block entfaellt.
- build_system_prompt kann nach prompts.py wandern
  (ohne Anti-Pattern-Block).
- anti_patterns_fuer entfaellt (AGENTS.md).

Nach Phase 3c:
- lade_anti_patterns -> incidents.py oder entfaellt.


### Nachtrag 2026-10-19 — Befund BO/BP (prompts.py)

| Was | Wo jetzt | Warum entfernen | Wann | Ersatz |
|---|---|---|---|---|
| build_system_prompt (45 Z.) | pipeline.py | Ruft _anti_pattern_block (Anker). Nach Anti-Pattern-Abloesung nach prompts.py. | Phase 3b/6 | prompts.py (ohne Anti-Pattern-Block) |
| _anti_pattern_block (43 Z.) | pipeline.py:638 | Prompt-Blockade durch Hooks ersetzt | Phase 3b | hooks.py (PreToolUse: mypy/ruff-Gate blockiert) |

**Zaehl-Klaerung A-4:**
prompts.py-Auftrag in Gate 18B: 21 Funktionen.
Aufteilung nach Messung:
- 8 in prompts.py (extrahiert, 7f51a63).
- 12 in commit_input.py (naechster Schritt).
- 1 build_system_prompt (pipeline.py, Befund BO).
Summe: 21.
