# Project Context

Last generated: 2026-04-24 22:51

This file is the compact startup memory for coding agents working in this repository.
Read it before broad exploration, then inspect only the specific files needed for the task.

## Purpose

Fitness Telegram Bot is a Russian-language Telegram bot for calorie tracking, nutrition logs, workouts, recipes, product catalogs, analytics, subscriptions, and admin workflows. It also has a collector bot for collecting user-submitted products, exercises, and recipes into a review queue.

## Stack

Python 3.12+, aiogram 3, SQLAlchemy 2 async, Alembic, Pydantic 2, pydantic-settings, OpenAI API, Redis, PostgreSQL 16 in production, SQLite for local development, Docker Compose, pytest, Ruff.

## Dependencies

- `aiogram>=3.15,<4`
- `sqlalchemy[asyncio]>=2.0,<3`
- `asyncpg>=0.30,<1`
- `aiosqlite>=0.20,<1`
- `alembic>=1.14,<2`
- `pydantic>=2.0,<3`
- `pydantic-settings>=2.0,<3`
- `openai>=1.60,<2`
- `redis>=5.0,<6`
- `pillow>=11.0,<12`

## Commands

```powershell
python -m bot
python -m collector_bot
python scripts/seed_products.py
python scripts/seed_exercises.py
alembic upgrade head
python -m pytest
python -m ruff check .
python -m ruff format .
docker compose up -d
```

## Architecture

The core flow is:

```text
Handler -> Service -> Repository -> DB
```

Handlers do Telegram I/O and FSM. Services hold testable business logic. Repositories own SQLAlchemy queries. Models define ORM schema. Schemas are Pydantic DTOs. States hold aiogram FSM. Keyboards build UI markup. Middlewares inject DB sessions, users, throttling, and logging.

## Database Modes

`bot/config.py` uses SQLite when `DB_HOST` is empty and PostgreSQL when `DB_HOST` is set. SQLite local mode auto-creates tables on startup. PostgreSQL should use Alembic migrations. Keep model changes compatible with both engines unless there is an explicit reason.

## Domain Rules

- Meal item calories/macros are denormalized at log time. Do not recompute historical meals from current product rows.
- Product and exercise catalogs are hybrid: `user_id IS NULL` is system-wide, `user_id = current_user` is personal.
- Mutating child rows must verify ownership through the parent entity.
- Router order matters: global main menu handling should stay before state-bound feature routers.
- User-facing text is Russian. Code, identifiers, comments, logs, and commit messages should be English.

## Module Map

- `bot/handlers`: Telegram I/O, callback parsing, message replies, FSM transitions. (19 files)
- `bot/services`: Business logic, designed to be testable without Telegram. (19 files)
- `bot/repositories`: SQLAlchemy query layer. (10 files)
- `bot/models`: SQLAlchemy ORM schema. (10 files)
- `bot/schemas`: Pydantic DTOs. (7 files)
- `bot/states`: aiogram FSM states and menu constants. (6 files)
- `bot/keyboards`: Reply and inline keyboard builders. (7 files)
- `bot/middlewares`: DB session, user injection, throttling, state logging. (5 files)
- `bot/integrations`: External API wrappers. (3 files)
- `collector_bot`: Second Telegram bot for collecting submissions. (8 files)
- `tests`: pytest coverage for services, handlers, repositories. (12 files)
- `alembic`: Database migrations. (8 files)
- `scripts`: Local maintenance and seed scripts. (5 files)

## File Inventory

### .claude

- `.claude/settings.local.json`

### .dockerignore

- `.dockerignore`

### .env.example

- `.env.example`

### .env.prod.example

- `.env.prod.example`

### .gitignore

- `.gitignore`

### .serena

- `.serena/.gitignore`
- `.serena/cache/python/document_symbols.pkl`
- `.serena/cache/python/raw_document_symbols.pkl`
- `.serena/memories/agent_bridge.md`
- `.serena/memories/architecture_and_domain_rules.md`
- `.serena/memories/coding_conventions.md`
- `.serena/memories/context_bot_workspace.md`
- `.serena/memories/project_assessment_2026_04_23.md`
- `.serena/memories/project_overview.md`
- `.serena/memories/suggested_commands.md`
- `.serena/memories/task_completion_checklist.md`
- `.serena/project.local.yml`
- `.serena/project.yml`

### AGENTS.md

- `AGENTS.md`

### CLAUDE.md

- `CLAUDE.md`

### Dockerfile

- `Dockerfile`

### Makefile

- `Makefile`

### README.md

- `README.md`

### alembic

- `alembic/env.py`
- `alembic/script.py.mako`
- `alembic/versions/.gitkeep`
- `alembic/versions/20260420_add_workout_burned.py`
- `alembic/versions/20260421_muscle_group_enum.py`
- `alembic/versions/20260422_add_submissions.py`
- `alembic/versions/20260423_agent_bridge.py`
- `alembic/versions/20260423_workout_expansion.py`

