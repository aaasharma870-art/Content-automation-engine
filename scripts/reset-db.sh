#!/usr/bin/env bash
set -euo pipefail

echo "=== AI Brain — Database Reset ==="
echo "WARNING: This will DROP and recreate the entire database."
read -p "Continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
fi

DB_USER="${DB_USER:-aibrain}"

echo "1. Dropping and recreating database..."
docker compose exec -T postgres psql -U "$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS aibrain;"
docker compose exec -T postgres psql -U "$DB_USER" -d postgres -c "CREATE DATABASE aibrain OWNER $DB_USER;"

echo "2. Running all migrations..."
for migration in db/migrations/*.sql; do
    echo "   Applying: $(basename "$migration")"
    docker compose exec -T postgres psql -U "$DB_USER" -d aibrain < "$migration"
done

echo "3. Running seed data..."
for seed in db/seed/*.sql; do
    echo "   Seeding: $(basename "$seed")"
    docker compose exec -T postgres psql -U "$DB_USER" -d aibrain < "$seed"
done

echo ""
echo "=== Database reset complete ==="
