# GitHub Copilot Instructions for LitFoundry

This file helps GitHub Copilot understand the LitFoundry codebase structure, architecture, and conventions.

## Project Overview

**LitFoundry** is an open-source application for systematic literature reviews, PRISMA workflows, and bibliometric analysis. It's a Python/Flask backend with a Vue 3 SPA frontend, deployed as a LAN-hosted multi-user server. The project uses OpenSpec for change management and incremental development.

**Source of truth:** OpenSpec artifacts in `openspec/` are authoritative. When `openspec/changes/` or `openspec/specs/` differ from other documentation, OpenSpec wins.

## Stack (Fixed by v1.3, Non-Substitutable)

- **Backend:** Python 3.12+, Flask (application factory + Blueprints), SQLAlchemy 2.x, SQLite (WAL, foreign keys, busy timeout)
- **Server:** Waitress on `127.0.0.1:5080` behind Caddy TLS reverse proxy
- **Database:** Central `catalog.sqlite` + one `project.sqlite` per project (Flask-Alembic for catalogue, Alembic programmatic API for projects)
- **Security:** Flask-JWT-Extended cookies (double-submit CSRF), Argon2id, `ldap3` for optional Active Directory
- **Frontend:** Vue 3 runtime-only ESM build (no SFC, no Node server, no in-browser compiler), Axios, Apache ECharts, Tailwind (compiled to static CSS)
- **Tests:** pytest, pytest-flask/httpx, Playwright
- **Packaging:** PyInstaller one-folder on target OS; Windows in v1, Linux/macOS as SHOULD items

## Building and Testing

### Setup

The project is a Python package under `src/litfoundry/`. There is no `package.json` or Node build step for development; Tailwind is compiled via a pinned standalone CLI into static CSS.

**To initialize a development environment:**
```bash
python -m venv venv
source venv/bin/activate  # or on Windows: venv\Scripts\activate
pip install -e ".[dev]"   # Install from pyproject.toml in editable mode
```

### Running Tests

```bash
# Full pytest suite (all Python tests)
pytest

# Single test file
pytest tests/test_auth.py

# Single test function
pytest tests/test_auth.py::test_login_success

# With coverage
pytest --cov=litfoundry

# Playwright tests only
pytest tests/e2e/

# Watch mode (if available)
pytest-watch
```

### Linting and Type Checking

```bash
# Lint with ruff (if configured)
ruff check src/ tests/

# Type checking with mypy (if configured)
mypy src/litfoundry/

# Format with black (if configured)
black src/ tests/
```

### Running the Application

```bash
# Start the server
litfoundry serve

# This binds to 127.0.0.1:5080 and outputs the endpoint.
# In development, use Caddy or access via http://127.0.0.1:5080 directly.
```

### Database Migrations

```bash
# Catalogue migrations (Flask-Alembic)
flask db upgrade

# Project migrations are handled programmatically per project during lifecycle operations.
```

## Architecture

### Entry Point and Application Factory

- **Module:** `litfoundry.app:create_app(config)`
- **Pattern:** Standard Flask application factory. Configuration loads from `LITFOUNDRY_*` environment variables or `.env` (dev only).
- **Blueprints:** One per API area under `litfoundry.api.*`

### Data Layout

**Catalogue database** (`catalog.sqlite`): Global state
- `system_settings` – configuration, backup schedules
- `audit_events` – admin changes (audited for every admin action and every admin project access)
- User accounts, sessions, AD configuration, project discovery, ACLs

**Project databases** (`project.sqlite` per project folder): Project state
- Records, screening decisions, analyses, corpus snapshots
- Each project has its own isolated database

### Request Flow

1. **Reverse proxy (Caddy):** Accepts HTTPS on LAN, forwards to loopback
2. **Flask middleware:** `ProxyFix` (trusted proxies only), host allowlist, CORS (dev only)
3. **Blueprint routes:** REST API under `/api/v1/*`
4. **Permission checks:** Checked on every API call and background job
5. **Response:** JSON envelope with error handling, audit logging for sensitive ops

### Secrets and Configuration

- **Master key:** `secret_material/master.key` (256-bit, random)
- **Session signing key:** `secret_material/session_signing.key` (512-bit)
- **Encryption:** AES-256-GCM via `cryptography`; key rotation supported via key ID in ciphertext
- **Secrets stored:** Source API keys, AD service account password, etc.
- **Logging:** JSON formatter with redaction filter (scrubs tokens, known secret patterns)

