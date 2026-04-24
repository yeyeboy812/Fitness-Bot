<!-- context7 -->
Use Context7 MCP to fetch current documentation whenever the user asks about a library, framework, SDK, API, CLI tool, or cloud service, even well-known ones like React, Next.js, Prisma, Express, Tailwind, Django, Spring Boot, aiogram, SQLAlchemy, Alembic, Pydantic, OpenAI, Redis, Docker, or GitHub. This includes API syntax, configuration, version migration, library-specific debugging, setup instructions, and CLI tool usage. Prefer this over web search for library docs.

Do not use Context7 for refactoring, writing scripts from scratch, debugging business logic, code review, or general programming concepts.

Context7 workflow:

1. Start with `resolve-library-id` using the library name and the user's full question, unless the user provides an exact `/org/project` library ID.
2. Pick the best match by exact name, relevance, snippet count, source reputation, benchmark score, and requested version.
3. Call `query-docs` with the selected library ID and the user's full question.
4. Answer using the fetched docs.
<!-- context7 -->

## Project Context Bootstrap

At the start of each new session in this repository:

1. Read this file first.
2. Read `docs/PROJECT_CONTEXT.md` before broad code exploration.
3. If `docs/PROJECT_CONTEXT.md` is missing or clearly stale, run `python scripts/update_project_context.py` and then read it.
4. Prefer targeted lookup over loading whole files: use `rg`, Serena symbol tools, and focused file reads.
5. If Serena MCP is available, activate the project, check onboarding, and use Serena memories/symbol search for local code understanding.
6. If Serena MCP is unavailable, continue with `docs/PROJECT_CONTEXT.md`, `rg`, and direct file reads.

## Memory Write-Back

After meaningful changes, keep the project memory current:

1. Run `python scripts/update_project_context.py` when files, dependencies, commands, architecture, database models, migrations, bot flows, or tests change.
2. If Serena memory tools are available, update concise memories for architecture, commands, workflows, and important decisions.
3. If agentmemory MCP is available in the current client, store only durable facts, patterns, and decisions.
4. Never store secrets, `.env` values, tokens, personal credentials, database dumps, or transient debug output.
5. Keep memories compact. Store the map and decisions, not full source files.

## Repository Rules

User-facing bot text is Russian. Code, identifiers, comments, logs, and commit messages should be English.

Preserve the layered architecture:

```text
Handler -> Service -> Repository -> DB
```

Handlers handle Telegram I/O and FSM only. Services contain testable business logic. Repositories contain SQLAlchemy queries. Models define ORM schema. Keyboards and states stay in their domain modules.

Use SQLite local fallback and PostgreSQL production compatibility. Avoid PostgreSQL-only model features unless there is a migration and an explicit reason.
