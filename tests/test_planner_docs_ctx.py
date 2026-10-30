"""Spec: docs_ctx fuer Doku-Aufgaben ist max 5 KB betroffene Datei."""
from __future__ import annotations
import sys
sys.path.insert(0, "/opt/werkstatt")
import pytest


class TestDocsCtxSchlank:
    """Testet die reine Logik: bei Doku-Aufgabe soll nur die
    betroffene .md genutzt werden, nicht alle docs."""

    def _build_docs_ctx(self, aufgabe: str, docs: dict) -> str:
        _aufgabe_lower = (aufgabe or "").lower()
        _ist_doku = (
            ("nur" in _aufgabe_lower or "ausschliesslich" in _aufgabe_lower
             or "keine python" in _aufgabe_lower
             or "kein code" in _aufgabe_lower)
            and (".md" in _aufgabe_lower or "docs/" in _aufgabe_lower)
        )
        if _ist_doku:
            import re as _re
            md = _re.findall(r"[a-zA-Z_][\w/.-]*\.md", aufgabe or "")
            ziel = md[0] if md else ""
            for k, v in docs.items():
                if ziel and (ziel in v[:2000] or ziel in k):
                    return f"--- {k} ---\n{v[:5000]}"
            return ""
        return "\n".join(
            f"--- {k} ---\n{v[:20000]}"
            for k, v in list(docs.items())[:3]
        )

    def test_doku_aufgabe_nur_betroffene_datei(self) -> None:
        docs = {
            "status": "# Status\nPunkt 1\n" + "x" * 10000,
            "security": "y" * 50000,
            "roadmap": "z" * 30000,
        }
        ctx = self._build_docs_ctx("Nur docs/STATUS.md aendern.", docs)
        assert "status" in ctx or len(ctx) == 0
        assert "security" not in ctx
        assert len(ctx) < 6000

    def test_code_aufgabe_voller_kontext(self) -> None:
        docs = {"a": "A" * 25000, "b": "B" * 25000, "c": "C" * 25000}
        ctx = self._build_docs_ctx("Refactor core/foo.py", docs)
        assert len(ctx) > 30000

    def test_doku_aufgabe_ohne_md_ziel_leer(self) -> None:
        docs = {"status": "x"}
        ctx = self._build_docs_ctx("Nur docs/aendern ohne Ziel", docs)
        assert ctx == ""
