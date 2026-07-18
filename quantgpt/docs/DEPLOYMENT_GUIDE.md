# Deployment and recovery guide

## Pre-flight

Provision TLS termination, a DNS name, encrypted persistent volumes, off-host encrypted backup storage, and a secret manager. Set all values below outside source control:

- `QUANTGPT_JWT_SECRET` (48+ random bytes)
- `QUANTGPT_ADMIN_PASSWORD` (unique, strong)
- `POSTGRES_PASSWORD`, `DATABASE_URL`, `OPENALGO_API_KEY`
- `GRAFANA_ADMIN_USER`, `GRAFANA_ADMIN_PASSWORD`
- HTTPS-only `BACKEND_CORS_ORIGINS` and your public host in `BACKEND_TRUSTED_HOSTS`

Use a least-privilege database user. Restrict public ingress to the TLS reverse proxy; Grafana’s port defaults to loopback only.

## Release

```sh
docker compose -f docker-compose.yml -f docker-compose.production.yml pull
docker compose -f docker-compose.yml -f docker-compose.production.yml up -d --build
docker compose -f docker-compose.yml -f docker-compose.production.yml exec -T backend alembic upgrade head
curl -fsS https://api.example.com/api/v1/health/ready
```

Review Grafana, error-rate alerts, and the readiness endpoint before routing traffic. Roll back by redeploying the previous immutable image tag; never roll back a database migration without a tested, approved downgrade.

## Backup and recovery

Run `BACKUP_DIR=/mounted/encrypted/path POSTGRES_DB=... POSTGRES_USER=... scripts/backup-postgres.sh` daily and test restore quarterly. Store the dump checksum with the backup. A restore is destructive and requires `CONFIRM_RESTORE` to exactly match the target database name.

Recovery steps: isolate traffic, restore to a clean environment, run migrations, validate `/ready`, compare audit volume and critical tables, then switch traffic after business approval.
