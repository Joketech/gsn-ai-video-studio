# GSN AI Video Studio — Phase 1

Joke Taiwo’s local production workspace, with replaceable cloud rendering and Hermes interfaces.

**Phase 1 generates a simulation report, not video.** No appearance model is trained, no voice is cloned, no GPU is rented, and no paid provider is called. Live adapters deliberately fail until implemented and tested. See `docs/VERIFICATION.md` for the evidence collected on this machine.

## Start here, Joke

1. Open this repository folder in your editor. Install and start Docker Desktop with Linux containers. You need Docker Compose v2. The first build downloads dependencies and container images.
2. In PowerShell, inside this folder, run:

   ```powershell
   Copy-Item .env.example .env
   $secretBytes = New-Object byte[] 32
   [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($secretBytes)
   $studioSecret = -join ($secretBytes | ForEach-Object { $_.ToString('x2') })
   (Get-Content .env) -replace '^AUTH_SECRET=.*', "AUTH_SECRET=$studioSecret" | Set-Content .env
   docker compose config --quiet
   docker compose up --build -d
   ```

3. Open [the dashboard](http://localhost:3000). Enter your email, a password of at least 12 characters, and “Joke Taiwo Studio”; click **Create workspace**. Each registration creates a separate workspace. There is no invitation or team-sharing flow in Phase 1.
4. Create a project, then create a scene with a script. Queue a simulation in **jobs**. It should change from queued to succeeded; download its JSON report. Refresh automatically runs every five seconds.
5. To add yourself: upload an authorized photograph and a consent-evidence file in **assets**. In **consents**, select the evidence, appearance scope and a future expiry. Create a character using that consent and photograph. Repeat with a WAV/MP3 recording and a separate voice consent for a voice profile. Recording consent is an attestation, not independent identity verification.
6. Create a scene using those profiles. Commercial scenes require commercial permission for both. Revoking a consent blocks subsequent submissions and queued work checked by the worker. It does not erase files or undo completed outputs.
7. Open **agent-tasks**, select a project and specialist, then submit an instruction. The result is explicitly simulated. The 13 roles include one orchestrator and 12 specialists.
8. Check **audit**. Run `python scripts/smoke.py` using Python 3.12+ to test the complete local simulation path with real services. A successful HTTP health response alone does not prove the queue or storage works.

To inspect errors: `docker compose logs api worker`. To stop: `docker compose down`. Named volumes preserve your files and database. Keep `.env` private. Local ports bind to localhost; database and Redis have no published ports. The MinIO console is at [localhost:9001](http://localhost:9001), using the S3 credentials in `.env`.

## Repository

```text
apps/web/                    Next.js App Router, TypeScript, dashboard
services/api/gsn/
  main.py                    authentication and tenant-scoped HTTP API
  schemas.py                 validated request contracts
  db.py                      PostgreSQL models (SQLite for fast unit tests)
  migrate.py                 initial additive schema creation
  storage.py                 private S3-compatible object access
  adapters.py                Hermes and GPU interfaces, simulated implementations
  worker.py                  outbox dispatch, Redis consumption, render lifecycle
services/api/tests/          backend behavior and isolation tests
scripts/smoke.py             real-service integration test
docs/ARCHITECTURE.md         data flow, boundaries and cloud deployment contract
docs/HERMES.md               orchestrator + 12 specialist responsibilities
docs/DEVELOPMENT.md          Claude Code / Codex workflow and local commands
docs/VERIFICATION.md         observed results and unverified components
.github/workflows/ci.yml     backend, dashboard and Compose smoke checks
compose.yaml                PostgreSQL, Redis, MinIO, API, worker, dashboard
```

Read `docs/DEVELOPMENT.md` before asking coding agents to change the project. This is a local development foundation; customer launch requirements are listed in the architecture document.

Implementation references: [Next.js installation](https://nextjs.org/docs/app/getting-started/installation), [FastAPI password and session security building blocks](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/). The session design here adds database-backed revocation to a signed cookie.
