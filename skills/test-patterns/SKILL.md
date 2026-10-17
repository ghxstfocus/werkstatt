---
name: test-patterns
description: |
  Muster fuer Unit-Tests. Ein Test = ein Verhalten,
  mocke externe Abhaengigkeiten, pruefe Verhalten
  statt Implementierung. Use when writing or
  reviewing tests.
---

# Test-Patterns

## Grundregeln
1. Ein Test = ein Verhalten.
2. Mocke externe Abhaengigkeiten (DB, HTTP, FS).
3. Pruefe Verhalten, nicht Implementierung.
4. Test-Namen: test_<verhalten>_<bedingung>.

## Beispiel (pytest)
def test_apply_merged_dict(tmp_path):
    (tmp_path / "x.py").write_text("a: 1\n")
    applier = ChangeApplier(tmp_path / "x.py", tmp_path / "backup")
    applier.apply(make_change({"a": {"b": 2}}))
    assert read_yaml(tmp_path / "x.py") == {"a": {"b": 2}}

## Anti-Patterns
- assert True (wertlos)
- Nur Listen-Vergleich bei __all__ (bricht bei Sortierung)
- Test ohne Assertion
