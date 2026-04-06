# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Telegram-бот для подсчёта калорий (КБЖУ), логирования приёмов пищи и тренировок. Русскоязычная аудитория. AI-парсинг текста и фото еды через OpenAI.

## Tech Stack

Python 3.12+ · aiogram 3 · SQLAlchemy 2.x (async) · Alembic · Pydantic 2 · OpenAI · Redis · Docker Compose.

Production runs on **PostgreSQL 16 + asyncpg + Redis**. Local dev falls back to **SQLite (aiosqlite) + MemoryStorage** automatically — see "Dual-mode DB" below.

## Commands

```bash
# Run bot (auto-creates tables in SQLite mode)
python -m bot

# Seed 92 system products from data/products_ru.csv
python scripts/seed_products.py

# PostgreSQL migrations (Alembic)
alembic revision --autogenerate -m "..."
alembic upgrade head

# Tests
pytest                                          # all
pytest tests/test_services/test_calorie_calc.py # single file
pytest -k test_male_bmr                         # single test

# Lint
ruff check .
ruff format .

# Docker (production-like: PostgreSQL + Redis + bot)
docker compose up -d
docker compose exec bot alembic upgrade head
docker compose exec bot python scripts/seed_products.py
```

## Communication & Code Conventions

- **User-facing text: Russian.** Code, comments, commit messages, identifiers: English.
- Don't mix; handlers/keyboards return Russian strings, logs stay English.

## Architecture

Strict layered flow: **Handler → Service → Repository → DB**.

- **`bot/handlers/`** — Telegram I/O only. No business logic, no SQL. FSM state transitions live here. Handlers receive `session`, `user`, `user_repo` via middleware data injection.
- **`bot/services/`** — Pure business logic. Must be testable without Telegram or DB (inject repo instances). `calorie_calc.py` is pure functions (Mifflin-St Jeor BMR → TDEE → macro split).
- **`bot/repositories/`** — All SQLAlchemy queries. Inherit from `BaseRepository[ModelT]`. Do not leak `select()` statements into services.
- **`bot/models/`** — SQLAlchemy 2.x declarative ORM. All models inherit `TimestampMixin` (`created_at`, `updated_at`).
- **`bot/schemas/`** — Pydantic DTOs for crossing layer boundaries.
- **`bot/states/`** — aiogram `StatesGroup`s. The main user-facing FSM lives in `AppState` (`bot/states/app.py`); ancillary flows keep their own groups (`OnboardingSG`, `CreateRecipeSG`, `CreateProductSG`, `CreateExerciseSG`, `MealHistorySG`). `bot/states/app.py` also owns `MAIN_MENU_BUTTONS` and `INTERRUPTIBLE_STATE_NAMES`.
- **`bot/filters/`** — reusable aiogram filters. `MainMenuFilter` powers the top-priority menu router; `NotMainMenuFilter` guards every state-bound text handler so menu button labels are never captured as free-text input.
- **`bot/keyboards/`** — Reply (`reply.py` — `MAIN_MENU`) + Inline builders. New keyboards go into the domain-specific file.
- **`bot/middlewares/`** — `DbSessionMiddleware` (per-update async session + auto commit/rollback), `UserInjectMiddleware` (get-or-create `User` and inject as `user`), `ThrottleMiddleware` (0.5s anti-flood).
- **`bot/integrations/openai_client.py`** — thin async wrapper, `chat_json` (text) + `vision_json` (image, auto-resizes to 1024px for cost control).

### Entry point wiring

`bot/__main__.py` → `create_db_engine` → `create_session_factory` → `create_bot` + `create_dispatcher` (`bot/factory.py`). `factory.py` registers middlewares on `dp.update.outer_middleware` in order (db → user → throttle) and includes all routers via `handlers/__init__.register_all_routers`.

### FSM storage

`factory._create_storage` tries `RedisStorage` first, silently falls back to `MemoryStorage` if Redis is unreachable or the package is missing. **This fallback is intentional** — do not turn it into a hard error.

### Dual-mode DB (important)

`bot/config.py:database_url` returns **SQLite** when `DB_HOST` is empty, **PostgreSQL** otherwise. `bot/__main__.py` auto-creates tables via `Base.metadata.create_all` in SQLite mode; PostgreSQL requires Alembic migrations. `bot/models/base.py` enables WAL + FK pragmas on SQLite connect.

Same applies to `scripts/seed_products.py` — it auto-creates tables when running against SQLite.

When adding models: prefer types that work in **both** engines (avoid `JSONB`, pg-specific enums with `create_type=True`, etc.).

### Denormalization rule

`MealItem` stores denormalized КБЖУ (`calories`, `protein`, `fat`, `carbs`, `name_snapshot`) at the moment of logging. **Never recompute historical meals from the current `Product` row** — user weight/portions are frozen at entry time for historical accuracy. `NutritionService.log_meal` receives pre-calculated values from the handler.

### Hybrid catalog

`Product` and `Exercise` have a hybrid system/user catalog: `user_id IS NULL` → system-wide (seeded from CSV), `user_id = N` → owned by that user. `ProductRepository.search` always filters with `or_(user_id.is_(None), user_id == current_user)`. Follow this pattern for any new user-extensible catalog.

### Meal item ownership

`MealRepository.delete_item` joins through `Meal` to verify `user_id` (IDOR protection). Any mutation on child rows (recipe ingredients, workout sets, etc.) must do the same — never trust an ID from a callback without checking ownership.

## Developer context

Developer: Игорь. Vibe Coding — building projects with AI assistance. Goal: Junior AI Engineer → Senior AI Engineer.
