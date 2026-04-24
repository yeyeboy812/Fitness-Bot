#!/usr/bin/env bash
# Idempotent redeploy: pull, build, migrate, restart.
# Run from the repo root on the server as the deploy user.
set -euo pipefail

COMPOSE="docker compose -f docker-compose.prod.yml"
BRANCH="${BRANCH:-main}"

if [[ ! -f .env ]]; then
  echo "ERROR: .env not found. Copy .env.prod.example to .env and fill it." >&2
  exit 1
fi

echo "==> git fetch & fast-forward $BRANCH"
git fetch --quiet origin "$BRANCH"
git checkout "$BRANCH"
git pull --ff-only origin "$BRANCH"

echo "==> build image"
$COMPOSE build

echo "==> start infra (postgres, redis)"
$COMPOSE up -d postgres redis

echo "==> alembic migrate"
$COMPOSE run --rm bot alembic upgrade head

echo "==> (re)start bots"
$COMPOSE up -d bot collector_bot context_bot

echo "==> status"
$COMPOSE ps
