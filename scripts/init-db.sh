#!/usr/bin/env bash
set -euo pipefail

echo "Running database migrations..."

for migration in db/migrations/*.sql; do
    echo "  Applying: $migration"
    docker compose exec -T postgres psql \
        -U "${DB_USER:-aibrain}" \
        -d aibrain \
        -f "/docker-entrypoint-initdb.d/$(basename "$migration")"
done

echo "Running seed data..."
for seed in db/seed/*.sql; do
    echo "  Seeding: $seed"
    docker compose exec -T postgres psql \
        -U "${DB_USER:-aibrain}" \
        -d aibrain \
        -f "/seed/$(basename "$seed")"
done

echo "Database initialization complete."
