---
name: review-work
description: |
  Bewertung von Code-Patches gegen einen Auftrag.
  Information-isolated verification: nur contract,
  mess_nach und test_results. Nutze diese Skill immer,
  wenn du als Judge pruefst. Sie ist statisch im
  Judge-Prompt.
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
