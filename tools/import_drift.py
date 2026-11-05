#!/usr/bin/env python3
"""Import-Drift-Wrapper (OP-144).

Ruft `lint-imports` (aus import-linter) mit pyproject.toml-Config
auf. Prueft Layer-Regeln aus ADR-0013.

Exit 0 = keine Verletzungen. Exit 1 = Verletzungen.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    lint_imports = Path(sys.executable).parent / "lint-imports"
    if not lint_imports.exists():
        print(
            f"import-linter nicht installiert: {lint_imports} fehlt. "
            f"Installieren mit: python3 -m pip install 'import-linter>=2.0'",
            file=sys.stderr,
        )
        return 1
    result = subprocess.run(
        [str(lint_imports), "--config", str(ROOT / "pyproject.toml"),
         "--no-cache"],
        cwd=ROOT,
        check=False,
    )
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
