# ADR-0030: Projektquellen und projektbezogene Rollenmodelle

- **Datum:** 2026-11-11
- **Status:** proposed
- **Ergaenzt:** ADR-0023 (Multi-Projekt-Kontext), ADR-0029 (Chat-zentrierte Projektsteuerung)
- **Grundlage fuer:** OP-399

## Kontext

Die Werkstatt soll Projekte aus zwei Quellen unter einer Projektoberflaeche
bearbeiten koennen: ein GitHub-Repository, das ohne vorherigen Server-Checkout
erkundet werden kann, und ein lokales Projektverzeichnis auf dem Werkstatt-
Server. Der Projekt-Tab muss unabhaengig von der Quelle denselben Kontext fuer
Chat, Loop, Runs und Doku anzeigen. Die Projektleiste soll bestehende Projekte
oeffnen und neue Projekte anlegen lassen.

Zusaetzlich brauchen Projekte eigene Rollenmodelle. Die heutige globale
Rollen-Routing-Konfiguration soll als funktionierender Default erhalten
bleiben; ein Projekt kann einzelne Rollen wie Architect, Builder, Reviewer,
Chat oder Debugger gezielt ueberschreiben. Zugangsdaten duerfen dabei nicht
in Repo-Dateien oder Git landen.

## Vorgeschlagene Richtung (noch nicht angenommen)

1. **Projektquellen als Adapter:** Ein registriertes Projekt hat eine stabile
   interne Projekt-ID und eine Quelle "local" oder "github". Quelle, Remote-
   URL, Default-Branch und der aufgeloeste Commit werden getrennt von
   laufzeitbezogenem Loop-Zustand gespeichert.
2. **GitHub-Inspektion ohne Server-Checkout:** Chat und Explorer koennen ein
   autorisiertes Repository ueber einen GitHub-Provider lesen. Ein URL-Paste
   darf nur nach Validierung auf einen unterstuetzten GitHub-Host zum Adapter
   fuehren; frei formulierter URL-Fetch ist ausgeschlossen.
3. **Schreibarbeit in isoliertem Checkout:** Wenn ein Remote-Projekt durch den
   Coding-Loop bearbeitet wird, erfolgt die Arbeit in einem isolierten lokalen
   Checkout/Worktree auf einem benannten Branch. Vorschau und Aenderungen
   laufen durch Plan-Gate, Patch-Freigabe, Verify, Review und Human-Gate.
   Merge oder Push auf den Default-Branch ist keine implizite Folge einer
   Freigabe.
4. **Werkstatt-Onboarding:** Der Scaffolder erkennt vorhandene Konventionen
   und erzeugt vor einer Migration einen konkreten, nicht-destruktiven Plan
   samt Diff. Er ueberschreibt weder Projektdateien noch Dokumente still.
   Erst nach ausdruecklicher Freigabe wird die Migration angewendet.
5. **Projektleiste:** Plus bietet "Lokales Projekt anlegen", "GitHub-Projekt
   hinzufuegen" und "Vorhandenes Projekt oeffnen". Registrierung und Oeffnen
   sind getrennte Aktionen; ein vorhandenes Verzeichnis/Remote wird nicht
   automatisch migriert.
6. **Rollenmodell-Einstellungen:** Eine Projekt-Einstellungsseite zeigt alle
   Rollen und ihre effektive Provider-/Modellwahl. Nicht ueberschriebene
   Rollen erben die globale Rollen-Registry. Vorhandene Defaults bleiben
   erhalten; Debugger darf zum Beispiel projektspezifisch ein leistungsfaehiges
   guenstiges Modell erhalten, ohne den Architect umzurouten.
7. **Secrets und Modellkatalog:** Projektkonfiguration speichert nur
   Provider- und Secret-Referenzen. API-Schluessel bleiben in einer
   serverseitigen Secret-Verwaltung oder einem explizit konfigurierten
   Secret-Backend. Modell-IDs, Anbieter, Thinking-Optionen und benoetigte
   Faehigkeiten werden gegen einen zentralen Katalog validiert. Secrets werden
   nie zurueck an den Browser ausgegeben.

## Zu klaerende Architekturfragen

- GitHub-Authentifizierung: GitHub App Installation, OAuth oder vorhandenes
  Server-Credential; erforderlicher Least-Privilege-Scope fuer private Repos.
- Remote-Lesezugriff: GitHub API Provider oder isolierter Mirror-Checkout fuer
  grosse Repos und AST-/Testwerkzeuge.
- Secret-Backend: vorhandene Server-Umgebungsvariablen, OS-Keyring oder
  dedizierter Secret-Store und dessen Backup-/Rotation-Verhalten.
- Modell-Katalog: statische Registry oder Provider-Metadaten mit Cache,
  Ausfallverhalten und Capability-Validierung.
- Erlaubte Projektquellen, Branch-Policy und Sicherheitsgrenzen beim Start von
  Tests oder anderen Projektprozessen.

## Anforderungen fuer die Umsetzung

Die Umsetzung muss Quellen-Isolation, stabile Repository-Revisionen,
Projekt-Tab-Reconnect, nicht-destruktive Migration, Branch-/PR-Write-Policy,
Secret-Redaktion, Modell-Override mit globalem Fallback sowie
Fehler-/Offline-Verhalten testen. Diese ADR bleibt "proposed", bis
Authentifizierung, Checkout-Modell und Secret-Backend entschieden sind.
