# PetCare 360 - Operations, Deployment & Disaster Recovery

## 1. Health Checks & Monitoring
- **Endpoint**: `GET /healthz`
- **Behavior**: Executes `SELECT 1` against the primary database.
- **Responses**:
  - `200 OK`: `{"status": "healthy", "database": "connected", "timestamp": "..."}`
  - `503 Service Unavailable`: `{"status": "unhealthy", "database": "error", "error": "...", "timestamp": "..."}`
- Configured in `Dockerfile` via standard Docker `HEALTHCHECK`.

## 2. Docker Deployment
### Local Multi-Container Stack (App, PostgreSQL, Background Worker)
```bash
docker-compose up --build -d
```
Verify logs:
```bash
docker-compose logs -f web
docker-compose logs -f worker
```

## 3. Database Backups & Disaster Recovery
### Automated Backup
Run the backup script (requires `pg_dump` on the host or executed inside the DB container):
```bash
python scripts/backup_db.py --output backups/
```
### Database Restore
To restore a custom format backup file created with `pg_dump -F c`:
```bash
pg_restore -h <DB_HOST> -p <DB_PORT> -U <DB_USER> -d <DB_NAME> -c -v backups/<backup_file>.sql
```

## 4. Background Job Worker
Periodic background tasks (appointment reminders, vaccination alerts, inventory checks) run via:
```bash
flask run-jobs
```
Or individually:
```bash
flask send-reminders --job all
flask check-inventory-alerts
```

