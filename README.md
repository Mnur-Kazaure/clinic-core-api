# HIS Monorepo (Clinic Information System)

## System overview

This repository contains:

- Backend API: FastAPI + SQLAlchemy + Alembic (`app/`, `alembic/`)
- Frontend app: Next.js (`clinic-app/`)
- Local dev automation: `scripts/`

## Architecture map

- Backend entrypoint: `app/main.py`
- API surface: `app/api/v1/*` mounted at `/api/v1`
- Domain services: `app/services/*`
- Data models: `app/models/*`
- Frontend entrypoint: `clinic-app/src/app/*`
- Frontend API client: `clinic-app/src/api/client.ts`

## Local setup

Use the isolated setup guide:

- [docs/isolated-dev-setup.md](/home/software-engineer/his/his-monorepo/docs/isolated-dev-setup.md)
