# Deployment guide

Target: Linux VPS (Ubuntu 22.04/24.04), Docker Compose, three bots + Postgres + Redis.

## 0. Prereqs on local machine

- SSH key ready (`~/.ssh/id_ed25519.pub`).
- Repo accessible from server (public GitHub or deploy key).
- Values for all secrets in [.env.prod.example](../.env.prod.example).

## 1. First SSH to server

```bash
ssh root@<server-ip>
```

Put your public key into `/root/.ssh/authorized_keys` if the provider did not already.

## 2. Server bootstrap (as root)

```bash
# Option A: clone repo first, then bootstrap
apt-get update && apt-get install -y git
git clone <repo-url> /tmp/fitness-bot
bash /tmp/fitness-bot/scripts/server_bootstrap.sh

# Option B: one-liner via curl (after repo is public)
# curl -fsSL https://raw.githubusercontent.com/<owner>/<repo>/main/scripts/server_bootstrap.sh | bash
```

The script installs Docker + compose plugin, creates user `deploy`, opens only 22/tcp in UFW, copies root's `authorized_keys` to the deploy user.

## 3. Switch to deploy user

```bash
ssh deploy@<server-ip>
cd /opt/fitness-bot
git clone <repo-url> .
```

## 4. Fill .env

```bash
cp .env.prod.example .env
nano .env
```

Required:
- `BOT_TOKEN`, `COLLECTOR_BOT_TOKEN`, `CONTEXT_BOT_TOKEN`
- `ADMIN_IDS` (comma-separated Telegram user IDs)
- `DB_PASSWORD` (strong)
- `OPENAI_API_KEY`

Leave `DB_HOST=postgres`, `REDIS_HOST=redis`, `USE_REDIS=true` — they must match compose service names.

## 5. Deploy

```bash
bash scripts/deploy.sh
# or:  make deploy
```

This runs: git pull → build image → start postgres/redis → `alembic upgrade head` → start all three bots.

Seed system data once:

```bash
make seed-products
make seed-exercises
```

## 6. Verify

```bash
make ps        # all services Up, postgres/redis healthy
make logs      # should show polling loops, no Traceback
```

Message `/start` to the bot in Telegram.

## Routine ops

| Task                   | Command                         |
|------------------------|---------------------------------|
| Redeploy latest main   | `make deploy`                   |
| Tail all bot logs      | `make logs`                     |
| Tail one bot           | `make logs-bot` / `-collector` / `-context` |
| Run migration manually | `make migrate`                  |
| Shell inside container | `make shell`                    |
| Restart bots only      | `make restart`                  |
| Stop everything        | `make down`                     |

## Backups

Postgres data lives in the named volume `pgdata`. Dump example:

```bash
docker compose -f docker-compose.prod.yml exec postgres \
  pg_dump -U fitness_bot fitness_bot | gzip > backup_$(date +%F).sql.gz
```

Copy off-server with `scp`.

## Hardening checklist

- Disable root SSH: `PermitRootLogin no`, `PasswordAuthentication no` in `/etc/ssh/sshd_config`, then `systemctl reload ssh`.
- UFW is already restricted to 22/tcp. DB/Redis have no published ports — reachable only inside the compose network.
- Rotate `BOT_TOKEN` and `OPENAI_API_KEY` if they ever leak; `.env` is git-ignored.

## Troubleshooting

- `TelegramNetworkError: Cannot connect to host api.telegram.org:443` — host has no route to Telegram. On RU VPS: check that the provider doesn't block it, or route through a proxy.
- `alembic upgrade head` fails with `relation already exists` — DB was previously populated without migrations; `alembic stamp head` once, then continue.
- Bots loop-crash — `make logs-bot` and look for the first Traceback. Fix .env or code, then `make deploy`.
