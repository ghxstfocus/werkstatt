"""Spec: IPv6-Redaction trennt Code-Kontext von Adressen (Fix 2026-10-31).

Regression: 'python::AuditError' wurde zu 'python[IPV6]uditError',
weil '::A' als IPv6 gesehen wurde. Der Fehler hat dazu gefuehrt,
dass der Builder einen old_string baute, der in der Zieldatei nicht
existiert.

Diese Specs testen Verhalten, nicht Implementation.
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/opt/werkstatt")

import pytest
import redaction


class TestCodeKontextNichtMaskiert:
    def test_python_doppelpunkt_klasse(self) -> None:
        inp = "core/reporting/audit_reader.py::AuditReaderError"
        out, _ = redaction.redact_all(inp)
        assert "[IPV6]" not in out
        assert "::AuditReaderError" in out

    def test_modul_doppelpunkt(self) -> None:
        out, _ = redaction.redact_all("python::os.path")
        assert "[IPV6]" not in out
        assert "::os.path" in out

    def test_sphinx_verweis(self) -> None:
        out, _ = redaction.redact_all("see foo.py::Bar for details")
        assert "[IPV6]" not in out
        assert "::Bar" in out


class TestEchteIPv6Maskiert:
    def test_public_vollform(self) -> None:
        inp = "Host 2001:4860:4860:0000:0000:0000:0000:8888"
        out, _ = redaction.redact_all(inp)
        assert "[IPV6]" in out

    def test_public_kurzform(self) -> None:
        out, _ = redaction.redact_all("Host 2001:db8::1")
        assert "[IPV6]" in out


class TestPrivateIPv6Bleibt:
    """Auflage 2195: private IPs bleiben sichtbar."""

    def test_loopback_alleine(self) -> None:
        out, _ = redaction.redact_all("::1")
        assert "::1" in out
        assert "[IPV6]" not in out

    def test_loopback_nach_space(self) -> None:
        out, _ = redaction.redact_all("Adresse: ::1")
        assert "::1" in out
        assert "[IPV6]" not in out

    def test_link_local(self) -> None:
        out, _ = redaction.redact_all("Link fe80::1")
        assert "fe80::1" in out
        assert "[IPV6]" not in out
