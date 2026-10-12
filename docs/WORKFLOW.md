# Werkstatt — Workflow

Regeln fuer die Entwicklung der Werkstatt selbst.
Nicht zu verwechseln mit den HR-Regeln der Agenten
(die stehen in pipeline.py als HARD_RULES).

## Anti-Patterns

### Anker in Dekorator-Kette

Bei Patch-Ankern auf Klassen mit Dekorator
(@dataclass, @functools.*, @app.route) muss der
Dekorator in den Anker aufgenommen werden.

Falsch:

    "class Measurement:"

    -> Patch kann zwischen Dekorator und Klasse
       eingefuegt werden.

Richtig:

    "@dataclass(frozen=True)
     class Measurement:"

    -> Patch kann nicht mitten in die
       Dekorator-Kette greifen.

Anlass: Werkstatt-Auflage 2086, 2026-10-12.

### Patch-Anker ohne Semantik-Pruefung

Ein Anker kann syntaktisch eindeutig (count == 1)
und semantisch falsch sein.

Regel: Bei jedem Anker pruefen, ob er semantisch
zusammenhangende Einheiten trifft. Bei Klassen mit
Dekorator gehoert der Dekorator dazu. Bei
Funktionsbloecken gehoeren Docstring und Signatur
zusammen.

Anlass: Werkstatt-Auflage 2086, 2026-10-12.

## Patch-Konventionen

### Anker-Wahl

- Anker muessen syntaktisch eindeutig (count == 1)
  UND semantisch zusammenhaengend sein.
- Bei mehrzeiligen Ankern: die volle Struktur
  aufnehmen (Dekorator, Signatur, Docstring-Anfang).
- Kein Anker, der nur zufaellig eindeutig ist.

### Patch-Skripte

- Patch-Skripte immer in /tmp/ schreiben.
- Anker im Skript messen (`text.count(alt)`),
  nie im Chat aus grep/wc ableiten.
- Bei `count != 1`: Skript bricht ab, keine
  Schreiboperation.
- Nach jedem Patch: py_compile, ruff, mypy,
  pytest.

### Commit-Konventionen

- Ein Commit pro Auflage, ausser thematisch
  verwandte Auflagen (Gruppen).
- Kategorie 3 (Auth, RBAC, Secrets, Parser,
  Kern-Services): Reviewer-Block vor Commit.
- Commit-Autor: ghxstfocus <ghxst.focus@gmail.com>.

## Kategorien

- Kategorie 1: Doku/Config. Kein Reviewer-Block
  vor Commit.
- Kategorie 2: Code-Hygiene, Tests, Robustheit.
  Kein Reviewer-Block noetig, aber Tests Pflicht.
- Kategorie 3: Auth, RBAC, CSP, Secrets, SQL,
  Input-Validierung, Output-Escaping, DB-Schema,
  Audit, Kern-Services, Parser. Reviewer-Block
  vor Commit.

## Fail-closed-Prinzip

Wenn eine Pruefung nicht moeglich ist: blockieren,
nicht durchlassen. Beispiele:

- parse_commit_paket: ungueltiger Patch -> verworfen.
- require_budget: Budget erschoepft -> Stop.
- subprocess_env: Secrets werden nicht durchgereicht.
- redact_text: max_len zu klein -> ValueError.

## Block-Auftraege

Ein Block-Auftrag an die Werkstatt muss vier Angaben
enthalten:

1. Anker: exakter Text aus der Zieldatei, oder
   Messung, die den Anker liefert.
2. Zieltext: der neue Text, wortgetreu.
3. Bezug: welcher offene Punkt (Nummer), oder
   welche Fundstelle.
4. Kategorie: 1/2/3.

Ohne diese vier Angaben ist der Auftrag unterbestimmt.
Der Reviewer-Agent wird NO-GO oder ESKALATION geben.

### Wer formuliert was

- Der Mensch formuliert den Auftrag.
- Der Builder kann den Anker messen, aber den
  Zieltext nicht erfinden (HR1: Faktenlage vor
  Meinung).
- Konkret: der Mensch gibt Zieltext, Bezug,
  Kategorie. Der Builder kann den Anker liefern,
  wenn der Mensch nur "die Datei X" nennt und
  den Zieltext vorgibt.

### Beispiele

Beispiel (gut):

    Anker: letzte Zeile in docs/INCONSISTENCIES_FOUND.md
           lautet '<X>'.
    Zieltext: "## Neue Inkonsistenz\n<Text>"
    Bezug: offener Punkt 88.
    Kategorie: 1.

Beispiel (schlecht):

    "Ergaenze einen Absatz in der Datei."

    Fehlt: Anker, Zieltext, Bezug, Kategorie.
    Der Reviewer-Agent kann das nicht bewerten.

### Bugfix-Auftraege

Auch Bugfix-Auftraege fallen unter die Konvention:

- Zieltext = neuer Code-Zustand.
- Anker = problematischer Zustand.

Ausnahme: Auftraege der Kategorie 3 (Reviewer-Block
extern). Dort ist die Review-Pflicht ohnehin
vorgeschaltet.

## Anlass-Historie

- 2026-10-12, Auflage 2086: subprocess_env()
  versehentlich zwischen @dataclass und
  class Measurement eingefuegt. mypy-Fehler.
  Lehre: Dekorator in den Anker aufnehmen.
