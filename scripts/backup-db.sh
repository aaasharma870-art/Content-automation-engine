#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/aibrain_$TIMESTAMP.sql.gz"

mkdir -p "$BACKUP_DIR"

echo "Backing up database to $BACKUP_FILE..."

docker compose exec -T postgres pg_dump \
    -U "${DB_USER:-aibrain}" \
    -d aibrain \
    --no-owner \
    --no-privileges \
    | gzip > "$BACKUP_FILE"

SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo "Backup complete: $BACKUP_FILE ($SIZE)"

# Cleanup: keep only last 7 backups
ls -t "$BACKUP_DIR"/aibrain_*.sql.gz | tail -n +8 | xargs -r rm --
echo "Cleaned up old backups (keeping last 7)"