### Frontend Architecture

**Key constraints:**
- Runtime-only Vue 3 build (no template compiler) → CSP `script-src 'self'`, no `'unsafe-eval'`
- All render functions use `h()` (no `<template>` strings, no in-DOM templates)
- No Vue SFC (.vue files) – use plain ES modules
- No Vite or Node application server in production
- Vendor files (Vue, Axios, ECharts) stored locally in `frontend/vendor/` with checksums
- Tailwind compiled to static CSS via standalone CLI (no JIT)
- Client-side routing via in-house History API module (not vue-router's ESM build)

**File layout:**
```
frontend/
  vendor/          # checksum-verified, local copies of Vue, Axios, ECharts
  css/             # tailwind.css (compiled, not source)
  js/              # application modules, routers, components
  index.html       # entry point
```

### Naming Conventions

- **Product:** LitFoundry (exact capitalization)
- **Machine ID:** `litfoundry` (lowercase, everywhere: package, CLI, service, env prefix `LITFOUNDRY_`)
- **Database files:** `catalog.sqlite`, `project.sqlite` (never `brm` or `pybrm`)
- **Admin account:** username is literally `admin` (reserved, not renamed)
- **Archive names:** `litfoundry_project_<uuid>_<timestamp>.zip`, `litfoundry_full_<timestamp>_<run_uuid>.zip`
- **Endpoints:** `/api/v1/*` (versioned)

## OpenSpec Workflow

This project uses OpenSpec for all feature work. **Do not commit code directly to main.**

### Typical Flow

1. **Explore:** Use `openspec explore` or the `openspec-explore` agent skill to think through requirements
2. **Propose:** Use `openspec propose` to generate a change with proposal, specs, design, and tasks
3. **Review:** Human review of the change artifacts (design.md, specs, tasks)
4. **Implement:** Use `openspec apply-change` agent skill to implement tasks
5. **Archive:** Once complete and tested, use `openspec archive-change` to merge into main specs and move code to main branch

### Change Structure

Each change in `openspec/changes/<name>/` contains:
- `.openspec.yaml` – metadata (dependencies, etc.)
- `proposal.md` – scope and rationale
- `specs/` – artifact specs (once archived, these merge to `openspec/specs/`)
- `design.md` – detailed design decisions, migration plan, risks
- `tasks.md` – implementation tasks
- `README.md` – short summary

### Key Principles

- **Source of truth:** OpenSpec. v1.3 spec is historical reference only.
- **Traceability:** Changes cite v1.3 section numbers for traceability.
- **Dependencies:** Changes form a DAG; some can be parallelized (e.g., source adapters, AD) once dependencies archive
- **Within a change:** `specs/` wins over `design.md`, `design.md` wins over `tasks.md`
- **Conflicts:** Stop and raise, don't guess

### OpenSpec Configuration

The project-wide context is in `openspec/config.yaml`. Every agent apply or archive run receives this context, which:
- Defines the fixed stack (Python 3.12+, Flask, Vue 3 runtime-only, etc.)
- Lists binding constraints from v1.3 that code cannot infer
- States that OpenSpec wins over v1.3 where they differ
- Explains the trust model (admin fully trusted, users are told this)
- References licensing requirements (GPL-3.0-compatible only)

**Do not commit code that violates config.yaml context.**

## Common Tasks and Patterns

### Adding a Database Table

1. Find the change that owns the feature (e.g., `m3-source-credentials` owns the credentials table)
2. In that change's design.md, note the migration step in "Migration Plan"
3. Create a new Alembic revision under `migrations/catalog/versions/` or use programmatic Alembic for project databases
4. Write the migration in the change's tasks
5. Add tests to verify the schema and constraints

### Adding an API Endpoint

1. Create a Blueprint under `litfoundry/api/<area>.py` if it doesn't exist
2. Define the route with proper permission checks: call the ACL function and raise `Forbidden` if denied
3. Return JSON responses with consistent error envelope (defined in `m1-web-foundation`)
4. Document the route in the change's specs (it's a publicly versioned contract)
5. Add pytest and Playwright tests

### Adding a Background Job

- Use the job coordinator in `m2-background-jobs`
- All background work must check permissions before running
- Use the audit log for sensitive operations
- Write coordinator tests and integration tests

### Vue Component Pattern

