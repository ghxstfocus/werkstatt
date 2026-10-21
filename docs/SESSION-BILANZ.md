# SESSION-BILANZ — Nachweise Body-VOR-Werte (M-57)

Stand: 2026-10-21, HEAD b352d54. Branch umbau/phase-2.

## Zweck (M-57)

Fuer jeden Commit mit Body-VOR-Wert muss der Vor-Comm (die SHA, gegen
die der VOR-Wert gemessen wurde) im Body oder in einem Nachweis-
Dokument referenziert sein. History-Rewrite ist nicht erlaubt; dieser
Nachweis belegt die Vor-Comm-SHA pro Commit eindeutig.

## Nachweise

### ae25e08 — 3a-1c-2b: AQ-Vorspann B7/B8 + 6887-Verhaltens-Test

- Vor-Comm: **ecf35a4** (nicht im Body referenziert, M-57)
- Stat: tests/test_pipeline_integration.py, 98 insert / 2 delete
- VOR-Werte im Body (Zitate):
  - "B7: VOR C7-Rumpf @ 8671-8673. NACH W2."
  - "B8: VOR C7-Rumpf @ 8675-8679. NACH W2."
  - "VOR/NACH: Reviewer-Aufruf 1 (C1) Mess-Wahl, Reviewer-Aufruf 2 (W2)"
- Beleg: Zeilennummern 8671-8679 im Vor-Comm ecf35a4.
  Verifikation: `git show ecf35a4:pipeline.py | sed -n '8671,8679p'`

### 277029f — refactor(3a-1c-2b): W2-Extraktion _commit_review_w25_loop

- Vor-Comm: **6e11718** (nicht im Body referenziert, M-57)
- Stat: pipeline.py, 181 insert / 176 delete
- VOR-Werte im Body: keine (Extraktion ohne VOR/NACH-Anker)
- Beleg: Reine Extraktion, kein Zeilenbereich behauptet. Body nennt
  Funktion, Parameter, Returns. Kein VOR-Wert zu belegen.
  M-57-Pflicht entfaellt fuer diesen Commit — der Body enthaelt
  keine Vor-Aussage, die einen Commit-Bezug braucht.

### 5762d8e — refactor(3a-1c-4): C8+C9 extrahiert

- Vor-Comm: **75f844b** (im Body referenziert: "75f844b")
- Stat: pipeline.py +178/-95, tests +48
- VOR-Werte im Body:
  - "Extrahiert aus run_pipeline Z. 8819-8898 (HEAD 75f844b)"
- M-57-konform. Kein Nachzug noetig.

### b352d54 — docs(3a-1c-4): Doku-Nachzug

- Vor-Comm: **5762d8e** (im Body referenziert)
- Stat: 5 Doku-Dateien, 61 insert / 18 delete
- VOR-Werte im Body: keine (reiner Doku-Commit)
- M-57-konform (kein VOR-Wert, keine Pflicht).

## Ergebnis

- **Nachzug erledigt** durch dieses Dokument fuer `ae25e08`
  (Vor-Comm `ecf35a4`).
- **Kein Nachzug noetig** fuer `277029f` (kein VOR-Wert im Body),
  `5762d8e` (Body nennt `75f844b`), `b352d54` (Doku, kein VOR-Wert).

## Konsequenz fuer kuenftige Commits

Jeder neue Commit mit Body-VOR-Wert MUSS die Vor-Comm-SHA im Body
nennen (z.B. "VOR 8671-8679 gegen <sha>"). Sonst M-57-Verstoss.
