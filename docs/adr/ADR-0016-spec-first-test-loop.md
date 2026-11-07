# ADR-0016: Spec-First Test-Loop — Tests vor Code

- **Datum:** 2026-11-07
- **Status:** proposed
- **Ergaenzt:** ADR-0015 (Tests sind Specs), OP-260 (Loop-Agenten mit Kontext-Vertrag)

## Kontext

Loop-Laeufe mit Test-Bau (Loop-Test 8, 9, 10; OP-181, OP-183) zeigen
dasselbe Muster:

1. Planner baut Tasks mit `task_files` inkl. `tests/test_*.py`
2. Builder schreibt Code + Test im selben LLM-Call
3. Test "bestaetigt" den Code, weil beide aus derselben Trajektorie
   stammen
4. Spec-Abweichungen werden nicht erkannt — Code und Test sind sich
   gegenseitig treu, aber der Spec untreu

**Messung 2026-11-07 (Benchmark):** Auf einem Mini-Modul mit 4
Funktionen und 4 naiven Tests hat `pytest-gremlins` 18 Mutanten
erzeugt, 3 ueberlebten die Test-Suite (17%). Zwei `max_of`/`clamp`-
Grenzfaelle (`x == lo`, `x == hi`) sind nicht getestet. Die Tests
sind gruen, aber unvollstaendig.

**Kernproblem:** Es gibt keine Qualifikations-Schwelle fuer Tests.
Ein gruener Test gilt als guter Test, auch wenn er den Ist-Zustand
statt den Soll-Zustand beschreibt.

## Entscheidung

**Tests werden vor dem Code gebaut, eingefroren und gegen den
unveraenderten Code qualifiziert.**

Konkret:

1. **Architect liefert `test_spec`** (Block 6 im `ARCHITECT_SYSTEM`):
   `[{name, target_file, assertion_prose}]`. Kein Test-Code, nur
   Test-Namen + Assertion-Beschreibung. Pro Akzeptanzkriterium ein
   Test.

2. **Neue Phase `_phase_test_loop`** laeuft nach Planner, vor
   Builder. Der Test-Agent baut Tests aus `test_spec`.

3. **Qualification:** Tests MUESSEN auf unveraendertem Repo rot sein
   (sonst testen sie den Ist-Zustand). Max 2 Runden, dann
   Human-Gate.

4. **Freeze:** SHA256 ueber alle Test-Dateien in
   `state.test_manifest`.

5. **Builder wird test-blind:** `task_files` mit `tests/` oder
   `test_*.py` werden rausgefiltert. Wenn nach Filter leer:
   fail-closed mit Audit-Event.

6. **Neue verify-Stages:** `test_integrity` (SHA256-Check),
   `test_must_fail_initial` (Qualification), `mutation_gate`
   (pytest-gremlins, `hart: false` im ersten Rollout).

7. **Test-Thaw bei Bedarf:** Wenn Code-Loop scheitert und
   Code-Bug vs. Test-Bug unklar bleibt, entscheidet der Debugger
   (ADR-0018). Test-Thaw ist auditierbar (`test_thawed`-Event) und
   invalidiert `state.test_manifest`.

## Konsequenzen

**Positiv:**
- Tests sind Spec, nicht Attrappe.
- Builder kann nicht "code to the test" betreiben.
- Mutation-Gate deckt unvollstaendige Tests auf.
- Debugger bekommt eindeutige Signale (Code-Bug vs. Test-Bug).

**Negativ / Trade-offs:**
- Mehr LLM-Calls pro Loop-Lauf (Test-Agent + Code-Agent).
- Laengere Laufzeit (+30-60s pro OP mit Tests).
- Test-Thaw ist ein zusaetzlicher Human-Gate-Zyklus.
- Architect muss `test_spec` praezise formulieren — Qualitaetsrisiko.

**Nicht abgedeckt:**
- Property-Based Tests (Hypothesis) — OP-215.
- Cross-Modul-Property-Tests — eigene OP.
- Test-Agent-Qualitaet selbst — nur durch Mutation-Gate messbar.

## Verweise

- ADR-0015 (Tests sind Specs, 2026-11-06)
- ADR-0017 (Mutation-Gate mit pytest-gremlins)
- ADR-0018 (Debugger als eigene Rolle)
- OP-260 (Loop-Agenten mit Kontext-Vertrag)
- OP-210 (Test-Loop-Phase)
- OP-211 (Builder test-blind + verify-Stages)
- OP-214 (Mutation-Gate)
- Messung: /tmp/mutbench Benchmark, 2026-11-07

## Nachtrag 2026-11-07 (Punkt 1 + 2 aus externem Review)

### Testblindheit technisch erzwingen

Die reine Prompt-Regel "Builder sieht tests/ nicht" ist zu schwach.
Zusaetzlich:

- **Tool-Trennung:** Builder-Tool-Registry hat keinen Zugriff auf
  `read_file(tests/**)` oder `apply_patch(tests/**)`. Fail-closed
  mit Audit `builder_test_access_denied`.
- **Keine Offenlegung via Feedback-Kanaele:** pytest-Fehlermeldungen
  koennen Test-Code leaken (Assertion-Messages). Reflection-Prompt
  bekommt bei Test-Fail nur: `stage`, `error_class`, `test_id` —
  NICHT den Assertion-Text.
- **Manifest ausserhalb Builder-Zugriffs:** `state.test_manifest`
  wird vom Test-Loop geschrieben, Builder hat nur Leserecht auf
  die *Existenz*, nicht den Inhalt.
- **Integritaets-Verify:** `test_integrity`-Stage prueft SHA256
  gegen aktuellen Test-Code. Bei Mismatch: fail-closed, kein Commit.
- **Audit:** jeder Manipulationsversuch (Patch auf tests/,
  read_file auf tests/, SHA256-Mismatch) erzeugt Audit-Event.

**Abnahme:** Automatisierte Tests weisen nach, dass Builder weder
lesen noch schreiben kann.

### Test-Spec unabhaengig validieren

Architect und Test-Agent sind beide LLMs, koennten dieselbe falsche
Interpretation der Anforderung uebernehmen. Konsequenz: technisch
korrekte Tests, die falsches Verhalten bestaetigen.

Gegenmassnahme:

- **Original-Anforderung** (OP-Text) bleibt als Referenz erhalten
  in `state.original_requirement`.
- **Architect** erstellt `test_spec` aus der Anforderung (Block 6).
- **Unabhaengige Validierung** (eigener LLM-Call, eigener Prompt)
  prueft: deckt `test_spec` die Anforderung vollstaendig ab? Fehlen
  Negativ-Faelle? Sind AK pruefbar formuliert?
- **Mehrdeutigkeit** fuehrt zu Human-Gate VOR Implementierung,
  nicht zu Loop-Fail.
- **Struktur der test_spec** erweitert:
      {
        "requirement_id": "OP-NNN",
        "acceptance_criteria": [
          {"id": "AC-NNN", "condition": "...", "verification": "..."}
        ],
        "negative_cases": ["...", "..."]
      }

**Abnahme:** Test-Spec ist auf Original-Anforderung rueckverfolgbar.
Kritische AK werden nicht allein durch dieselbe Agenteninterpretation
bestaetigt.

**Neue OP:** OP-212 (Test-Spec-Validator).
