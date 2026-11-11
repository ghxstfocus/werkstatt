# ADR-0030: Projektquellen und projektbezogene Rollenmodelle

- **Datum:** 2026-11-11
- **Status:** accepted
- **Ergaenzt:** ADR-0023 (Multi-Projekt-Kontext), ADR-0029 (Chat-zentrierte Projektsteuerung)
- **Grundlage fuer:** OP-399

## Kontext

Der Werkstatt-Server ist der primaere Arbeitsort: Neue Projekte werden dort
angelegt und gescaffoldet. GitHub kann beim Greenfield-Setup direkt verbunden
oder spaeter als Remote ergaenzt werden. Bestehende GitHub-Repositories koennen
zusaetzlich ohne vorherigen manuellen Clone erkundet und als Projekt
registriert werden. Chat, Loop, Runs und Doku zeigen fuer alle Quellen
denselben Projektkontext. Die Projektleiste soll bestehende Projekte oeffnen
und neue lokale oder GitHub-verbundene Projekte anlegen lassen.

Zusaetzlich brauchen Projekte eigene Rollenmodelle. Die heutige globale
Rollen-Routing-Konfiguration soll als funktionierender Default erhalten
bleiben; ein Projekt kann einzelne Rollen wie Architect, Builder, Reviewer,
Chat oder Debugger gezielt ueberschreiben. Zugangsdaten duerfen dabei nicht
in Repo-Dateien oder Git landen.

## Entscheidung

1. **Serverprojekt mit optionalem Remote:** Ein registriertes Projekt hat eine
   stabile interne Projekt-ID und einen Server-Arbeitsbereich. GitHub-Remote,
   Default-Branch und aufgeloester Commit werden separat vom lokalen
   Arbeitsstand und vom Laufzeit-Zustand gespeichert. Neue Projekte koennen
   serverseitig ohne GitHub erstellt werden; ein Remote kann beim Anlegen oder
   spaeter hinzugefuegt werden. Ein GitHub-Repository kann auch direkt
   registriert und serverseitig ausgecheckt werden.
2. **GitHub-Inspektion ohne Server-Checkout:** Chat und Explorer koennen ein
   autorisiertes Repository ueber einen GitHub-Provider lesen. Ein URL-Paste
   darf nur nach Validierung auf einen unterstuetzten GitHub-Host zum Adapter
   fuehren; frei formulierter URL-Fetch ist ausgeschlossen.
3. **Serverseitige Git-Synchronisierung:** Bei verbundenem Remote ruft der
   Werkstatt-Server vor jedem Run den konfigurierten Branch/Ref selbst ab und
   pinnt dessen Commit-SHA. Ist der Server-Branch clean und nur hinter dem
   Remote, darf er kontrolliert per Fast-Forward aktualisiert werden. Lokale
   Commits, uncommittete Aenderungen oder divergierende Branches werden nie
   ueberschrieben oder still verworfen: der Chat zeigt den Zustand und fordert
   eine gezielte Sync-/Konfliktentscheidung, wenn kein sicherer Fast-Forward
   moeglich ist. Der Loop arbeitet anschliessend in einem verwalteten,
   isolierten Worktree auf der bestaetigten Revision; der manuelle Clone/Pull
   entfällt. Neue serverseitige Projekte koennen auf Wunsch mit GitHub
   verbunden und initial veroeffentlicht werden. Initiales Pushen sowie spaetere
   Pushes/Merges benoetigen jeweils eine eigene Freigabe und sind keine
   implizite Folge eines Plan-Gates. Fetch und Push verwenden ausschliesslich
   serverseitig konfigurierte Git-Zugangsdaten; Tokens/Schluessel werden weder
   in Projektdateien gespeichert noch in Logs oder Browserantworten
   ausgegeben. Projekte ohne Remote arbeiten weiter direkt lokal.
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

## Umsetzungsentscheidungen fuer OP-399

- **Authentifizierung:** Remote-Zugriff verwendet nur serverseitig konfigurierte Git-/GitHub-Credentials mit Least-Privilege. Das konkrete Credential-Backend und seine Rechte werden vor dem ersten Remote-Schreibzugriff dokumentiert; Browser und Projektdateien erhalten keine Tokens.
- **Greenfield-Lifecycle:** Scaffolding und Erstpruefung erfolgen auf dem Werkstatt-Server. GitHub-Repository anlegen/verbinden und initial pushen sind getrennte, explizit freizugebende Aktionen. Falls die konfigurierte Integration kein Repository anlegen darf, zeigt die UI die sichere Verknuepfung eines bereits angelegten Repositories, ohne lokale Arbeit zu verlieren.
- **Remote-Ausfuehrung:** Chat darf autorisierte Repository-Metadaten lesend untersuchen. Tests und andere Projektbefehle laufen ausschliesslich in verwalteten, isolierten Checkouts auf gepinnten Commit-SHAs.
- **Synchronisierung:** Nur ein sauberer Branch, der ausschliesslich hinter dem Remote liegt, darf automatisch per Fast-Forward aktualisiert werden. Dirty, lokale ahead oder divergierende Branches stoppen die Aktualisierung und erfordern eine erklaerte, gezielte Entscheidung.
- **Secrets:** Bestehende serverseitige Credential-Verwaltung wird wiederverwendet, sofern sie den Least-Privilege-Vertrag erfuellt. Andernfalls muss vor Remote-Schreibzugriffen ein geeignetes Secret-Backend mit Rotation und Rechtebegrenzung eingerichtet werden.
- **Modelle:** Projektbezogene Rollen-Overrides und Modellkatalog folgen OP-400; bis dahin gelten globale Defaults.
- **Migration:** Scaffolder erzeugt einen konkreten Vorschau-Diff; keine bestehenden Dateien werden ohne ausdrueckliche Freigabe ueberschrieben.

## Anforderungen fuer die Umsetzung

Die Umsetzung muss Quellen-Isolation, stabile Repository-Revisionen,
Projekt-Tab-Reconnect, nicht-destruktive Migration, Branch-/PR-Write-Policy,
Secret-Redaktion, Modell-Override mit globalem Fallback sowie
Fehler-/Offline-Verhalten testen. Die Architekturentscheidung ist angenommen. OP-399 muss die konkreten serverseitigen Credentials, Berechtigungen und Betriebsgrenzen vor Remote-Schreibzugriffen dokumentieren und die oben genannten Sicherheitsinvarianten durch Tests belegen.
