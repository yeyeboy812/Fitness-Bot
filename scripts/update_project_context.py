"""Refresh the compact project context used by coding agents.

The output is intentionally concise: it gives future sessions a startup map
without loading the whole repository into the prompt.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from pathlib import Path
import tomllib


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "PROJECT_CONTEXT.md"

EXCLUDED_DIRS = {
    ".git",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "fitness_bot.egg-info",
}
EXCLUDED_FILES = {
    ".env",
    "data/bot.db",
    "data/bot.db-shm",
    "data/bot.db-wal",
}

MODULE_NOTES = {
    "bot/handlers": "Telegram I/O, callback parsing, message replies, FSM transitions.",
    "bot/services": "Business logic, designed to be testable without Telegram.",
    "bot/repositories": "SQLAlchemy query layer.",
    "bot/models": "SQLAlchemy ORM schema.",
    "bot/schemas": "Pydantic DTOs.",
    "bot/states": "aiogram FSM states and menu constants.",
    "bot/keyboards": "Reply and inline keyboard builders.",
    "bot/middlewares": "DB session, user injection, throttling, state logging.",
    "bot/integrations": "External API wrappers.",
    "collector_bot": "Second Telegram bot for collecting submissions.",
    "tests": "pytest coverage for services, handlers, repositories.",
    "alembic": "Database migrations.",
    "scripts": "Local maintenance and seed scripts.",
}


def should_skip(path: Path) -> bool:
    rel = path.relative_to(ROOT).as_posix()
    if rel in EXCLUDED_FILES:
        return True
    return any(part in EXCLUDED_DIRS for part in path.parts)


def iter_files() -> list[str]:
    files: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or should_skip(path):
            continue
        files.append(path.relative_to(ROOT).as_posix())
    return sorted(files)


def load_dependencies() -> list[str]:
    pyproject = ROOT / "pyproject.toml"
    if not pyproject.exists():
        return []
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    return list(data.get("project", {}).get("dependencies", []))


def grouped_files(files: list[str]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for file in files:
        top = file.split("/", 1)[0]
        grouped[top].append(file)
    return dict(sorted(grouped.items()))


def bullet_lines(items: list[str], *, max_items: int = 80) -> list[str]:
    shown = items[:max_items]
    lines = [f"- `{item}`" for item in shown]
    if len(items) > max_items:
        lines.append(f"- ... {len(items) - max_items} more")
    return lines


def build_markdown() -> str:
    files = iter_files()
    deps = load_dependencies()
    groups = grouped_files(files)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    out: list[str] = [
        "# Project Context",
        "",
        f"Last generated: {now}",
        "",
        "This file is the compact startup memory for coding agents working in this repository.",
        "Read it before broad exploration, then inspect only the specific files needed for the task.",
        "",
        "## Purpose",
        "",
        "Fitness Telegram Bot is a Russian-language Telegram bot for calorie tracking, nutrition logs, workouts, recipes, product catalogs, analytics, subscriptions, and admin workflows. It also has a collector bot for collecting user-submitted products, exercises, and recipes into a review queue.",
        "",
        "## Stack",
        "",
        "Python 3.12+, aiogram 3, SQLAlchemy 2 async, Alembic, Pydantic 2, pydantic-settings, OpenAI API, Redis, PostgreSQL 16 in production, SQLite for local development, Docker Compose, pytest, Ruff.",
        "",
        "## Dependencies",
        "",
    ]

    out.extend(bullet_lines(deps, max_items=40) if deps else ["- No dependencies found in pyproject.toml."])

    out.extend(
        [
            "",
            "## Commands",
            "",
            "```powershell",
            "python -m bot",
            "python -m collector_bot",
            "python scripts/seed_products.py",
            "python scripts/seed_exercises.py",
            "alembic upgrade head",
            "python -m pytest",
            "python -m ruff check .",
            "python -m ruff format .",
            "docker compose up -d",
            "```",
            "",
            "## Architecture",
            "",
            "The core flow is:",
            "",
            "```text",
            "Handler -> Service -> Repository -> DB",
            "```",
            "",
            "Handlers do Telegram I/O and FSM. Services hold testable business logic. Repositories own SQLAlchemy queries. Models define ORM schema. Schemas are Pydantic DTOs. States hold aiogram FSM. Keyboards build UI markup. Middlewares inject DB sessions, users, throttling, and logging.",
            "",
            "## Database Modes",
            "",
            "`bot/config.py` uses SQLite when `DB_HOST` is empty and PostgreSQL when `DB_HOST` is set. SQLite local mode auto-creates tables on startup. PostgreSQL should use Alembic migrations. Keep model changes compatible with both engines unless there is an explicit reason.",
            "",
            "## Domain Rules",
            "",
            "- Meal item calories/macros are denormalized at log time. Do not recompute historical meals from current product rows.",
            "- Product and exercise catalogs are hybrid: `user_id IS NULL` is system-wide, `user_id = current_user` is personal.",
            "- Mutating child rows must verify ownership through the parent entity.",
            "- Router order matters: global main menu handling should stay before state-bound feature routers.",
            "- User-facing text is Russian. Code, identifiers, comments, logs, and commit messages should be English.",
            "",
            "## Module Map",
            "",
        ]
    )

    for module, note in MODULE_NOTES.items():
        count = len([f for f in files if f == module or f.startswith(f"{module}/")])
        out.append(f"- `{module}`: {note} ({count} files)")

    out.extend(["", "## File Inventory", ""])
    for group, group_files_list in groups.items():
        out.append(f"### {group}")
        out.append("")
        out.extend(bullet_lines(group_files_list, max_items=60))
        out.append("")

    out.extend(
        [
            "## Agent Workflow",
            "",
            "- Use Context7 for current docs about libraries and tools.",
            "- Use Serena for local code symbol navigation and memory when available.",
            "- Use this file as the first context layer and avoid reading the entire repository unless necessary.",
            "- After architecture-level changes, run `python scripts/update_project_context.py` and update any available MCP memories with durable decisions only.",
            "- Never store secrets, `.env` values, tokens, credentials, database dumps, or transient debug output.",
            "",
        ]
    )
    return "\n".join(out)


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(build_markdown(), encoding="utf-8")
    print(f"Updated {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
