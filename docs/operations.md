# DhakaNest Operations

## Validation

```powershell
python scripts/verify_production_indexes.py
python scripts/production_release_check.py
python scripts/production_smoke_test.py --base-url https://api.example.com
python scripts/load_test_recommendations.py --base-url http://127.0.0.1:8000
```

Authenticated smoke checks require an explicit test token. Load testing defaults
to 50 `/health` requests at concurrency 5, rejects remote targets without an
override, and prohibits ranked submissions. Cached authenticated paths require
an explicit flag. Results are samples, not capacity guarantees.

## Database, Backup, and Recovery

Startup idempotently creates required user, listing, and history indexes.
`verify_production_indexes.py` only inspects metadata. Schema evolution uses
backward-compatible fields and startup-safe indexes; old history is not rewritten.

After installing MongoDB Database Tools:

```powershell
python scripts/backup_mongodb.py
mongorestore --uri="$env:MONGO_URI" --nsFrom="dhakanest_db.*" --nsTo="dhakanest_recovery_test.*" --archive="backups\BACKUP.archive.gz" --gzip
```

The backup wrapper never prints credentials. Restore only into a verified,
different isolated database; never use `--drop` against the active database.
Verify collection counts and indexes afterward. Store encrypted backups off-host.
Recommended baseline retention is 14 daily, 8 weekly, and 12 monthly copies.
No automated scheduler currently exists.

## Monitoring and Lifecycle

Use `/health` for liveness, `/ready` for readiness, and `/health/routing` for
safe aggregate routing state. Structured logs include timestamps, levels,
request IDs, and provider metadata without bodies or secrets. Startup validates
configuration, initializes routing, connects MongoDB, and creates indexes;
shutdown closes Motor. External aggregation remains platform work.

## Rollback

Redeploy previously verified frontend/backend image tags and matching environment
revision. Part 11 has no destructive schema migration, so application rollback
normally needs no database downgrade. Database restore is a separate incident
decision requiring a verified archive and isolated rehearsal. No zero-downtime
claim is made before a hosting platform and rollout strategy are selected.
