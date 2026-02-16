#!/usr/bin/env bash
set -euo pipefail

echo "=== AI Brain — Full Rebuild ==="

echo "1. Stopping all services..."
docker compose down

echo "2. Rebuilding images (no cache)..."
docker compose build --no-cache

echo "3. Starting services..."
docker compose up -d

echo "4. Waiting for PostgreSQL..."
until docker compose exec -T postgres pg_isready -U "${DB_USER:-aibrain}" > /dev/null 2>&1; do
    sleep 1
done

echo "5. Running migrations..."
bash scripts/init-db.sh

echo ""
echo "=== Rebuild complete ==="
