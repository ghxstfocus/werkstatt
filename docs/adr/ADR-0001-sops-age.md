# ADR-0001: Key-Architektur mit SOPS + age

## Status

Accepted (2026-10-22, M-203).

## Kontext

Die Werkstatt las `DEEPSEEK_API_KEY` per `os.getenv` aus dem
Prozess-Environment. Nachteile:

- Key im Agenten-Prozess (`os.environ`).
- `subprocess_env()`-Allowlist schuetzte nur teilweise.
- Z.3269 (`run_measurement_mit_argv`) reichte `os.environ`
  an `pytest`-Subprozesse weiter. Latenter Leak (M-186).
- Kein Audit-Trail, kein Rollback bei Key-Wechsel.
- Key-Setzen erforderte manuellen Shell-Eingriff.

## Entscheidung

SOPS + age.

- `secrets.enc.yaml` (committet, verschluesselt) haelt den Key.
- `~/.config/sops/age/keys.txt` (0600, in `.gitignore`) haelt
  den age-Private-Key.
- Aufruf: `sops exec-env --pristine secrets.enc.yaml 'python pipeline.py'`.
- `--pristine` gibt nur die entschluesselten Variablen weiter,
  nicht die Parent-Umgebung.
- `subprocess_env()` bleibt Allowlist ohne API-Key.
- `pipeline.py` bleibt unveraendert (liest `os.getenv`).

## Konsequenzen

Positiv:
- Key nur im `pipeline.py`-Prozess sichtbar.
- Z.3269-Leak geschlossen, sobald Key via `sops exec-env` kommt.
- Git-native: Diff zeigt *dass* sich ein Secret geaendert hat,
  nicht *was*.
- Audit-Trail: `git log` auf `secrets.enc.yaml`.
- Rollback: `git revert` auf `secrets.enc.yaml`.

Negativ:
- Zusaetzliche Abhaengigkeit: `sops` + `age` installieren.
- Setup pro Maschine (age-Keypair).
- Aufruf ist laenger (`sops exec-env ... 'python pipeline.py'`
  statt `python pipeline.py`).

## Alternativen

- **`.env`-Datei mit python-dotenv:** Key im Klartext, in
  `.gitignore`. Kein Audit-Trail. Verworfen.
- **`~/.config/werkstatt/deepseek.key`:** Key als Datei, `0600`.
  Kein Audit-Trail. Verworfen.
- **OS-Keychain (libsecret, Keychain):** Plattformabhaengig.
  Fuer Server-Setup ungeeignet. Verworfen.
- **Placeholder-Proxy (nvenv, Veil):** Aufwand groesser,
  Nutzen fuer Solo-Setup gering. Spaeter pruefen (M-203
  Stufe 2).

## Referenzen

- `docs/KEY-ARCHITEKTUR.md` — Setup-Anleitung.
- `docs/MERKPOSTEN.md` — M-186, M-203.
- getsops/sops: https://github.com/getsops/sops
- FiloSottile/age: https://github.com/FiloSottile/age
