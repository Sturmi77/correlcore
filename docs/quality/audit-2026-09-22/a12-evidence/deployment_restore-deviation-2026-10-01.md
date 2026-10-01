# deployment_restore — Abweichung und Restore-Probe — 2026-10-01 (UTC)

Dies ist **keine** Abnahme des Gates. Es dokumentiert eine vom Owner akzeptierte Abweichung und die bisher
erbrachte Restore-Probe. Das Gate `deployment_restore` bleibt offen, bis Staging-Smoke und Produktions-Smoke
auf dem Kandidaten vorliegen (siehe „Noch offen“).

- Release-Kandidat: `v1.9.2`, Git SHA `a48b84cae4bd7ba39c174f098fabee577cd9a934`
- API image: `sha256:f0ccdd295e962378288c6426c326ad089bdc97d509018fbdfcc8e5557c71eb9e`
- Web image: `sha256:ca1bd66dca0f1bca7cd5725a3ea972ba0472855c184eefe44782c35ee7e64cb3`
- Worker image: wie API (der Worker läuft aus dem API-Image)
- Environment: Produktions-Docker-Host des Owners (NAS), PostgreSQL im Container `correlcore-postgres`
- Executor role: Owner / Operations
- Result: Restore-Probe bestanden; Upgrade-Fixture-Nachweis **abweichend** (siehe unten)

## Abweichung vom geforderten Nachweis

Gefordert ist ein „v1.9.1-Fixture-Upgrade mit finalen Image-Digests“ (Runbook §8, Schritt 2–3).

- Die Produktionsdatenbank stand beim Backup bereits auf **Alembic-Revision 055** (Head von 1.9.2). Die
  Revisionen 047–055 waren dort also schon angewendet, darunter 049 (Marker→Tag-Backfill, danach `DROP` von
  `entry_note_markers`).
- Ein Backup **vor** dieser Migration existiert nicht. Eine echte v1.9.1-Fixture aus Produktivdaten gibt es deshalb
  nicht, und der Upgrade-Pfad 046→055 wurde auf Produktivdaten nicht geprobt.
- **Entscheidung des Owners (01.10.2026):** Die Abweichung wird akzeptiert und dokumentiert; ein Ersatz-Upgrade
  auf Staging wird nicht verlangt.

**Ersatznachweis für den Upgrade-Pfad:** `backend/tests/test_a01_release_upgrade_integration.py` erstellt in der CI
unter PostgreSQL 16 jeweils eine separate Datenbank für die Ausgangsrevisionen 046, 047 und 048, befüllt sie mit
mehreren Nutzern und Markern, führt das Upgrade bis `head` aus und erzwingt einen Backfill-Fehler mitten im Upgrade
(Rollback-Verhalten). Der Integrationsjob läuft grün auf dem Kandidaten
(siehe [A10-Lauf](https://github.com/Sturmi77/correlcore/actions/runs/36855944618), Job „Migrations, backfills, real
PostgreSQL integration“; der Lauf gehört zu `rc.2`, dessen Quelltext dem Kandidaten entspricht).

Einschränkung: Das sind synthetische Daten. Sie belegen nicht, dass die konkrete Produktionsmigration verlustfrei
war. Der Nachweis dafür fehlt, weil kein Stand davor gesichert wurde.

## Restore-Probe (Runbook §8, Schritt 5, teilweise)

Prozedur (ohne Daten und Geheimnisse):

1. `pg_dump -Fc` der Produktionsdatenbank mit der Owner-Rolle in eine Datei im Container.
2. Kopie auf das NAS-Volume; **SHA-256 identisch** in Container und Ziel
   (`63ba379dfe0b3c3edba2e21c36f1f4966f2247bf42568347e8df66e6bd2b44c4`).
3. Neue, leere Datenbank im selben PostgreSQL-Container angelegt.
4. `pg_restore --exit-on-error` in diese Datenbank: **ohne Fehler**.
5. Vergleich Produktion gegen Wiederherstellung (`alembic_version`, Nutzer, Einträge).

| Prüfwert         | Produktion | Wiederherstellung |
| ---------------- | ---------- | ----------------- |
| Alembic-Revision | 055        | 055               |
| Nutzer           | 2          | 2                 |
| Einträge         | 150        | 150               |

6. Probe-Datenbank gelöscht. Die Produktionsdatenbank wurde weder überschrieben noch verändert. Eine Rückspielung
   in die Originaldatenbank war nicht Teil der Probe und ist nur im echten Notfall nötig.

## Noch offen für dieses Gate

- Mindestens ein **entschlüsselbarer Datensatz** in der Wiederherstellung (setzt den `ENCRYPTION_KEY` auf der
  Zielinstanz voraus, dessen separate Sicherung der Owner bestätigen muss).
- **Staging-Smoke** mit den Kandidaten-Digests (Health/Readiness, Login, Eintrag, Sync, Insights/Worker, Reportexport,
  Account-Export).
- **Nachweis, welche Digests in Produktion laufen**, und anschließender **Produktions-Smoke** ohne Testdatenmutation.
- Rollback-Entscheidung und Verantwortliche (Runbook §8, Schritt 6): Rollback erfolgt über Datenbank-Backup plus
  Image, nicht über einen Alembic-Downgrade (ein Downgrade legt nur eine leere Markertabelle an).

## Findings and follow-up

- Produktion folgt vermutlich einem beweglichen Tag (`:latest`/`:main`); noch zu bestätigen. Das hat die Migration
  vor der Probe ausgelöst und ist der Anlass der Abweichung. Siehe Z0.2 ([#1019](https://github.com/Sturmi77/correlcore/issues/1019)).

## Sign-off

- Role: Owner / Operations (zu bestätigen)
- Date: (zu ergänzen bei Abschluss des Gates)
- Result: offen
