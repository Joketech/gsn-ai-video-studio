# Working step by step with Claude Code and Codex

Joke, use the repository as the shared source of truth. Open it in your existing Claude Code or Codex workspace. The following are task prompts, not claims that either coding tool has already executed them.

## First session

1. Start Docker Desktop and follow the README. Make sure `docker compose config --quiet` succeeds.
2. Ask one coding tool: “Read README.md and docs/ARCHITECTURE.md. Start the local stack. Run scripts/smoke.py. Show the actual results. Do not enable paid providers.”
3. Ask the other tool: “Review services/api/gsn/main.py and tests for tenant isolation and consent bypasses. Report concrete issues with reproductions; do not edit files yet.”
4. Fix findings one at a time, rerun the relevant tests, then run the full backend suite and dashboard build. Record which integrations were exercised.
5. Use different branches or checkouts for concurrent changes. Do not run destructive tests against a database containing real profiles.

## Run backend checks outside Docker

Python 3.12+, from repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r services/api/requirements.lock
$env:AUTH_SECRET='local-test-only-secret-at-least-32-characters'
Set-Location services/api
python -m pytest -q
```

Tests use an isolated SQLite database by default and replace storage with an in-memory fake. Set `TEST_DATABASE_URL` only to a disposable PostgreSQL database: fixtures delete and recreate its tables. CI uses a dedicated PostgreSQL service. Passing these tests does not verify MinIO or Redis networking; run `scripts/smoke.py` against Compose for that.

For a direct development API, configure `DATABASE_URL`, `S3_ENDPOINT`, `REDIS_URL` and storage keys to reachable services; run `python -m gsn.migrate`, then `uvicorn gsn.main:app --reload`. Start `python -m gsn.worker` separately. With the default Compose file, data services are intentionally not exposed to host applications; develop inside the API/worker containers or create a local-only port override. `COOKIE_SECURE=false` is required for local HTTP testing.

## Dashboard checks

From `apps/web` with Node 22:

```powershell
npm ci
npm run typecheck
npm run build
npm run dev
```

Dashboard defaults to `http://localhost:8000`. `NEXT_PUBLIC_API_URL` is embedded at build time; rebuild when changing it. The UI shows the newest 200 records per category. It supports creating records and revoking consent; full editing, pagination, project-filtered lists and scene ordering are later work.

## Suggested implementation assignments

- Claude Code task: “Implement the documented Hermes bridge against my actual installed version. Keep mock mode as the default. Add contract tests and a live opt-in smoke test. Do not send private references to an external service without explicit configuration.”
- Codex task: “Review the Hermes bridge implementation, run its tests and verify tenant scoping. Update the verification document with only observed outcomes.”
- Next joint task: “Add a sandbox cloud GPU adapter and job lease heartbeats. Require a hard cost ceiling and explicit provider configuration. Keep generation disabled until one authorized short clip passes inspection.”

Keep secrets out of prompts, commits and logs. Never mark a live integration working because a mock passed. The included CI workflow is ready to run after placing this folder at the root of a Git repository and pushing it; no remote repository or CI run has been created by this build.
