---
name: mypy-typing
description: |
  mypy-Typ-Narrowing mit typing.cast NACH Runtime-Check. Kein int(x), kein type:ignore.
globs:
  - "**/*.py"
rollen:
  - builder
---

# mypy-typing

Wenn mypy Fehler der Form 'Unsupported operand types for ... int and object'
oder 'No overload variant of int matches argument type object' meldet:

- NIEMALS int(x) schreiben. Das aendert den Laufzeit-Wert: aus '10' wird 10,
  aber aus 'abc' wird ein ValueError.
- NIEMALS type:ignore verwenden. Wird von OP-064b als Antipattern geblockt.
- NUR typing.cast(int, x) NACH einem Runtime-Check verwenden. Der Runtime-
  Check (isinstance(x, int), check_port(x) oder ein aequivalenter Guard)
  garantiert zur Laufzeit int, aber mypy sieht das nicht. cast macht die
  Narrowing-Absicht fuer den Typechecker explizit, ohne den Wert zu aendern.

Beispiel: aus 'return min_port <= port <= max_port' wird
'return min_port <= cast(int, port) <= max_port' — nach check_port(port)
als Runtime-Guard. NICHT int(port) und NICHT type:ignore.
