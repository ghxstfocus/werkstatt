---
name: web-security
description: |
  Web-Sicherheits-Pruefung. XSS, CSRF, SQL-Injection,
  Auth, Session, Secrets. Use when code touches
  authentication, user input, or HTTP responses.
---

# Web-Security

## Checkliste
- User-Input escaped (HTML, SQL, Shell)?
- CSRF-Token bei POST/PUT/DELETE?
- Auth vor jeder geschuetzten Route?
- Session-Cookie: httpOnly, secure, sameSite?
- Secrets nicht im Code, nicht im Log?
- SQL parametrisiert?
- Command-Injection verhindert (kein shell=True)?
- Error-Messages ohne Stacktrace an User?

## Bei Fund
Reviewer: NO-GO mit konkretem Angriffs-Szenario.
