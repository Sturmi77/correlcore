# A01: Marker-Upgrade aus Revision 046–048

Migration 049 konvertiert Marker und entfernt danach `entry_note_markers` in
derselben PostgreSQL-Transaktion. Sie verwendet Alembics bestehende Verbindung
und nur Spalten des Schemas von 049. Sie liest `entries.note_enc` nicht; der
verschlüsselte Notiztext bleibt unverändert. Der Sync-Revision-Log enthält wie
bei regulären Entry-Revisionen `note: null` und die neuen Tag-IDs.

## Vor dem Upgrade

1. Schreibzugriffe der App und Worker anhalten. Migrationen mit dem dafür
   vorgesehenen Owner beziehungsweise einer Rolle mit `BYPASSRLS` ausführen.
   Die eingeschränkte App-Rolle ist nicht als Migrationsrolle geeignet.
2. Eine vollständige PostgreSQL-Sicherung erstellen und **in eine separate
   Datenbank zurückspielen**. `pg_dump -Fc` und `pg_restore` sind dafür ein
   mögliches Verfahren; Datenbankname, Rolle und Secrets gehören in die
   Betriebsumgebung, nicht in dieses Repository.
3. Auf der Wiederherstellung `alembic current`, Nutzer-, Marker- und Tag-Zahlen
   festhalten. Den Weg `046→head`, `047→head` oder `048→head` passend zum
   Ausgangsstand proben. Die Runtime-Rolle anschließend mit einem Lese- und
   Schreibtest für einen eigenen Nutzer prüfen.

## Fehler und Wiederanlauf

Ein Fehler vor Ende von 049 rollt Link-, Tag- und Revision-Log-Schreibvorgänge
sowie den `DROP` zurück. Die Markertabelle bleibt erhalten. Ursache beheben und
`alembic upgrade head` erneut ausführen. Ein schon abgeschlossenes 049 wird
nicht erneut ausgeführt. Falls ein älterer Release-Build 049 bereits erfolgreich
angewendet hat, sind seine Marker entfernt; fehlende Daten können nur aus einer
vorherigen Sicherung rekonstruiert werden. Deshalb den Restore **vor** dem
Produktionsupgrade testen.

Ein Downgrade erzeugt nur eine leere Markertabelle und ist **kein** Restore.
Produktions-Rollback erfolgt über die zuvor geprüfte Datenbanksicherung und das
zugehörige App-Image. Den konkreten Backup-/Restore-Nachweis und die finalen
Image-SHAs im Release-Protokoll ergänzen, bevor #977 geschlossen wird.

## Automatische Nachweise

`tests/test_a01_release_upgrade_integration.py` erstellt unter PostgreSQL 16
jeweils eine separate alte Datenbank für 046, 047 und 048, seeded mehrere Nutzer
und Marker und erzwingt ein Backfill-Fehler mitten im Upgrade. Jeder
Alembic-Aufruf hat einen festen Timeout. Der CI-Integrationsjob führt diese
Tests mit `CORRELCORE_RUN_INTEGRATION=1` aus. Die allgemeinen Migration-Smokes
prüfen zusätzlich die frische Installation und eine `pg_dump`/`pg_restore`-Probe
der migrierten CI-Datenbank. Der produktive Backup-/Restore-Nachweis bleibt ein
eigener Release-Gate auf den finalen Images und Betriebsdaten.
