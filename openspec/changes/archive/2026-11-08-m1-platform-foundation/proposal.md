# Proposal: M1 platform foundation

## Why

LitFoundry has a specification (v1.3) but no code. Every later milestone needs the same base, so it comes first:
- a correctly branded, installable `litfoundry` package;
- a protected data root with a central catalogue;
- portable secret storage;
- a server that is only reachable on the LAN through HTTPS (or locally in workstation mode);
- basic health reporting and safe operational logs.

## What Changes

- Establish the LitFoundry naming contract: product name, tagline, description, the `litfoundry` package and CLI, the `LITFOUNDRY_` configuration prefix, and the About screen with the administrator trust disclosure.
- Add `litfoundry init`. It creates the data root layout, the central `catalog.sqlite` and `secret_material/`, and sets restrictive operating-system permissions.
- Add portable, encrypted-at-rest secret storage: a master key file and a session signing key. Secrets are write-only through every interface.
- Add `litfoundry serve`, which has two modes:
  - **server mode:** Waitress on loopback behind a Caddy TLS reverse proxy, with trusted proxies and a host allowlist;
  - **workstation mode:** loopback only, for a single user on one machine.
- Add `/api/v1/health/live`, `/api/v1/health/ready` and `litfoundry status`.
- Add structured, redacted operational logs under `<data_root>/logs/`.

## Capabilities

### New Capabilities

- `platform/product-identity`: product name, tagline, machine identifiers, configuration prefix and the About screen.
- `platform/data-root`: data root location, layout, initialisation, permissions and path containment.
- `platform/secret-storage`: master key, session signing key, encryption at rest and write-only secret handling.
- `platform/server-deployment`: server and workstation modes, the TLS reverse proxy, trusted proxies, the host allowlist, cross-origin policy and offline operation.
- `platform/system-status`: liveness and readiness endpoints, the `litfoundry status` command and the admin system screen.
- `platform/operational-logging`: structured logs, correlation IDs, redaction and admin log viewing.

### Modified Capabilities

None.

## Impact

- **v1.3 sections implemented:** §0.1, §1 decisions 1 and 9, §2 (stack and licensing baseline), §3, §4 (data root layout), §17 (TLS, proxy, secrets, logging, permissions bullets), §18 (development setup), §18.1 (`init`, `serve`, `status`), §19 groups 13–14 (partially) and the §20 M1 platform items.
- **Depends on:** nothing. This is the first change.
- **Code:** `pyproject.toml`, `src/litfoundry/` (`app.py`, `config.py`, `cli.py`, `catalog/`), `migrations/catalog/`, `packaging/caddy/`, `docs/` (configuration reference, deployment notes, `decisions.md`), `.env.example`.
- **Dependencies introduced:** Flask, Waitress, SQLAlchemy 2, Flask-Alembic, `cryptography` (Apache-2.0/BSD, GPLv3-compatible).
- **Out of scope:**
  - authentication and sessions (`m1-local-identity`);
  - the API error contract, the CSP and the SPA shell (`m1-web-foundation`);
  - projects (`m2-*`);
  - packaged installers and OS services (`m7-windows-distribution`).