```javascript
import { h } from 'vue';

export default {
  setup(props) {
    return () => h('div', { class: 'container' }, [
      h('h1', 'My Component'),
      // more render functions
    ]);
  }
};
```

Never use `<template>` or SFC syntax.

### Environment Variables

All configuration via `LITFOUNDRY_*` prefix:
- `LITFOUNDRY_DATA_ROOT` – data directory (defaults: Windows `%PROGRAMDATA%\LitFoundry`, Linux `/var/lib/litfoundry`, macOS `/Library/Application Support/LitFoundry`)
- `LITFOUNDRY_RUN_MODE` – `server` or `workstation`
- `LITFOUNDRY_ALLOWED_HOSTS` – comma-separated allowlist
- `LITFOUNDRY_TRUSTED_PROXIES` – comma-separated trusted proxy IPs for `ProxyFix`
- `.env` file is read in development only

## Testing Strategy

### Unit Tests

- Use `pytest` fixtures for database setup
- Mock external APIs (OpenAlex, WoS, AD)
- Test permission checks in isolation

### Integration Tests

- Use `pytest-flask` for app context and client fixture
- Test full request/response cycles
- Verify database state changes
- Test with actual migrations applied

### End-to-End Tests

- Use Playwright (`pytest-playwright`) for browser automation
- Test user flows (login, search, screening, export)
- Run against a live application instance

### Permission Tests

- Every endpoint must have tests verifying that users without permission are denied
- Admin actions must be tested and must appear in audit logs

## Licensing and Compliance

- LitFoundry is **GPL-3.0** (see `LICENSE`)
- All bundled dependencies must be GPL-3.0-compatible (MIT, BSD, Apache-2.0, LGPL-3.0, GPL-3.0)
- Never bundle GPL-2.0-only, proprietary, or non-commercial-use-restricted code
- Distributed packages must include licence texts and offer source for copyleft components
- `pywin32` (used for Windows ACLs) is PSF, GPL-compatible
- `ldap3` is LGPL-3.0, GPL-compatible

## Key Constraints

- **No mandatory LLM service dependency** – AI features must be optional
- **Manual file-import path for every source** – never assume access to paid APIs
- **All features in GUI and REST API** – except host-only ops (bootstrap token, admin password recovery, migration, full restore), which are CLI-only
- **Network filesystem rejection** – `init` and `serve` reject live SQLite files on UNC/NFS/CIFS/SMB/SSHFS
- **Windows x86_64 only for packaged v1** – Linux and macOS packaging are post-v1
- **Fixed stack, no substitutions** – Python 3.12+, Flask, Vue 3 runtime-only, Waitress, etc. are binding

## Where to Find Things

- **Specification and design:** `specs/litfoundry_codex_spec_v1_3.md` (historical), `openspec/` (source of truth)
- **Source code:** `src/litfoundry/`
- **Migrations:** `migrations/catalog/` (catalogue), project migrations in each project folder
- **Tests:** `tests/`
- **Frontend:** `frontend/`
- **Packaging:** `packaging/`
- **CI/CD:** `.github/workflows/`
- **OpenSpec changes:** `openspec/changes/`

## Before Starting Work

1. Read the relevant OpenSpec change (e.g., if working on authentication, read `m1-local-identity/design.md`)
2. Check `.openspec/config.yaml` context – it contains binding constraints
3. If working on an existing change, open that change's directory in your editor; changes are self-contained
4. Run the full test suite to ensure nothing is broken
5. Use `openspec apply-change` agent skill, not manual edits, for planned work

## Recommended MCP Server Integrations

For enhanced Copilot context, configure these MCP servers in your GitHub Copilot settings:

- **GitHub MCP:** Access PR context, issue discussions, and commit history. Useful for OpenSpec change reviews and understanding related work.
- **Database Tools MCP:** Query SQLite schema for `catalog.sqlite` and `project.sqlite`. Useful when working on migrations or understanding data models.

These are optional and configured outside the repository.

## Questions or Ambiguities?

If a design decision isn't clear or artifacts conflict:
- Check `openspec/config.yaml` context first
- Check the change's `design.md` section "Decisions"
- Look at v1.3 spec sections cited in the change's proposal.md
- Refer to `specs/litfoundry_v1_3_openspec_map.md` for section traceability
- Raise the conflict rather than guessing; OpenSpec workflows expect human review
