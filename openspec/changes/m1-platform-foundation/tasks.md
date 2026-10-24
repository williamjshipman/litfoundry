# Tasks: M1 platform foundation

## 1. Project scaffolding

- [x] 1.1 Create `pyproject.toml` with distribution `litfoundry`, the `src/litfoundry/` layout, `[project.scripts] litfoundry = "litfoundry.cli:main"` and `[dev]` extras. Verify that `pip install -e .[dev]` succeeds in a clean venv and that `litfoundry --version` prints the version.
- [x] 1.2 Add a checked-in lockfile or constraints file and a CI workflow running lint, type check and pytest on Windows, Linux and macOS. Verify the workflow passes on all three runners.
- [x] 1.3 Add `docs/decisions.md` and record the decisions from this change's design.md. Verify the file lists each decision.

## 2. Product identity

- [x] 2.1 Add product constants (name, tagline, description, version) and the `litfoundry-server` and `litfoundry-worker` process names. Verify with a unit test.
- [x] 2.2 Add a naming test that scans the source tree, packaging and entry points for `brm`, `pybrm`, `bibliometric-research-manager` and `appctl`. Verify that it fails on a seeded violation.

## 3. Configuration and data root

- [x] 3.1 Implement the `LITFOUNDRY_*` configuration loader with platform defaults and `.env.example`. Verify with unit tests for each OS default, for overrides, and for unprefixed variables being ignored.
- [x] 3.2 Implement `litfoundry init`: data root layout, catalogue at the latest revision, and idempotent re-runs. Verify with integration tests for a fresh and a repeated init.
- [x] 3.3 Apply restrictive permissions: a Windows DACL with inheritance disabled, and POSIX `0700`. Verify with OS-specific tests on each CI runner.
- [x] 3.4 Refuse UNC and network-filesystem data roots in `init` and `serve`. Verify with unit tests using mocked drive types and mount tables.
- [x] 3.5 Implement the path-containment helper (rejecting `..`, absolute user paths and escaping symlinks) and UUID-only naming. Verify with unit tests, including a symlink fixture.
- [x] 3.6 Write the configuration reference in `docs/` for Windows, Linux and macOS. Verify that every variable in `.env.example` is documented.

## 4. Catalogue and secret storage

- [x] 4.1 Create the catalogue engine (WAL, foreign keys, busy timeout) and the Flask-Alembic baseline revision. Verify that `PRAGMA journal_mode` returns `wal` in a test.
- [x] 4.2 Implement the master key and session signing key files, AES-GCM encrypt/decrypt with key IDs, and signing-key rotation. Verify with unit tests, including decrypting on a copied data root.
- [ ] 4.3 Implement the write-only secret field helper (reports configured or not, never the value; an omitted field keeps the stored secret), for reuse by the AD and credential endpoints. Verify with unit tests.
- [ ] 4.4 Add a secret-leak test helper that scans logs, the catalogue, job records and generated files for known test secrets. Verify that it fails on a seeded leak. It is reused by later changes.

## 5. Serving and deployment

- [ ] 5.1 Implement `litfoundry serve` with Waitress on loopback, an explicit run mode, refusal of non-loopback binds and of debug mode. Verify with CLI tests.
- [ ] 5.2 Add trusted-proxy handling and the host allowlist. Verify with tests that spoofed `X-Forwarded-For` is ignored and that an unknown `Host` returns 400.
- [ ] 5.3 Add same-origin CORS defaults, with an origin allowlist only through configuration. Verify with a preflight test.
- [ ] 5.4 Add `packaging/caddy/Caddyfile.example` and deployment documentation covering the proxy, CA trust per OS and browser, and the firewall. Verify the docs build and that the Caddyfile validates with `caddy validate` in CI where Caddy is available.

## 6. Status and logging

- [ ] 6.1 Implement `GET /api/v1/health/live` and the admin-only `GET /api/v1/health/ready`. Verify with API tests; the admin check is stubbed until `m1-local-identity` lands, then re-verified.
- [ ] 6.2 Implement `litfoundry status`, which exits non-zero on a failed check. Verify with a CLI test against a healthy and a broken data root.
- [ ] 6.3 Implement structured JSON logging with rotation, process names and redaction. Verify with a unit test that a logged password or token is redacted.
- [ ] 6.4 Implement `GET /api/v1/admin/logs` with filters. Verify the admin-only access test once identity lands.
- [ ] 6.5 Add an offline-operation test: with outbound network blocked, the server starts, serves existing data and reports a retryable error for an outbound call. Verify that it passes.

GUI screens for this change's requirements (branding, About, Admin → System and the log view) are built in `m1-local-identity` group 6, because the SPA shell and sign-in arrive there. Archive the three `m1-*` changes together.
