---
name: security-review
description: |
  Sicherheits-Review gegen OWASP Top 10:2025, CWE Top 25.
  Mit Vier-Fragen-Triage (angreiferkontrolliert,
  erreichbar, Blast Radius, Exploit-Schritte) und
  Severity-Definitionen. Use when code touches auth,
  input, crypto, network, or file handling.
---

# Security-Review

## Vor jedem Finding: die 4-Fragen-Triage

Ein Pattern-Match ist keine Vulnerability. Pruefe alle vier:

1. Ist der Input angreiferkontrolliert?
   Trace back zu einem echten Entry Point:
   Request-Parameter, Header, Cookie, Upload,
   Webhook, Queue, Third-Party-API.
   Nur Konstanten, Enums, interne Config: KEIN Finding.

2. Ist der Sink erreichbar?
   Gibt es Validierung, Allowlist, ORM,
   Framework-Kontrolle dazwischen?
   Auth-Middleware vorhanden?

3. Was ist der Blast Radius?
   Wer kann es triggern, was bekommt er,
   welche Trust Boundary wird ueberschritten?

4. Kann der Angreifer jeden Schritt?
   Jeder Exploit-Schritt muss moeglich sein.
   Sonst: Needs verification, nicht High.

## OWASP Top 10:2025

A01 Broken Access Control (inkl. SSRF)
A02 Security Misconfiguration
A03 Software Supply Chain Failures
A04 Cryptographic Failures
A05 Injection
A06 Insecure Design
A07 Authentication Failures
A08 Software or Data Integrity Failures
A09 Logging & Alerting Failures
A10 Mishandling of Exceptional Conditions

## CWE Top 25 (haeufigste)

- CWE-79 XSS
- CWE-89 SQL Injection
- CWE-352 CSRF
- CWE-862 Missing Authorization
- CWE-787 Out-of-bounds Write
- CWE-22 Path Traversal
- CWE-78 OS Command Injection
- CWE-94 Code Injection
- CWE-502 Deserialization of Untrusted Data
- CWE-20 Improper Input Validation
- CWE-306 Missing Auth for Critical Function
- CWE-918 SSRF

## Severity

Critical: Unauthenticated RCE, Auth-Bypass, Mass-Data-Exposure
High:     Authentifizierte Exploitation ueber Trust Boundary
Medium:   Ungewoehnliche Preconditions, Impact nur eigene Daten
Low:      Defense-in-Depth ohne Exploit-Pfad
Info:     Hardening; explizit 'keine Vulnerability'

## Reporting-Format

[SEVERITY] Title (CWE-###, OWASP A##:2025)
Location:    path/to/file.ext:LINE
Entry Point -> Hops -> Sink
Impact:      who, what, which trust boundary
Remediation: concrete change, code snippet
Confidence:  Confirmed | Likely | Needs verification

## Was NICHT melden

- Unerreichbare Code-Pfade.
- Bereits mitigierte Stellen (Auth-Middleware zentral).
- Defense-in-Depth ohne Exploit-Pfad als 'Critical'.
- Info-Items als Padding.
