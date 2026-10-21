# Bau-Handoff — Werkstatt

Stand: 2026-10-21 (nach 3a-1c-3, HEAD 44eaedc).
Branch: umbau/phase-2 (origin ist 10 Commits hinterher, seit b502e20).
Baseline: 1245 passed / ruff 17 / mypy 9 (mypy 2.4.0) / AST+Katalog 14.

## Abgeschlossene Bloecke (seit b502e20)

- 3a-1c-2b (W2): endabgenommen (ca66927 + d512264).
- 3a-1c-3/C2 (Basis-Gate): abgenommen (d06cf23 + fafc5b5).
- 3a-1c-3/C0+C1 (Vorlauf+State): abgenommen (bb919d1 + da67198 + 44eaedc).
- 3a-1c-3/C6 (Coverage/Chaos): GESTRICHEN (Auftraggeber-Entscheid).
- VorlaufErgebnis-Dataclass in werkstatt/state.py (Z. 275-292).

## Naechster Block

3a-2 (run_phase, 528 Z.) ODER 3a-3 (_phase_main_pfad, 641 Z.).
Reviewer-Empfehlung: 3a-2 zuerst (kleiner, kein Deadlock-Risiko).
Auftraggeber-Entscheid offen.

Vorgehen wie 3a-1c-2b/3a-1c-3: messen, Signatur-Freeze,
Trockenlauf, Ausfuehrung, py_compile, pytest, Commit.
Reviewer-Block VOR dem ersten Code-Touch.

## Offene Merkposten (docs/OFFENE-BLOECKE.md)

- Struktur-Tests umstellen: 5/~15 erledigt (74ff77d).
  Rest folgt mit C0/C1/C2/C6/C8/C9 — C0+C1 erledigt (bb919d1).
- Werkstatt-Entkopplung von security-ai (werkstatt/verify.py).
- Commit-Body-Fehler 3a-1c-2a/2b (dokumentiert, behoben in
  Doku-Commits).
- W2-Grenze VOR/NACH (Doku-Klaerung 3b).
- A22-1-Erweiterung: 6-fach budget-Doppelquelle (3b).
- A10-1: Struktur-Test-Zeilen in 3a-1c-1b veraltet (3b).

## Neue Merkposten (aus dieser Session, noch nicht in
OFFENE-BLOECKE.md)

- Quality-Gate-Skript (Deterministic Orchestration):
  Shell Bypass fuer pytest/ruff/mypy, JSON-Output,
  Hook nach apply_code_patches. Best aus allen Welten:
  Claude Code Hooks, Codex Auto-Review, Devin Relay-
  Pattern, Shell Bypass Principle. Aufwand ~1 Tag.
  Zeitpunkt: 3b (Loop-Umbau).
- Reviewer-Modus straffen: Block + Baseline + Signatur
  + Return-Bilanz als Pflicht, Detail-Runden nur bei
  konkretem Widerspruch mit Zitat. (Reviewer-Vorschlag
  Durchlauf 54.)

## Tool-Umgebung

- ruff 0.17.1, mypy 2.4.0 via pipx (/root/.local/bin).
  PATH exportieren: export PATH="/root/.local/bin:$PATH".
- Heredoc-Transfer zerstoert regelmaessig Zeilen
  (Artefakte C2, C7, _vorlauf_und_state., run_pipeline.
  in dieser Session). Ab jetzt: Skripte als
  python3 -c "...eizeilig" oder cat > datei <<'EOF'
  mit einer Marker-Zeile.

## Letzte 10 Commits

44eaedc docs(3a-1c-3): A22-2-Nach-Liste — 4 Return-Listen (46)
bb919d1 refactor(3a-1c-3): C0+C1 Vorlauf+State _vorlauf_und_state extrahiert
da67198 feat(state): VorlaufErgebnis-Dataclass (10 Felder)
d8f16cf docs(3a-1c-3): M-55 + A22-1/2/3 — Struktur-Test-Rest + budget + Return-Bilanz
1ee420d docs(3a-1c-3): M-53 + M-54 — Marker-Zeilen + budget-Herkunft
5e7a37e docs(3a-1c-3): M-48..M-52 — C0+C1-Belege (HEAD fafc5b5)
fafc5b5 test(3a-1c-3): A17-1 Docstring-Update Basis-Gate-Test
d06cf23 refactor(3a-1c-3): C2 Basis-Gate _basis_gate extrahiert
8ac1092 docs(3a-1c-3): M-46 + M-47 — Return-Bilanz korrigiert (ehrlich)
ca66927 docs(3a-1c-2b): Entscheidung (b) — W2-Grenze VOR/NACH
