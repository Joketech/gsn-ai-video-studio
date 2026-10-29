# Verification record — 30 October 2026

## Passed on this machine

| Check | Observed result | Scope |
|---|---|---|
| Backend behavior suite | **12 passed**, one dependency deprecation warning, 3.12 seconds | Python 3.12, SQLite isolated per test, in-memory storage replacement |
| Dashboard production build | Passed | Next.js 16.4.3, TypeScript compilation, static page generation |
| Separate TypeScript check | Passed | `npm run typecheck` |
| npm dependency audit during installation | Zero reported vulnerabilities | Point-in-time npm report, not a complete security review |
| Compose configuration | Passed | `docker compose --env-file .env.example config --quiet`; syntax and interpolation only |

Backend results are also saved in `backend-test-results.xml`. Tests cover login/logout and server-side session revocation, bad passwords and tampered sessions, rejected browser origins, cross-tenant object references and downloads, consent scope/commercial restrictions, consent revocation before execution, expiry validation, file/media limits, duplicate render submissions, conflicting request keys, job output and audit history, worker storage errors, lease recovery and duplicate delivery, all 13 mock roles, and refusal of unconfigured live adapters.

`requirements.lock` captures the exact Python distributions installed for this run. Docker and CI use it. `apps/web/package-lock.json` captures the dashboard dependency resolution. Python top-level dependency intentions remain in `requirements.txt`. The locked Linux container installation has not been executed here.

## Not verified

- **Full Docker stack:** Docker Desktop engine pipe access returned permission denied. No containers were launched. PostgreSQL, Redis and MinIO networking, image pulls and container startup are not represented as tested. A registry manifest lookup also returned an authentication/access error; pinned MinIO image availability must be confirmed by the first successful Compose run.
- **PostgreSQL behavior:** unit tests used SQLite here. The CI backend job is configured to rerun against disposable PostgreSQL, but that CI job has not run. Concurrent PostgreSQL row locking has not been load-tested.
- **Browser interaction and appearance:** the production build succeeded, but a Playwright-driven Edge launch was denied by Windows and closed before opening the page. Registration/project/scene browser interactions and responsive visual layout were not validated. No screenshot is represented as an inspected preview.
- **Live local HTTP preview:** background server launch attempts did not remain available between tool calls. No running dashboard is promised by this handover.
- **Real S3 / Redis end-to-end path:** unit tests replace storage and simulate queue notifications. `scripts/smoke.py` and the Compose CI job are provided to test actual services; neither has passed against a running stack here.
- **Hermes:** only the Python adapter interface and mock behavior were tested. No installed Hermes instance, CLI or API was called.
- **Cloud GPU, video generation, identity consistency, voice cloning and lip sync:** not implemented or tested. The live worker class fails explicitly; it cannot silently produce a mock result in live mode.
- **Remote CI:** workflow files are present, but no remote repository was created, no workflow was triggered and no green remote CI result is claimed.

## Next acceptance check for Joke

Start Docker Desktop with a user account allowed to access its engine. Follow README steps 1–4, then run `python scripts/smoke.py`. Record the result here. Next inspect the dashboard in a browser at desktop and phone widths, then use two separately registered workspaces to confirm that each sees only its own records. Keep simulation modes enabled until each live adapter has a recorded, explicit acceptance test.
