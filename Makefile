.PHONY: up down build logs start stop rebuild \
       db-migrate db-seed db-reset \
       test test-unit smoke-test \
       run-one-job clean

# ── Start / Stop / Build ──────────────────
up start:
	docker compose up -d

down stop:
	docker compose down

build:
	docker compose build

rebuild:
	docker compose down
	docker compose build --no-cache
	docker compose up -d

# ── Logs ──────────────────────────────────
logs:
	docker compose logs -f

logs-orchestrator:
	docker compose logs -f orchestrator

logs-ai:
	docker compose logs -f ai-services

logs-renderer:
	docker compose logs -f renderer

# ── Database ──────────────────────────────
db-migrate:
	bash scripts/init-db.sh

db-seed:
	bash scripts/init-db.sh

db-reset:
	bash scripts/reset-db.sh

# ── Testing ───────────────────────────────
test: test-unit

test-unit:
	cd services/ai-services && python -m pytest tests/ -v
	cd services/renderer && python -m pytest tests/ -v

smoke-test:
	bash scripts/smoke-test.sh

# ── Jobs ──────────────────────────────────
run-one-job:
	bash scripts/run-one-job.sh

# ── Cleanup ───────────────────────────────
clean:
	docker compose down -v --remove-orphans
