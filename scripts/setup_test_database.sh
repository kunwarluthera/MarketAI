#!/usr/bin/env bash
set -euo pipefail
TEST_DATABASE_URL="${TEST_DATABASE_URL:?TEST_DATABASE_URL is required}"
DEVELOPMENT_DATABASE_URL="${DEVELOPMENT_DATABASE_URL:-}"
docker compose run --rm -e TEST_DATABASE_URL="$TEST_DATABASE_URL" -e DEVELOPMENT_DATABASE_URL="$DEVELOPMENT_DATABASE_URL" api python -c 'from app.common.test_database import assert_safe_test_database; import os; assert_safe_test_database(os.environ["TEST_DATABASE_URL"], os.environ.get("DEVELOPMENT_DATABASE_URL"))'
echo "Using isolated integration database: ${TEST_DATABASE_URL##*/}"
echo "Waiting for isolated PostgreSQL readiness..."
for attempt in $(seq 1 30); do
  if docker compose exec -T test-db pg_isready -U postgres -d market_ai_test >/dev/null 2>&1 \
    && docker compose exec -T test-db psql -U postgres -d market_ai_test -tAc 'SELECT 1' | grep -qx 1; then
    echo "Test database ready (attempt ${attempt})."
    break
  fi
  if [ "$attempt" -eq 30 ]; then
    echo "Test database did not become ready; container logs:" >&2
    docker compose logs test-db >&2
    exit 1
  fi
  echo "Readiness attempt ${attempt}/30 failed; retrying..."
  sleep 2
done
docker compose run --rm -e DATABASE_URL="$TEST_DATABASE_URL" api alembic upgrade head
