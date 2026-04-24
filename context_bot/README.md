# Context Bot Boundary

`context_bot/` is the dedicated workspace for the assistant/context bot.

It exists to keep the control-plane code isolated from:
- `bot/` - end-user fitness bot flows
- `collector_bot/` - submission intake bot

## Ownership

`context_bot/` owns:
- Telegram handlers, commands, and orchestration for the context bot
- future assistant-specific prompts, policies, and control workflows
- read access to shared bridge data (`agent_events`, `agent_commands`, `user_shortcuts`)

Shared domain code stays in `bot/`:
- ORM models
- repositories
- business services
- migrations

## Boundaries

Allowed dependencies for `context_bot/`:
- `bot.models.*`
- `bot.repositories.*`
- `bot.services.agent_*`
- read-only access to other shared services when needed

Avoid importing into `context_bot/`:
- `bot.handlers.*`
- `bot.keyboards.*`
- `collector_bot.*`

Mutation rules:
- do not perform arbitrary SQL from the context bot layer
- enqueue typed `agent_commands` or call shared services explicitly
- keep Telegram I/O inside `context_bot/`, business mutations in shared services

## Entrypoint

Run with:

```powershell
python -m context_bot
```
