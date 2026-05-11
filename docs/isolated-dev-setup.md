# Isolated Local Development

This repository is pre-wired for isolated local development to avoid collisions with
other projects on the same machine.

## System defaults

- Project slug: `his_monorepo`
- Backend API: `http://127.0.0.1:8110`
- Frontend UI: `http://127.0.0.1:3310`
- Database: `his_monorepo_db`
- Database user: `his_monorepo_user`

Defaults are centrally defined in [`scripts/dev-env.sh`](/home/software-engineer/his/his-monorepo/scripts/dev-env.sh).

## One-time setup

1. Install backend dependencies.

```bash
cd /home/software-engineer/his/his-monorepo
python3 -m venv .venv
.venv/bin/pip install -r requirements
.venv/bin/pip install alembic psycopg2-binary
```

2. Install frontend dependencies.

```bash
cd /home/software-engineer/his/his-monorepo/clinic-app
pnpm install
```

3. Generate synchronized env files for backend and frontend.

```bash
cd /home/software-engineer/his/his-monorepo
./scripts/sync-local-env.sh
```

4. Create the isolated Postgres role/database.

```bash
cd /home/software-engineer/his/his-monorepo
PGPASSWORD=postgres ./scripts/setup-isolated-db.sh
```

5. Apply migrations.

```bash
cd /home/software-engineer/his/his-monorepo
. ./.venv/bin/activate
DATABASE_URL="$(grep '^DATABASE_URL=' .env | cut -d'=' -f2-)" alembic upgrade head
```

## Full reset (clears all users and data)

```bash
cd /home/software-engineer/his/his-monorepo
PGPASSWORD=postgres ./scripts/reset-isolated-db.sh
```

## Start services

Backend:

```bash
cd /home/software-engineer/his/his-monorepo
./scripts/start-backend-isolated.sh
```

Frontend:

```bash
cd /home/software-engineer/his/his-monorepo
./scripts/start-frontend-isolated.sh
```

## Environment files

- Backend env: `/home/software-engineer/his/his-monorepo/.env`
- Frontend env: `/home/software-engineer/his/his-monorepo/clinic-app/.env.local`
