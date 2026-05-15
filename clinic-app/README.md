# Clinic Frontend

## Local development

1. Install dependencies:

```bash
cd /home/software-engineer/his/his-monorepo/clinic-app
pnpm install
```

2. Ensure the root env sync has been run:

```bash
cd /home/software-engineer/his/his-monorepo
./scripts/sync-local-env.sh
```

3. Start the frontend:

```bash
cd /home/software-engineer/his/his-monorepo
./scripts/start-frontend-isolated.sh
```

Default URL: `http://127.0.0.1:3310`

## Runtime configuration

- API base URL: `NEXT_PUBLIC_API_URL` (from `clinic-app/.env.local`)
- Default local API: `http://127.0.0.1:8110/api`
