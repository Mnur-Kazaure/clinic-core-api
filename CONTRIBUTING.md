# Contributing Guide

## Branching Model
- Do not push directly to `main`.
- Create feature branches from `develop`:
  - `feat/<short-scope>`
  - `fix/<short-scope>`
  - `chore/<short-scope>`
- Open PR to `develop` for integration work.
- Open PR from `develop` to `main` for release-ready changes.

## Pull Requests
- Keep PRs focused and small enough to review.
- Use the PR template and fill all sections.
- Link related issue(s) when available.
- Add screenshots/logs for UI or workflow changes.

## Required Quality Gates
- PR CI must pass.
- Required review approval must be obtained.
- Playwright E2E should be green for high-risk flows (auth, billing, lab, pharmacy, admissions).

## Engineering Standards
- Never trust frontend input; enforce validation server-side.
- Enforce RBAC server-side for every protected action.
- Prefer modular services and clear boundaries in backend code.
- Add/adjust tests for behavior changes.
- Include migration and rollback notes for schema/data changes.

## Commit Convention
- Use Conventional Commits where practical:
  - `feat: ...`
  - `fix: ...`
  - `refactor: ...`
  - `test: ...`
  - `chore: ...`

## Local Validation (recommended)
- Backend fast checks:
  - `python3 -m pytest app/tests/test_lab_workflow_contract.py -q`
  - `python3 -m pytest app/tests/test_billing_lab_payment_gate.py -q`
- Frontend build:
  - `pnpm --dir clinic-app build`

## Security
- Never commit secrets or credentials.
- Use GitHub secrets for CI.
- Escalate security-related defects immediately.

