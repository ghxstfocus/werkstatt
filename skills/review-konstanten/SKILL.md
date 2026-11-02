---
name: review-konstanten
description: |
  Konstanten-Check: Task-Zahlen muessen als Literal im Diff auftauchen (R-CHECK-1).
globs:
  - "**/*.py"
rollen:
  - reviewer
---

# review-konstanten

## KONSTANTEN-CHECK (HIGH-Bug, R-CHECK-1)

- Wenn die Task eine numerische Konstante nennt (z.B. `limit=10`,
  `max_retries=3`, `timeout=60`): pruefe, ob der Diff diese Zahl
  WOERTLICH enthaelt.
- Wenn der Diff eine ANDERE Zahl nutzt (`limit=5` statt `limit=10`):
  HIGH-Bug, reject. Auch wenn der Diff ansonsten korrekt aussieht.
- Wenn die Task eine Zahl nennt, der Diff sie aber NICHT setzt
  (z.B. `limit` unveraendert laesst): HIGH-Bug, reject.
- Wenn die Task KEINE Zahl nennt: ignorieren, kein Bug.
- Belege die Zahl im `description`-Feld: "Task fordert X=10,
  Diff nutzt X=5".
