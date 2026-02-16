#!/usr/bin/env bash
set -euo pipefail

echo "=== AI Brain — Stopping Development Environment ==="
docker compose down
echo "All services stopped. Data volumes preserved."
echo "To also remove data volumes: docker compose down -v"
