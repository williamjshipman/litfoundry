# Decisions: M1 platform foundation

This document records architectural and design decisions made during the M1 platform foundation change.

## Application Structure

### Flask Application Factory
- **Decision:** Use a Flask application factory pattern with one Blueprint per API area under `litfoundry.api`.
- **Rationale:** Standard Flask pattern enabling test isolation, flexible configuration, and multi-environment deployments.
- **Implementation:** `litfoundry.app:create_app(config)`.

### CLI Framework
- **Decision:** Use Click for the CLI, built into Flask dependencies.
- **Rationale:** Lightweight, dependency-efficient, and already required by Flask.
- **Implementation:** `litfoundry.cli:main` as the `[project.scripts]` entry point.

### Configuration Loader
- **Decision:** Read configuration from `LITFOUNDRY_*` prefixed environment variables, with an optional `.env` file in development only.
- **Rationale:** Simple, transparent configuration with platform-appropriate defaults (no dependency on pydantic-settings).
- **Implementation:** `litfoundry.config:Config.load_from_env()`.
- **Rejected Alternative:** pydantic-settings to keep dependencies short and avoid GPL-compatibility review.

## Serving and Deployment

### WSGI Server
- **Decision:** Use Waitress bound to loopback (`127.0.0.1:<port>`), with support for `server` and `workstation` modes via `LITFOUNDRY_RUN_MODE`.
- **Rationale:** Pure Python WSGI server with no C extensions, portable, and prohibits non-loopback binds by design.
- **Implementation:** `litfoundry serve` command.

### Proxy Handling
- **Decision:** Apply Werkzeug `ProxyFix` only for IPs listed in `LITFOUNDRY_TRUSTED_PROXIES` (empty by default).
- **Rationale:** Prevents spoofed headers from untrusted sources; safe default with explicit allowlist.

### Host Allowlist
- **Decision:** Enforce `LITFOUNDRY_ALLOWED_HOSTS` check in a `before_request` hook.
- **Rationale:** Prevents host header injection attacks.

### Reverse Proxy
- **Decision:** Provide `packaging/caddy/Caddyfile.example` for LAN deployment via Caddy with `tls internal` or organization certificates.
- **Rationale:** Caddy is lightweight and manages TLS termination automatically; the example shows best practices.

## Catalogue Database

### Engine Settings
- **Decision:** SQLAlchemy 2.x engine with WAL mode, foreign keys enabled, and a 5-second busy timeout per connection.
- **Rationale:** WAL improves concurrency; foreign keys enforce referential integrity; busy timeout handles contention gracefully.
- **Implementation:** Engine config applied to all connections via `SQLAlchemy` event handlers.

### Migrations
- **Decision:** Use Flask-Alembic under `migrations/catalog/` for catalogue migrations; Alembic programmatic API for per-project databases.
- **Rationale:** Flask-Alembic integrates with the Flask lifecycle; programmatic Alembic allows flexible per-project schema versioning.
- **Baseline:** This change creates the baseline revision holding only `system_settings` and `schema_meta` tables.

## Secrets

### Master Key
- **Decision:** Store a random 256-bit key at `secret_material/master.key`.
- **Rationale:** Single, trusted root for deriving all encrypted secrets; fixed location simplifies deployment and backup procedures.

### Encryption Scheme
- **Decision:** Use AES-256-GCM via the `cryptography` library (Apache-2.0/BSD, GPL-compatible). Each ciphertext carries a key ID for rotation.
- **Rationale:** Authenticated encryption is industry-standard; key ID enables seamless key rotation without decryption failures.

### Signing Key
- **Decision:** Store a random 512-bit key at `secret_material/session_signing.key`.
- **Rationale:** Dedicated key for session signing via Flask-JWT-Extended; separate from encryption key reduces risk of misuse.

### Rejected Alternatives
- **OS Keychains (Windows, macOS, Linux):** Break restoring a backup to another machine (v1.3 §16.3 step 5).
- **DPAPI (Windows):** Same issue; not portable.

## Data Root Permissions

### Windows
- **Decision:** Apply an explicit DACL with inheritance disabled, granting full control to SYSTEM, Administrators, and the configured service account. Fall back to `icacls` if `pywin32` is unavailable.
- **Rationale:** Prevents accidental exposure; explicit ACLs are easier to audit than inherited permissions.

### POSIX
- **Decision:** Apply `os.chmod(0o700)`, with ownership set to the service user when `init` runs as root.
- **Rationale:** Standard restrictive permissions; `0o700` prevents any access by other users.

## Network Filesystem Detection

### Policy
- **Decision:** Refuse UNC and network-filesystem data roots in `init` and `serve`. v1.3 §4 and §17 forbid live SQLite files on network shares.
- **Rationale:** SQLite over network filesystems is unsafe; early detection prevents subtle data corruption.

### Detection Mechanism
- **Windows:** Reject UNC paths and drive letters whose `GetDriveTypeW` result is `DRIVE_REMOTE`.
- **Linux:** Reject `nfs`, `cifs`, `smb3` and `fuse.sshfs` mounts listed in `/proc/self/mountinfo`.
- **macOS:** Reject `smbfs`, `nfs` and `afpfs` via `statfs`.

### Risk Mitigation
- Detection is a safety net, not a guarantee. Document the rule and the limitations.

## Logging

### Format and Destination
- **Decision:** Standard-library `logging` with a JSON formatter, writing to `RotatingFileHandler` under `<data_root>/logs/`.
- **Rationale:** JSON is machine-readable and integrates well with log aggregation; rotating files cap disk usage.
- **Configuration:** 10 files × 10 MB by default.

### Redaction
- **Decision:** A redaction filter scrubs known secret keys and token patterns before formatting.
- **Rationale:** Prevents accidental leaks of credentials into logs.

### Admin Log View
- **Decision:** Serve logs via the admin-only `GET /api/v1/admin/logs` endpoint (not in v1.3 §14). Implement filtering by level, timestamp range, and keyword.
- **Rationale:** v1.3 §0 requires every admin feature to be reachable through REST. This endpoint is recorded in decisions.md as a new admin capability.

## Process Names
- `litfoundry-server`: Main server process.
- `litfoundry-worker`: Background job worker (for future work).
- **Rationale:** Consistent naming enables process monitors and CI/CD scripts to identify LitFoundry processes.

## Path Containment
- **Decision:** Implement a path-containment helper rejecting `..` (parent directory escapes), absolute user paths and following symlinks.
- **Rationale:** Prevents directory traversal attacks and ensures all project/snapshot data is under the declared data root.
- **UUID-Only Naming:** All project and snapshot folders use UUIDs only; human names are stored in metadata.

## References

- **v1.3 Sections Implemented:**
  - §0.1: Naming contract (LitFoundry, litfoundry machine ID).
  - §1 decisions 1 and 9: Stack and architectural decisions.
  - §2: Stack and licensing baseline.
  - §3: Configuration and `.env` example.
  - §4: Data root layout, initialization, permissions and path containment.
  - §17: TLS, proxy, secrets, logging, permissions.
  - §18: Development setup (`init`, `serve`, `status`).
  - §18.1: CLI commands and usage.
  - §19 groups 13–14: Partially (API structure, health endpoints).
  - §20: M1 platform items (configuration, database, server startup).

- **Design Document:** `openspec/changes/m1-platform-foundation/design.md`
- **Proposal:** `openspec/changes/m1-platform-foundation/proposal.md`
