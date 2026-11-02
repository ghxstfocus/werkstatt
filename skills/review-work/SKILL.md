---
name: review-work
description: |
  Bewertung von Code-Patches gegen einen Auftrag.
  Information-isolated verification: nur contract,
  mess_nach und test_results. Nutze diese Skill immer,
  wenn du als Judge pruefst. Sie ist statisch im
  Judge-Prompt.
rollen:
  - reviewer
---

# Review-Work

## Was der Judge sieht
- contract.md (was gebaut werden soll).
- mess_nach.txt (was tatsaechlich gebaut wurde).
- basis_gate_test_results (Tests, Linter).

## Was der Judge NICHT sieht
- code_entwurf (Builder-Prompt).
- mess_protokoll (Builder-Messungen vor Apply).
- basis_protokoll (Basis-Gate vor Apply).

## Verdict
- GO: Contract erfuellt, Tests gruen, Linter sauber.
- NO-GO: Contract nicht erfuellt ODER Tests rot ODER Linter rot.
- Bei NO_GO: Problem-Liste (max 5 Punkte), konkret.

## Regeln
1. Pruefe Contract-Punkt fuer Contract-Punkt.
2. Zitiere konkrete Zeilen/Regeln, keine Prosa.
3. Kein eigener Code. Kein eigener Fix.

## MARKDOWN-PATCHES (OP-079)

Bei `.md`-Dateien (STATUS.md, ROADMAP.md, PROGRESS.md) gilt:

- Der `@@`-Hunk-Header (z.B. `@@ -294,7 +294,6 @@ DB-Reset...`) ist 
  git-Kontext aus dem umgebenden Text. Er gehoert NICHT zur Task-Description.
- Pruefe Auftrag-Treue **nur** anhand der `+`- und `-`-Zeilen.
- Beispiel: Der Diff landet im Bereich "DB-Reset", fuegt aber
  `### OP-074: Web-Backend` ein. Das ist KEIN Auftrag-Treue-Verstoss, 
  sondern ein normaler Patch am Ende eines Blocks.
- Nur wenn die `+`/`-`-Zeilen inhaltlich nicht zur Aufgabe passen, ist es
  ein HIGH-Bug.

## PYTHON-PATCHES (OP-080)

Bei `.py`-Dateien gilt fuer Route-/Handler-Pruefungen:

- Route-Handler stehen oft verschachtelt in einer App-Factory
  (z.B. `def create_app(): @app.get(...) def foo(): ...`).
- Pruefe den **woertlich genannten Pfad** aus der Task-Beschreibung
  gegen die `+`-Zeilen des Diffs (z.B. suche nach `"/api/projects/{name}/state"`).
- Erfinde KEINE Routen, die nicht im Diff stehen. Wenn der Task sagt
  "GET /api/projects/{name}/state fehlt", dann pruefe, ob genau dieser
  String in den `+`-Zeilen vorkommt — nicht ob der Handler-Name passt.
- Ein `@app.get("/api/projects/{name}/state")` in einer verschachtelten
  Funktion ist eine gueltige Route. Die Verschachtelung ist kein Bug.
- Wenn im Diff nur die 3 geforderten Routen stehen und du "Over-Delivery"
  oder "fehlt" meldest: pruefe deine Annahme, bevor du den Bug setzt.

## DATEI-PATCHES: Hunk-Header-Ignorieren (OP-079-Nachtrag)

Fuer alle Patches (`.md` und `.py`) gilt zusaetzlich:
- Der `@@ -X,Y +A,B @@ <text>`-Header beschreibt den umgebenden Kontext,
  nicht die semantische Zuordnung des Patches.
- Bei `docs/STATUS.md` (OP-079): nur `+`/`-`-Zeilen zaehlen.
- Bei `.py`: nur den Code in `+`-Zeilen pruefen. `@@`-Anker ignorieren.

