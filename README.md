# Schichtalarm – Testversion

Noch nicht aktiviert. Die Erkennung wurde nur mit künstlichen Beispielen getestet. Anmeldung, echte Angebote und iPhone-Zustellung müssen vor Aktivierung live geprüft werden.

## Einrichtung

1. In GitHub ein neues öffentliches Repository `schichtalarm` mit README anlegen. Nur den Inhalt dieses Ordners hochladen, einschließlich `.github/workflows/watch.yml`. Keine Zugangsdaten oder Sitzungsdateien hochladen.
2. In ntfy auf dem iPhone ein zufälliges Thema abonnieren: `shift-` plus 32 zufällige Hexzeichen, Server `https://ntfy.sh`. Mitteilungen erlauben. Thema geheim halten; öffentliche ntfy-Themen sind nicht durch ein Passwort geschützt. Es werden ausschließlich allgemeine Hinweise gesendet.
3. GitHub → Repository → Settings → Secrets and variables → Actions → New repository secret. Anlegen:
   - `NTFY_TOPIC`: das abonnierte Thema.
   - `FLASCHENPOST_LOGIN`: dein Portal-Benutzername.
   - `FLASCHENPOST_PASSWORD`: dein Portal-Passwort.
   - `STATE_KEY`: zufälliger Fernet-Schlüssel. Mit Python nach Installation der requirements erzeugbar: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`. Nur in Secrets speichern.
   Das bedeutet: GitHub erhält deine Flaschenpost-Zugangsdaten zur Ausführung. Erst einrichten, wenn du damit einverstanden bist. Zugangsdaten nicht in Chat, Quellcode, Issues oder README schreiben.
4. Actions → Schichtalarm → Run workflow → `notification-test`. Empfang auf dem iPhone kontrollieren.
5. Einmal manuell `retry-login` ausführen. Bei Fehlern zuerst prüfen, nicht wiederholt neu anmelden. Bei CAPTCHA/MFA funktioniert diese Testversion nicht automatisch.
6. Anschließend `check` ausführen: Wiederverwendung der Sitzung und Erkennung prüfen. Auch ein tatsächlich verfügbares Angebot muss vor Aktivierung geprüft werden.
7. Erst danach unter Actions → Variables die Repository-Variable `MONITOR_ENABLED` auf `true` setzen. Deaktivieren: Variable auf `false` setzen oder Workflow deaktivieren.

## Verhalten und Grenzen

- Prüft standardmäßig die beim Öffnen angezeigte Angebotsansicht; andere Monate/Filter werden noch nicht durchlaufen. Kein Anspruch auf vollständige Erfassung aller künftigen Schichten.
- Erkennt vorläufig Textänderungen mit mindestens zwei Uhrzeiten. Änderungen oder Entfernen einzelner Angebote können ebenfalls eine Meldung auslösen. Keine verifizierte Erkennung eindeutig neuer Schicht-IDs.
- Nimmt keine Schicht an. Eine Meldung verlinkt das Portal, wo du selbst entscheidest.
- Geplanter Abstand fünf Minuten; GitHub kann Starts verzögern oder auslassen. Keine Sofortbenachrichtigung oder Verfügbarkeitsgarantie. Öffentliche geplante Workflows können nach 60 Tagen ohne Repository-Aktivität deaktiviert werden.
- Workflow ist auf öffentliche Repositories und Standard-Linux-Runner beschränkt. Bei privaten Repositories wird der Job übersprungen. Kostenfreiheit hängt weiterhin von den geltenden Anbieterbedingungen ab.
- Sitzungen und Zustände werden nur verschlüsselt in Actions Cache gespeichert; Schlüssel liegt separat als Secret. Öffentlich lesbare Caches enthalten somit ausschließlich verschlüsselte Daten. Cacheverlust stoppt automatische Anmeldeversuche; manuelles `retry-login` ist nötig. Verschlüsselungsfehler erfordern Prüfung des Schlüssels und ggf. Löschen alter Caches.
- Vor einem Anmeldeversuch wird die Sitzung als gesperrt markiert. Erst bei erfolgreicher Anzeige wird die Sperre aufgehoben. Scheitert jedoch die Cache-Speicherung selbst, kann dieser Schutz nicht garantiert werden. Actions-Fehler deshalb beachten.
- Keine Rohdaten, Screenshots, Cookies oder Passwörter in Logs. Generische Fehlermeldungen werden höchstens täglich versucht. Fehler vor dem Einlesen des Zustands (fehlender Schlüssel/Cache) und ausgefallene GitHub-Jobs können keine Pushmeldung garantieren.
- Das Programm muss bei Portaländerungen angepasst werden. Es ist kein offizielles Flaschenpost-Angebot.

## Lokale Prüfung

Python 3.12, `pip install -r requirements.txt`, danach `python -m unittest discover -s tests`.
Fünf Tests prüfen Klassifizierung, doppelte Meldungen, Wiederholung nach Sendefehlern und Verschlüsselung. Kein automatischer Live-Login während der Tests.

Offizielle Dokumentation:
- https://docs.ntfy.sh/publish/
- https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows
- https://docs.github.com/en/actions/concepts/billing-and-usage