### alembic.ini

- `alembic.ini`

### bot

- `bot/__init__.py`
- `bot/__main__.py`
- `bot/access.py`
- `bot/callbacks/__init__.py`
- `bot/callbacks/factory.py`
- `bot/config.py`
- `bot/factory.py`
- `bot/filters/__init__.py`
- `bot/filters/menu.py`
- `bot/handlers/__init__.py`
- `bot/handlers/admin.py`
- `bot/handlers/analytics/__init__.py`
- `bot/handlers/analytics/dashboard.py`
- `bot/handlers/common.py`
- `bot/handlers/main_menu.py`
- `bot/handlers/nutrition/__init__.py`
- `bot/handlers/nutrition/add_meal.py`
- `bot/handlers/nutrition/daily_summary.py`
- `bot/handlers/onboarding.py`
- `bot/handlers/products/__init__.py`
- `bot/handlers/products/create.py`
- `bot/handlers/products/favorites.py`
- `bot/handlers/recipes/__init__.py`
- `bot/handlers/recipes/create.py`
- `bot/handlers/recipes/list_recipes.py`
- `bot/handlers/subscription.py`
- `bot/handlers/workout/__init__.py`
- `bot/handlers/workout/start_workout.py`
- `bot/integrations/__init__.py`
- `bot/integrations/food_api.py`
- `bot/integrations/openai_client.py`
- `bot/keyboards/__init__.py`
- `bot/keyboards/inline.py`
- `bot/keyboards/nutrition.py`
- `bot/keyboards/onboarding.py`
- `bot/keyboards/reply.py`
- `bot/keyboards/stats.py`
- `bot/keyboards/workout.py`
- `bot/middlewares/__init__.py`
- `bot/middlewares/db.py`
- `bot/middlewares/state_logger.py`
- `bot/middlewares/throttle.py`
- `bot/middlewares/user.py`
- `bot/models/__init__.py`
- `bot/models/agent.py`
- `bot/models/base.py`
- `bot/models/exercise.py`
- `bot/models/meal.py`
- `bot/models/product.py`
- `bot/models/recipe.py`
- `bot/models/submission.py`
- `bot/models/user.py`
- `bot/models/workout.py`
- `bot/repositories/__init__.py`
- `bot/repositories/agent.py`
- `bot/repositories/base.py`
- `bot/repositories/exercise.py`
- `bot/repositories/meal.py`
- `bot/repositories/product.py`
- `bot/repositories/recipe.py`
- ... 39 more

### collector_bot

- `collector_bot/__init__.py`
- `collector_bot/__main__.py`
- `collector_bot/factory.py`
- `collector_bot/handlers/__init__.py`
- `collector_bot/handlers/common.py`
- `collector_bot/handlers/submit.py`
- `collector_bot/keyboards.py`
- `collector_bot/states.py`

### context_bot

- `context_bot/README.md`
- `context_bot/__init__.py`
- `context_bot/__main__.py`
- `context_bot/factory.py`
- `context_bot/handlers/__init__.py`
- `context_bot/handlers/common.py`
- `context_bot/handlers/monitoring.py`

### data

- `data/logs/bot.stderr.log`
- `data/logs/bot.stdout.log`
- `data/product_aliases.csv`
- `data/products_ru.csv`

### debug.log

- `debug.log`

### docker-compose.prod.yml

- `docker-compose.prod.yml`

### docker-compose.yml

- `docker-compose.yml`

### docs

- `docs/DEPLOY.md`
- `docs/PROJECT_CONTEXT.md`

### pyproject.toml

- `pyproject.toml`

### scripts

- `scripts/deploy.sh`
- `scripts/seed_exercises.py`
- `scripts/seed_products.py`
- `scripts/server_bootstrap.sh`
- `scripts/update_project_context.py`

### tests

- `tests/test_handlers/__init__.py`
- `tests/test_handlers/test_main_menu_keyboard.py`
- `tests/test_handlers/test_stats_dashboard.py`
- `tests/test_repositories/test_agent_bridge.py`
- `tests/test_repositories/test_exercise_catalog.py`
- `tests/test_services/test_agent_commands.py`
- `tests/test_services/test_analytics_period.py`
- `tests/test_services/test_analytics_streak.py`
- `tests/test_services/test_calorie_calc.py`
- `tests/test_services/test_entitlements.py`
- `tests/test_services/test_my_day.py`
- `tests/test_services/test_workout_burned.py`

## Agent Workflow

- Use Context7 for current docs about libraries and tools.
- Use Serena for local code symbol navigation and memory when available.
- Use this file as the first context layer and avoid reading the entire repository unless necessary.
- After architecture-level changes, run `python scripts/update_project_context.py` and update any available MCP memories with durable decisions only.
- Never store secrets, `.env` values, tokens, credentials, database dumps, or transient debug output.
