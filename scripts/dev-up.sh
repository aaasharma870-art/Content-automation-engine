#!/usr/bin/env bash
set -euo pipefail

echo "=== AI Brain — Starting Development Environment ==="

# Check for .env file
if [ ! -f .env ]; then
    echo "No .env file found. Copying from .env.example..."
    cp .env.example .env
    echo "  Created .env — please edit it with your API keys before continuing."
    exit 1
fi

# Build and start all services
echo "1. Building Docker images..."
docker compose build

echo "2. Starting services..."
docker compose up -d

echo "3. Waiting for PostgreSQL to be ready..."
until docker compose exec -T postgres pg_isready -U "${DB_USER:-aibrain}" > /dev/null 2>&1; do
    sleep 1
done
echo "   PostgreSQL is ready."

echo "4. Running database migrations and seeds..."
bash scripts/init-db.sh

echo "5. Creating MinIO bucket..."
docker compose exec -T minio mc alias set local http://localhost:9000 "${S3_ACCESS_KEY:-minioadmin}" "${S3_SECRET_KEY:-minioadmin}" 2>/dev/null || true
docker compose exec -T minio mc mb local/"${S3_BUCKET:-aibrain-assets}" 2>/dev/null || true

echo ""
echo "=== All services are running ==="
echo "  Orchestrator: http://localhost:3000/api/v1/health"
echo "  AI Services:  http://localhost:8000/api/v1/health"
echo "  Renderer:     http://localhost:8001/api/v1/health"
echo "  n8n:          http://localhost:5678"
echo "  Grafana:      http://localhost:3001"
echo "  MinIO:        http://localhost:9001"
