# ADR-0008: Chat als eigener Agent, nicht als Loop-Modus

- **Datum:** 2026-11-04
- **Status:** accepted
- **Kontext:** Der Nutzer will einen Assistenten pro Projekt, der
  Fragen beantwortet, Audit-Logs liest, Diffs prueft — wie
  ChatGPT/Claude Code, aber ohne Messbloecke an den Menschen zu
  schicken. Der Coding-Loop hat einen anderen Zweck (Produktion mit
  Gates) und eine andere Tool-Oberflaeche (Builder, Verify, Commit).
  Ein `--chat`-Modus des Coding-Loops wuerde zwei fundamentale
  Verantwortlichkeiten vermischen.

**Fragestellung:** Ist der Chat ein Modus des Coding-Loops oder ein
eigener Agent?

**Optionen:**

A) Modus im Coding-Loop (`--chat`). Ein Prozess, zwei Konfigurationen.
B) Eigener Agent mit eigener Tool-Registry, eigener System-Prompt,
   eigenem Loop.

## Entscheidung

**Option B — eigener Agent.**

- `werkstatt/chat_agent.py` mit eigenem `chat_loop()`.
- `werkstatt/chat_tools.py` — **read-only** Registry: `read_file`,
  `grep`, `git_log`, `git_diff`, `audit_query`, `pytest_collect`,
  `diagnose`, `read_status`. **Kein** `write_file`/`apply_patch`/
  `git_commit`.
- System-Prompt ist eigenstaendig (Diagnose, Erklaerung).
- Session-Store getrennt (`chat_session.py`) — der Chat hat eigene
  Historie.

**Begruendung:** Zwei Verantwortlichkeiten mit unterschiedlichen
Risiko-Profilen (Coding schreibt, Chat liest) sollten nicht im
selben Prozess mit demselben Mutex leben. Ein Fehler im Chat darf
den Coding-Loop nicht blockieren und umgekehrt. Der Chat ist
Diagnose-Instrument, der Coding-Loop ist Produktions-Instrument.

## Konsequenzen

Positiv:
- Saubere Trennung: Chat kann nie versehentlich committen.
- Chat kann unabhaengig erweitert werden (Debugger-Modus, Memory-
  Injektion), ohne den Coding-Loop anzufassen.
- Tests sind isoliert (Chat-Tests brauchen keinen Builder).

Negativ:
- Zwei Loops, zwei System-Prompts, zwei Tool-Sets — Wartung.
- Gemeinsame Infrastruktur (Event-Store, Projekt-Kontext) muss
  sauber geteilt werden (keine Duplikate).

Neutral:
- Chat ist nicht "der Coding-Loop mit anderem Prompt" — er hat
  eigene Grenzen.
