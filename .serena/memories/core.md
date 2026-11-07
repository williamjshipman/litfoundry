# Core Project Map

**LitFoundry** — Open-source systematic literature reviews, PRISMA workflows, and bibliometric analysis. Python/Flask backend (SQLite) + Vue 3 runtime-only frontend.

## Key Invariants

- Source of truth: OpenSpec artifacts (not v1.3 spec). Within a change: `specs/` > `design.md` > `tasks.md`.
- **Mandated non-substitutable stack:** Python 3.12+; Flask (app factory + Blueprints); Waitress on `127.0.0.1:5080`; SQLAlchemy 2.x + SQLite (WAL, FK, busy timeout); Flask-Alembic (catalogue) + Alembic programmatic (projects); Flask-JWT-Extended cookies (CSRF); Argon2id; ldap3 (AD); Vue 3 runtime-only ESM (`h()` render, no SFC/Vite/template compiler); Axios; Apache ECharts; Tailwind (static CSS from standalone CLI); pytest + Playwright.
- **License:** GPL-3.0 only; all deps GPL-compatible.
- **Naming:** product "LitFoundry"; CLI/package/service `litfoundry` (env prefix `LITFOUNDRY_`). Never `brm`, `pybrm`, `appctl`.
- **Platforms:** CI on Win/Linux/macOS; only Windows x86_64 for v1 packages.
- **Trust:** admin fully trusted; all users told this.

## Architecture

- **Entry:** `litfoundry.cli:main` (Click groups: `init`, `serve`, `status`) → `create_app()` (Flask factory)
- **DB:** Central `catalog.sqlite` + one `project.sqlite` per project (each in project folder)
- **API:** Blueprints under `litfoundry.api.*`, versioned routes `/api/v1/*`
- **Middleware:** ProxyFix (trusted IPs), host allowlist, CORS (dev only)
- **Config:** `LITFOUNDRY_*` env vars (no `.env` in prod)
- **Secrets:** `secret_material/master.key` (256-bit), `session_signing.key` (512-bit); AES-256-GCM; key ID in ciphertext for rotation
- **Logging:** JSON format + redaction filter (scrubs tokens, known secrets)

## Module Structure

- `src/litfoundry/` — main package
  - `cli.py` — Click CLI entry point
  - `app.py` — Flask application factory
  - `server.py`, `config.py`, `initialization.py`, `status.py` — bootstrap & config
  - `logging.py`, `middleware.py`, `secrets.py`, `filesystem.py` — infra
  - `api/` — Blueprints (`admin.py`, `health.py`, …)
  - `catalog/` — catalogue DB models & logic
  - `migrations/` — Alembic catalogue migrations
  - `test_helpers/` — pytest fixtures & utilities
- `tests/` — pytest + Playwright suite
- `migrations/catalog/` — Alembic versioned migrations
- `openspec/` — OpenSpec workflow (source of truth for features)
  - `config.yaml` — project context & constraints
  - `specs/` — main specs (archived from changes)
  - `changes/` — feature changes (m1-* to m7-* are v1 core)
- `frontend/` — Vue 3 SPA
  - `vendor/` — local checksum-verified Vue, Axios, ECharts
  - `css/` — static Tailwind output
  - `js/` — app modules & components (no SFC)
  - `index.html` — entry point
- `docs/`, `specs/`, `packaging/` — docs, historical spec, PyInstaller config

## Onboarding References

For detailed conventions, stack specifics, build/test commands, and task completion checks, see:
- `mem:tech_stack` — languages, frameworks, versions, package manager
- `mem:suggested_commands` — dev, test, lint, format, run commands (Windows paths)
- `mem:conventions` — code style, naming, docstrings, patterns
- `mem:task_completion` — exact test/lint/check commands for task sign-off