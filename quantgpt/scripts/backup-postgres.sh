#!/usr/bin/env sh
set -eu

: "${BACKUP_DIR:?set BACKUP_DIR to a mounted encrypted backup destination}"
: "${POSTGRES_DB:?POSTGRES_DB is required}"
: "${POSTGRES_USER:?POSTGRES_USER is required}"

umask 077
stamp=$(date -u +%Y%m%dT%H%M%SZ)
target="$BACKUP_DIR/quantgpt-${stamp}.dump"
mkdir -p "$BACKUP_DIR"
docker compose exec -T postgres pg_dump -U "$POSTGRES_USER" -Fc "$POSTGRES_DB" > "$target"
sha256sum "$target" > "$target.sha256"
echo "Created $target and checksum"
