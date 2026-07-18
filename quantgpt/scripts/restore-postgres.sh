#!/usr/bin/env sh
set -eu

: "${POSTGRES_DB:?POSTGRES_DB is required}"
: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${1:?usage: restore-postgres.sh /absolute/path/to/backup.dump}"
backup=$1
[ -f "$backup" ] || { echo "Backup not found: $backup" >&2; exit 1; }

echo "This overwrites database '$POSTGRES_DB'. Set CONFIRM_RESTORE=$POSTGRES_DB to continue."
[ "${CONFIRM_RESTORE:-}" = "$POSTGRES_DB" ] || exit 2
docker compose exec -T postgres pg_restore -U "$POSTGRES_USER" --clean --if-exists --no-owner -d "$POSTGRES_DB" < "$backup"
docker compose exec -T backend alembic upgrade head
