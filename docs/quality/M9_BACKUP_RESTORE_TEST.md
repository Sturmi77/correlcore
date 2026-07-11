# M9 Backup & Restore Test Protocol

Last updated: 2026-07-11  
Sprint: M9-S3 (Backup & install)  
Operator guide: [`docs/selfhost/INSTALL.md`](../selfhost/INSTALL.md)

## Objective

Verify that the documented backup toolchain (`pg_dump` → optional `restic`) can restore
PostgreSQL data integrity. This satisfies the M9 acceptance criterion:

> Backup-Prozess dokumentiert und Restore-Test erfolgreich durchgeführt

## Scope

| In scope                                     | Out of scope                                              |
| -------------------------------------------- | --------------------------------------------------------- |
| Logical `pg_dump` / `psql` restore cycle     | Full production stack DR drill                            |
| restic `init` + `backup` + `snapshots` smoke | MinIO volume restore                                      |
| Probe table round-trip                       | GlitchTip DB restore                                      |
| Fernet field decryption                      | Requires live app + `ENCRYPTION_KEY` (operator checklist) |

## Environment

| Field          | Value                           |
| -------------- | ------------------------------- |
| Date           | 2026-07-11                      |
| Host           | Cursor Cloud agent VM           |
| Postgres image | `pgvector/pgvector:pg16`        |
| Container      | `m9-restore-test-pg`            |
| restic image   | `restic/restic:latest`          |
| Operator       | Automated Sprint 3 verification |

## Procedure

### Step 1 — Start isolated Postgres

```bash
docker run -d --name m9-restore-test-pg \
  -e POSTGRES_USER=correlcore \
  -e POSTGRES_PASSWORD=correlcore \
  -e POSTGRES_DB=correlcore \
  -p 5433:5432 \
  pgvector/pgvector:pg16
```

Wait until `pg_isready -U correlcore -d correlcore` succeeds.

### Step 2 — Insert probe data

```sql
CREATE TABLE m9_restore_probe (id serial primary key, label text);
INSERT INTO m9_restore_probe (label) VALUES ('sprint3-restore-ok');
```

### Step 3 — Backup (`pg_dump`)

```bash
docker exec m9-restore-test-pg pg_dump -U correlcore correlcore \
  | gzip > /tmp/m9-backup-test.sql.gz
```

**Result:** archive size **815 B** (gzip).

### Step 4 — Simulate disaster (drop database)

```bash
docker exec m9-restore-test-pg psql -U correlcore -d postgres \
  -c "DROP DATABASE correlcore;" \
  -c "CREATE DATABASE correlcore OWNER correlcore;"
```

### Step 5 — Restore

```bash
gunzip -c /tmp/m9-backup-test.sql.gz \
  | docker exec -i m9-restore-test-pg psql -U correlcore -d correlcore -v ON_ERROR_STOP=1
```

### Step 6 — Verify row count

```sql
SELECT count(*) FROM m9_restore_probe WHERE label = 'sprint3-restore-ok';
```

**Expected:** `1`  
**Actual:** `1` ✅

### Step 7 — restic smoke test

```bash
export RESTIC_PASSWORD='<test-password>'
restic init -r /tmp/m9-restic-repo
restic -r /tmp/m9-restic-repo backup /tmp/m9-backup-test.sql.gz --tag m9-sprint3
restic -r /tmp/m9-restic-repo snapshots
```

**Result:** 1 snapshot `0db81741`, tag `m9-sprint3`, path `/tmp/m9-backup-test.sql.gz` ✅

## Outcome

| Check                                | Status |
| ------------------------------------ | ------ |
| `pg_dump` produces valid archive     | Pass   |
| Empty DB restore via `psql`          | Pass   |
| Probe row survives round-trip        | Pass   |
| restic encrypted repo accepts backup | Pass   |
| restic snapshot listable             | Pass   |

**Overall: PASS** — backup→restore cycle documented and executed successfully.

## Production operator follow-up

Before beta onboarding, each production instance operator should:

1. Run a **full** `pg_dump -Fc` against `correlcore-postgres` (see INSTALL.md).
2. Store dump via restic to an off-site repository.
3. Perform one **manual** restore to a staging container and confirm:
   - `GET /api/v1/health` OK after `docker compose up`
   - Test user login
   - Encrypted notes decrypt (confirms `ENCRYPTION_KEY` matches backup era)
4. Record date and operator name in this file (append row below).

## Production restore log (operator-maintained)

| Date       | Instance                 | Operator    | pg_restore | Notes decrypt        | restic restore |
| ---------- | ------------------------ | ----------- | ---------- | -------------------- | -------------- |
| 2026-07-11 | m9-restore-test-pg (lab) | M9-S3 agent | N/A (psql) | N/A (no Fernet data) | smoke only     |

## Cleanup (lab)

```bash
docker rm -f m9-restore-test-pg
rm -f /tmp/m9-backup-test.sql.gz
rm -rf /tmp/m9-restic-repo
```
