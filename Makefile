.PHONY: setup up down migrate seed dev test test-api test-web lint format typecheck e2e reset-demo logs health
setup:
	cp .env.example .env
	python3 -m venv .venv
	.venv/bin/pip install -e 'apps/api[dev]'
	cd apps/web && npm install
up:
	docker compose up --build -d
down:
	docker compose down
migrate:
	docker compose run --rm api alembic upgrade head
seed:
	curl -fsS -X POST -H 'Authorization: Bearer demo-local-token' http://localhost:8000/api/v1/paper/reset
dev:
	docker compose up --build
test: test-api test-web
test-api:
	TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5433/market_ai_test .venv/bin/pytest apps/api/tests -q
test-db-create:
	docker compose up -d test-db
test-db-drop:
	docker compose stop test-db
test-db-migrate: test-db-create
	TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@test-db:5432/market_ai_test DEVELOPMENT_DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/market_ai ./scripts/setup_test_database.sh
test-db-reset:
	docker compose stop test-db
	docker compose rm -f test-db
	docker volume rm aiproject_market_ai_test_db || true
	docker compose up -d test-db
	$(MAKE) test-db-migrate
test-integration: test-db-reset test-api
test-concurrency: test-integration
test-rollback: test-integration
test-financial-integrity: test-integration
test-web:
	cd apps/web && npm test
lint:
	.venv/bin/ruff check apps/api
format:
	.venv/bin/ruff format apps/api
	cd apps/web && npx prettier --write src
typecheck:
	.venv/bin/mypy apps/api/app
	cd apps/web && npm run typecheck
e2e:
	cd apps/web && npm run e2e
reset-demo: seed
logs:
	docker compose logs -f --tail=100
health:
	curl -fsS http://localhost:8000/health
