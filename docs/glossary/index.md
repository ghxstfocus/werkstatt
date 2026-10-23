# Glossar — Werkstatt

Fachbegriffe und M-Nummern. Alphabetisch sortiert.
M-Nummern: ausfuehrliche Lehre in `../MERKPOSTEN.md`.

## Fachbegriffe

**Anker** — Eindeutiger String im Code, an dem ein Patch
eingefuegt wird. `count(anker) == 1` Pflicht.

**Audit-Kind** — String, mit dem ein Ereignis in `.werkstatt/audit.log`
protokolliert wird. Katalog in `pipeline.py:521` (`_KATALOG_SOLL`).

**Baseline** — Verbindliche Soll-Werte: pytest 1259, ruff 14,
mypy 8, AST 6, Katalog 162. Siehe `../HANDOFF-BASELINE.md`.

**Builder** — Rolle, die Code-Patches baut. `agents/builder*.md`.

**C-Nummerierung** — Zerlegung von `run_pipeline` in 10 logische
Bloecke (C0..C9). Doku-Konvention, nicht Code-Reihenfolge.

**Deadlock** — Zyklische Abhaengigkeit zwischen `run_phase`-Aufrufen.
Sicherung zweistufig: `_phase_wiederaufnahme` (Z.2547/2566) +
`_phase_main_plan_verarbeiten` (force_new_phase-Korrektur).

**Diaetaxis** — Vier Doku-Typen: Tutorial, How-to, Reference,
Explanation. Siehe `../INDEX.md`.

**Judge** — Rolle, die Code gegen Contract prueft. `agents/judge.md`.

**Katalog** — Menge aller Audit-Kinds, gegen die `audit("kind", ...)`
pruefen muss. `_KATALOG_SOLL` in `pipeline.py`.

**M-Nummer** — Merkposten-Nummer (M-58, M-72, M-186, ...).
Jede Nummer = eine Lehre. Siehe `../MERKPOSTEN.md`.

**Planner** — Rolle, die Plaene formuliert (Stufe 1/2).
`agents/planner.md`.

**Return-Bilanz** — Anzahl Returns pro Funktion. Wird bei jeder
Extraktion als Liste dokumentiert (M-70/M-73).

**SOPS + age** — Key-Architektur. Key liegt verschluesselt in
`secrets.enc.yaml`, age-Key in `~/.config/sops/age/keys.txt`.
Siehe `../KEY-ARCHITEKTUR.md`.

**Skill** — Wiederverwendbares Rollen-Modul. `skills/*/SKILL.md`
mit Frontmatter `name` + `description`.

**W36-Mock** — Schutz-Mechanismus in Tests, der `subprocess.run`
auf Tupel-Argumente prueft. Siehe M-194.

## M-Nummern (Auswahl)

**M-57** — Body-VOR-Werte pro Commit in `SESSION-BILANZ.md`.

**M-70/M-73** — Return-Bilanz als Liste, nicht als Summe.

**M-72** — Semantik-Beweis bei Extraktion: jeder Return behaelt
Wert und Bedingung.

**M-74** — Herkunft neuer Returns nach Extraktion.

**M-142** — Marker-Zuordnung nur mit Repro, nicht per Sichtpruefung.

**M-148** — 0 fruehe Returns in 2a: 1 finaler Return.

**M-151** — Return-Bilanz-Korrektur nach 3a-3 (123 global).

**M-155** — Test-Funktionen, nicht Assert-Zeilen zaehlen.

**M-156** — `_phase_main_w50_gate` 4 Returns (3 + mypy-Fallback).

**M-158** — `1837/1838` sind in `_vorlauf_und_state`, nicht in
`_phase_main_pfad`.

**M-163** — C6-Grenze: Z.8807-8852 @64d9318, nicht 8557-8600.

**M-171** — C6-Code = 8807-8849 (43 Z.), nicht 8807-8850 (44 Z.).

**M-186** — Z.3269 env-Leak (latent, weil Key nicht in os.environ).

**M-193** — tuple(args) in `werkstatt/exec.py` (W36-Mock).

**M-194** — Merkposten: W36-Mock auf list|tuple erweitern (3b).

**M-198** — Destruktive git-Befehle bleiben explizit in Aufrufzeilen.

**M-201/M-202** — 5 tote Audit-Kinds gestrichen, Kandidaten-Erkennung
vollstaendig.

**M-203** — Key-Architektur SOPS + age.

**M-204** — Test, der Commit-Autor prueft, darf nicht auf globalen
git-config vertrauen.

**M-206** — Baseline 1245 -> 1259 (A3: 14 Skill-Tests).
