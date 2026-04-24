COMPOSE := docker compose -f docker-compose.prod.yml

.PHONY: help deploy up down restart build logs logs-bot logs-collector logs-context migrate seed-products seed-exercises shell ps prune

help:
	@echo "Targets:"
	@echo "  deploy            git pull + build + migrate + up (see scripts/deploy.sh)"
	@echo "  up / down         start / stop all services"
	@echo "  restart           restart all bots (keeps postgres/redis)"
	@echo "  build             rebuild image"
	@echo "  logs              tail logs for all bots"
	@echo "  logs-bot|collector|context   tail one bot"
	@echo "  migrate           alembic upgrade head"
	@echo "  seed-products     seed system products"
	@echo "  seed-exercises    seed system exercises"
	@echo "  shell             exec into bot container"
	@echo "  ps                compose ps"
	@echo "  prune             docker system prune -f"

deploy:
	bash scripts/deploy.sh

up:
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

restart:
	$(COMPOSE) restart bot collector_bot context_bot

build:
	$(COMPOSE) build

logs:
	$(COMPOSE) logs -f --tail=200 bot collector_bot context_bot

logs-bot:
	$(COMPOSE) logs -f --tail=200 bot

logs-collector:
	$(COMPOSE) logs -f --tail=200 collector_bot

logs-context:
	$(COMPOSE) logs -f --tail=200 context_bot

migrate:
	$(COMPOSE) run --rm bot alembic upgrade head

seed-products:
	$(COMPOSE) run --rm bot python scripts/seed_products.py

seed-exercises:
	$(COMPOSE) run --rm bot python scripts/seed_exercises.py

shell:
	$(COMPOSE) exec bot bash

ps:
	$(COMPOSE) ps

prune:
	docker system prune -f
