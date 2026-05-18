# KSH Enterprise HIS Monorepo

## System overview

This repository contains the Specialist Hospital Kazaure Hospital Information System (HIS). HIS is the parent enterprise platform; EMR/clinical records are implemented as a clinical subdomain inside the HIS ecosystem, not as a separate platform.

The monorepo contains:

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
