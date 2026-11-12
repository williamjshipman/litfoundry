# Design: M1 platform foundation

## Context

This is a greenfield repository: it holds only `LICENSE`, `README.md`, the v1.3 specification under `specs/` and the OpenSpec scaffolding. The stack is fixed by v1.3 §2 and by `openspec/config.yaml`. See proposal.md for scope.

## Goals / Non-Goals

**Goals:**
- An installable `litfoundry` package that later milestones extend, with the source under `src/litfoundry/`.
- A catalogue database and migration baseline that later changes add tables to.
- Secret storage that later changes use for source keys and the AD service-account password.

**Non-Goals:**
- Accounts, sign-in, sessions and CSRF (`m1-local-identity`).
- Error envelope, CSP and SPA shell (`m1-web-foundation`).
- Project databases and migrations of project databases (`m2-project-workspaces`).
- Accepting archives from the earlier `brm` naming scheme. v1.3 §0.1 states there is no such requirement.

## Decisions

### Application structure
- **Flask application factory:** `litfoundry.app:create_app(config)`, with one Blueprint per API area under `litfoundry.api`.
- **CLI:** `litfoundry.cli:main` is the `[project.scripts]` entry point, built with Click, which Flask already depends on.
- **Configuration:** read in `litfoundry.config` from `LITFOUNDRY_*` environment variables, with an optional `.env` file in development only. `.env.example` lists every variable and contains no secrets.
- **Alternative rejected:** pydantic-settings. A plain typed dataclass keeps the dependency list short and avoids GPL-compatibility review of extra packages.

### Serving
- **WSGI server:** `litfoundry serve` runs Waitress bound to `127.0.0.1:<port>`. It reads `LITFOUNDRY_RUN_MODE` (`server|workstation`) and refuses non-loopback binds.
- **Proxy handling:** Werkzeug `ProxyFix` is applied only for the addresses in `LITFOUNDRY_TRUSTED_PROXIES`. Requests from other peers pass through unmodified.
- **Host allowlist:** `LITFOUNDRY_ALLOWED_HOSTS` is checked in a `before_request` hook that runs before any routing.
- **Reverse proxy:** `packaging/caddy/Caddyfile.example` uses `litfoundry.example.internal`, `reverse_proxy 127.0.0.1:5080`, and comments explaining how to use an organisation certificate instead of `tls internal`.

### Catalogue database
- **Engine settings:** SQLAlchemy 2.x engine on `catalog.sqlite`. Each connection runs `PRAGMA journal_mode=WAL`, `foreign_keys=ON` and `busy_timeout=5000`.
- **Migrations:** managed by Flask-Alembic under `migrations/catalog/`. This change creates the baseline revision, holding only `system_settings` and `schema_meta`; later changes add their own tables in new revisions.

### Secrets
- **Master key:** a random 256-bit key at `secret_material/master.key`.
- **Encryption:** secrets are encrypted with AES-256-GCM through `cryptography` (Apache-2.0/BSD). Each ciphertext carries a key ID so the key can be rotated later.
- **Signing key:** a random 512-bit key at `secret_material/session_signing.key`.
- **Alternatives rejected:** OS keychains and DPAPI. They would break restoring a backup on another machine (v1.3 §16.3 step 5).

### Data root permissions
- **Windows:** `init` applies an explicit DACL with inheritance disabled, granting full control to SYSTEM, Administrators and the configured service account. It uses `pywin32` (PSF licence, GPL-compatible), with an `icacls` fallback.
- **POSIX:** `os.chmod(0o700)`, with ownership set to the service user when `init` runs as root.

### Network filesystem detection
- **Windows:** reject UNC paths, and drive letters whose `GetDriveTypeW` result is `DRIVE_REMOTE`.
- **Linux:** reject `nfs`, `cifs`, `smb3` and `fuse.sshfs` mounts listed in `/proc/self/mountinfo`.
- **macOS:** reject `smbfs`, `nfs` and `afpfs`, using `statfs`.
- **Decision recorded:** v1.3 says live SQLite files must never sit on network shares but does not say how to enforce this. This design enforces it at `init` and `serve`.

### Logging
- **Format:** standard-library `logging` with a JSON formatter.
- **Destination:** `RotatingFileHandler` under `logs/`, with a total cap of 10 files × 10 MB by default.
- **Redaction:** a redaction filter scrubs known secret keys and token patterns before formatting.
- **Admin log view:** served by a new admin-only endpoint, `GET /api/v1/admin/logs`, which is not in the v1.3 §14 table. v1.3 §0 requires every admin feature to be reachable through REST, so the endpoint is added and recorded in `docs/decisions.md`.

## Risks / Trade-offs

- [Network filesystem detection misses exotic mounts] → Document the rule. Detection is a safety net, not a guarantee.
- [Windows ACL code differs per Windows edition] → Run the ACL test on the Windows CI runner. `litfoundry status` reports a data root whose ACL inherits.
- [Waitress plus a `ProxyFix` misconfiguration could trust spoofed headers] → Make an empty trusted-proxy list the default, and test that spoofed headers are ignored.

## Migration Plan

Not applicable: no earlier installation exists.
