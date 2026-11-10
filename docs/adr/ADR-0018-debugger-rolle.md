# ADR-0018: Debugger als eigene Rolle

- **Datum:** 2026-11-07
- **Status:** rejected (2026-11-10; siehe ADR-0011 und ADR-0029)
- **Ersetzt teilweise:** OP-092 Sub-Item 092d (Debugger als Teil
  des Sammel-OPs)

## Kontext

`systematic-debugging` ist heute als Skill registriert:

- In `skills/systematic-debugging/SKILL.md`: `rollen: [builder]`
- In `werkstatt/rollen.py`: `ROLLEN["reflection"].skills =
  ("systematic-debugging",)`
- In `werkstatt/reflection.py:993-994`: `_skill_body_fuer_reflection`
  laedt es fuer Reflection.
- Builder hat `skill_filter_rolle="builder"` und laedt es damit auch.

**Das ist konzeptionell falsch.** Ein Skill namens
"systematic-debugging" sollte nicht im Builder laufen (der baut
Code, nicht debuggt ihn) und nicht in Reflection (die probiert
Fixes, ohne Root-Cause zu suchen). Debugging ist eine eigene Rolle
mit eigenem System-Prompt und eigener Verantwortung.

Zusaetzlich: Der Ausbau des Debuggers (Erfahrungs-Gehirn,
Repair Ladder) ist ein umfangreiches Feature (OP-128, OP-160),
das als eigenstaendige Rolle besser skalierbar ist als als
Skill-Anhang zum Builder.

## Verworfener Vorschlag

Der Vorschlag einer separaten Loop-Rolle `debugger` wird nicht
angenommen. ADR-0011 waehlt den Debugger als Chat-Modus; ADR-0029
bestaetigt Chat als Koordinator und den Coding-Loop als ausfuehrenden
Pfad. Die hier beschriebenen 3-Wege-Checks und Test-File-Guards sind
als moegliche Anforderungen fuer den Debugger-Modus zu pruefen, aber
begründen keine eigene Rolle.

`systematic-debugging` bleibt bis zu einer neuen akzeptierten
Architekturentscheidung beim bestehenden Skill-/Reflection-Vertrag.
Die Zuordnung darf nicht allein aufgrund dieses verworfenen ADRs
aus Builder oder Reflection entfernt werden.

## Entscheidung

Kein separates `debugger`-Rollenobjekt und keine Verdrahtung als
Loop-Phase. Debugging wird als Chat-Faehigkeit gemaess ADR-0011/OP-240
umgesetzt; schreibende Codearbeit wird nach expliziter Chat-Freigabe an
den normalen Coding-Loop uebergeben (ADR-0029).

Die folgenden Rollen-, Verdrahtungs- und Testdetails dokumentieren den
verworfenen Vorschlag und sind keine aktive Implementierungsanforderung.

**3-Wege-Check (aus OP-092 Z.114-118):**
- Spec <-> Code <-> Test
- Code != Spec, Test = Spec -> Fix Code (Test hatte recht)
- Code = Spec, Test != Spec -> Human-Gate (Test falsch, nicht
  still patchen)
- Alle = Spec, Test rot -> Human-Gate (Infra/flaky/env)

**Test-File-Guard:** Debugger-Patch auf Test-Datei nur erlaubt bei
(a) syntaktischem Fehler, (b) Human-Gate-Freigabe. Sonst
`debugger_test_patch_blocked`-Audit.

**Max 3 Runden, dann Human-Gate.**

**Verdrahtung:** In `phases/tasks.py` bei `_verify_patches` rot UND
`_reflection_loop` bereits 1x ohne Erfolg -> Debugger statt
Reflection.

**Rollenzuordnung im Detail:**
- `ROLLEN["debugger"].skills = ("systematic-debugging",)`
- `ROLLEN["builder"].skill_filter_rolle`: Builder laedt
  `systematic-debugging` NICHT mehr.
- `ROLLEN["reflection"]`: `systematic-debugging` aus der Skill-
  Liste entfernen. Reflection behaelt die Reflection-Loop-
  Logik, aber ohne Debugging-Skill.

## Historische Abwaegung (Vorschlag nicht umgesetzt)

**Positiv:**
- Debugging bekommt eigene Verantwortung.
- Test-File-Guard verhindert stillen Test-Patch.
- 3-Wege-Check trennt Code-Bug von Test-Bug.
- Platz fuer Repair Ladder (OP-128) und Erfahrungs-Gehirn
  (OP-160/OP-113).

**Negativ:**
- Neue Rolle -> mehr LLM-Calls.
- Debugger braucht Spec-Kontext (abhaengig von OP-188).
- Cross-Role-Verdrahtung in `phases/tasks.py` komplex.

**Ausbau (OP-160):** Debugger-Fixes ins Erfahrungs-Gehirn
(OP-113). Aktuell blockiert durch OP-113.

## Verweise

- ADR-0016 (Spec-First Test-Loop)
- OP-092 (Loop-Agenten mit Kontext-Vertrag, Spec-Quelle fuer
  3-Wege-Check)
- OP-191 (Debugger-Rolle)
- OP-192 (Test-Thaw-Mechanik)
- OP-128 (Chat-Modus Debugger, blockiert von OP-124/125/127)
- OP-160 (Debugger-Lern-Loop, blockiert von OP-128)
- OP-113 (Erfahrungs-Gehirn)
