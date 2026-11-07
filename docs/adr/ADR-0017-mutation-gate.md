# ADR-0017: Mutation-Gate mit pytest-gremlins

- **Datum:** 2026-11-07
- **Status:** proposed

## Kontext

Ein gruener Test garantiert nicht, dass er Spec-Verhalten prueft.
Ein Test kann zu schwach sein (testet Ist-Zustand) oder zu
spezifisch (bricht bei Refactoring ohne Verhaltensaenderung).

Mutation-Testing ist der einzige mechanische Test-Quality-Check:
Es mutiert den Code systematisch (Vergleiche, Rueckgaben,
Bedingungen) und prueft, ob ein Test die Mutation faengt.

**Messung 2026-11-07:** Auf einem Mini-Modul (4 Funktionen,
4 naive Tests) hat `pytest-gremlins` 18 Mutanten erzeugt:
- 15 zapped (83%)
- 3 survived (17%) — Grenzfaelle in `max_of`/`clamp`
- Laufzeit: 6s fuer Mini-Modul

Die Werkstatt-Test-Suite hat ~197 Test-Dateien mit ~1364 Tests.
Hochgerechnet: ~120s fuer die vollstaendige Suite. Mit
`--changed`-Filter auf geaenderte Files eines Tasks: 10-30s pro
Task.

## Tool-Vergleich

| Tool | Version | Status | Integration | Laufzeit (Benchmark) |
|---|---|---|---|---|
| **pytest-gremlins** | 1.13.2 | stable | native pytest | 6s |
| cosmic-ray | 8.7.0 | stable | CLI, Celery-Optional | ConfigError beim Benchmark |
| mutmut | 3.5 | stable | CLI, fork-based | nicht getestet |
| Poodle | akademisch | nicht produktionsreif | — | — |

**Entscheidung:** pytest-gremlins.

Gruende:
- Native pytest-Integration — Werkstatt nutzt pytest ohnehin,
  keine zusaetzliche CLI-Konfiguration noetig.
- Mutation Switching statt fork-basiertem Neuladen — schnell
  genug fuer "pro Task".
- Incremental Cache (in v1.13.2).
- Aktive Entwicklung (regelmaessige Releases 2026).

**Cosmic-ray** waere reifer, aber:
- ConfigError in isoliertem venv (Benchmark gescheitert).
- CLI-basiert, weniger pytest-nativ.
- Fuer den Loop nicht noetig.

## Entscheidung

**Mutation-Gate als eigene verify-Stage, `hart: false` im ersten
Ausrollen.**

Konkret:

1. Neue Stage `mutation_gate` in `.werkstatt/verify.json`:
   `command: ["python3", "-m", "pytest", "--gremlins"]`,
   `phase: "post_build"`, `timeout: 120`, `hart: false`.

2. **Scope:** Nur geaenderte Prod-Dateien des Tasks. Ueber
   `[tool.pytest-gremlins].paths` in `pyproject.toml` gesteuert,
   dynamisch pro Task gesetzt.

3. **Ergebnis-Behandlung:**
   - `zapped / total >= 0.8`: OK, weiter.
   - `zapped / total < 0.8`: Audit-Event `mutation_gate_low_score`,
     **kein Hard-Block** in Runde 1 (Pre-release-Erfahrung sammeln).
   - Nach 4 Wochen stabil: `hart: true`.

4. **Override:**
   - Test-Thaw durch Debugger (ADR-0018) invalidiert den Score.
   - Manueller `--skip-mutation`-Flag im Loop fuer dringende Laeufe.

## Konsequenzen

**Positiv:**
- Test-Qualitaet wird mechanisch gemessen.
- Unvollstaendige Tests werden sichtbar.
- Test-Agent-Output wird qualitativ bewertet.

**Negativ / Trade-offs:**
- +10-30s pro Task mit Tests.
- pytest-gremlins hat Grenzen (z.B. async-Code).
- Score-Schwelle (0.8) ist willkuerlich — muss sich in der Praxis
  zeigen.

**Nicht abgedeckt:**
- Equivalence-Mutationen (Mutanten, die verhaltensgleich sind).
- Property-Based-Tests als zusaetzliche Quelle.

## Verweise

- ADR-0016 (Spec-First Test-Loop)
- pytest-gremlins: https://github.com/smartt/pytest-gremlins
- Benchmark: /tmp/mutbench, 2026-11-07
- OP-214 (Mutation-Gate als verify-Stage)

## Nachtrag 2026-11-07 (Punkt 5 aus externem Review)

### Mutation-Report aussagekraeftiger

Score allein ist zu wenig. Zusaetzlich speichern:

- Anzahl erzeugter Mutationen
- Anzahl erkannter (zapped) Mutationen
- Anzahl ueberlebender (survived) Mutationen
- **Art der ueberlebenden Mutationen** (comparison, arithmetic, boundary)
- **Betroffene Dateien und Funktionen** (welche Stelle im Code)
- **Nicht ausreichend abgedeckte Anforderungen** (Rueckbezug auf AC-NNN)
- **Gruende fuer nicht ausfuehrbare Mutationen** (timeout, syntax, os)

### Rollout-Strategie konkretisiert

- **Woche 1-2:** `hart: false`, Score wird auditiert, nicht blockiert.
  Ziel: Baseline der ueberlebenden Mutanten pro Modul verstehen.
- **Woche 3-4:** `hart: false`, aber Warnung im Commit-Gate bei
  Score < 0.8 (Mensch sieht es, entscheidet).
- **Nach 4 Wochen:** Entscheidung ueber `hart: true` anhand realer
  Daten. Kriterien: Score stabil? Ueberlebende Mutanten alle
  bewertet? False-Positives bekannt?

### Neue Audit-Events

- `mutation_gate_low_score` mit Detail-Report
- `mutation_gate_survived` mit Datei, Funktion, Mutant-Typ
- `mutation_gate_skipped` (timeout, nicht ausfuehrbar)

**Neue OP:** OP-214-AK erweitert (Report-Struktur + Rollout).
