# LitFoundry Configuration Guide

This guide documents all configuration options for LitFoundry, their defaults, and platform-specific considerations.

## Configuration Methods

LitFoundry reads configuration from environment variables with the `LITFOUNDRY_` prefix. In development, you can also use a `.env` file in the working directory. In production, use your system's environment variable management (systemd, Docker, etc.).

See `.env.example` for a template.

## Configuration Variables

### LITFOUNDRY_DATA_ROOT

**Type:** Path (directory)
**Default:** Platform-specific:
  - **Windows:** `%PROGRAMDATA%\LitFoundry` (typically `C:\ProgramData\LitFoundry`)
  - **macOS:** `~/Library/Application Support/LitFoundry`
  - **Linux:** `/var/lib/litfoundry`

**Purpose:** Root directory where LitFoundry stores all persistent data, including the catalogue database, project databases, secret material, logs, and backup staging area.

**Constraints:**
- Must be on a local filesystem (not a network share, NFS, CIFS, etc.)
- Will be created by `litfoundry init` if it doesn't exist
- Must have restricted permissions (0700 on POSIX, explicit DACL on Windows)

**Example (Windows):**
```
LITFOUNDRY_DATA_ROOT=C:\Users\admin\LitFoundry
```

**Example (Linux):**
```
LITFOUNDRY_DATA_ROOT=/srv/litfoundry
```

### LITFOUNDRY_RUN_MODE

**Type:** String (choice)
**Default:** `server`
**Allowed values:** `server`, `workstation`

**Purpose:** Execution mode, which affects proxy handling and security assumptions.

- **`server`:** LitFoundry runs behind a reverse proxy (e.g., Caddy) and trusts `X-Forwarded-*` headers only from configured trusted proxies. Suitable for production behind a TLS-terminating proxy.
- **`workstation`:** LitFoundry runs locally without a proxy. No `X-Forwarded-*` headers are processed. Suitable for development or single-user deployments.

**Example:**
```
LITFOUNDRY_RUN_MODE=server
```

### LITFOUNDRY_PORT

**Type:** Integer
**Default:** `5080`

**Purpose:** TCP port on which the Waitress WSGI server listens.

**Constraints:**
- Must be > 1024 to avoid requiring root privileges
- LitFoundry always binds to `127.0.0.1` (loopback), never to `0.0.0.0` or other interfaces
- The reverse proxy (e.g., Caddy) listens on the public port and forwards to this port

**Example:**
```
LITFOUNDRY_PORT=5080
```

### LITFOUNDRY_TRUSTED_PROXIES

**Type:** Comma-separated list of IP addresses
**Default:** (empty; no proxies trusted)

**Purpose:** IP addresses of reverse proxies that are allowed to set `X-Forwarded-*` headers.

**Details:**
- Used only in `server` run mode
- Empty by default (strict security posture): only direct connections are trusted
- Requests from untrusted proxies will have spoofed headers rejected
- Example: `127.0.0.1,192.168.1.10`

**Security note:** In production, set this to the specific IP address of your reverse proxy, not a range or `*`. If not set, no proxy headers are trusted, even if they are present.

**Example (single local proxy):**
```
LITFOUNDRY_TRUSTED_PROXIES=127.0.0.1
```

**Example (production with Caddy on a network interface):**
```
LITFOUNDRY_TRUSTED_PROXIES=192.168.1.50
```

### LITFOUNDRY_ALLOWED_HOSTS

**Type:** Comma-separated list of hostnames/IPs
**Default:** `localhost,127.0.0.1`

**Purpose:** Host names and IP addresses that the application will accept in the `Host` request header.

**Details:**
- Requests with a `Host` header not in this list are rejected with HTTP 400 (Bad Request)
- Used to prevent host header injection attacks
- Should include the hostname used by clients and the reverse proxy

**Example (development):**
```
LITFOUNDRY_ALLOWED_HOSTS=localhost,127.0.0.1
```

**Example (production with external domain):**
```
LITFOUNDRY_ALLOWED_HOSTS=localhost,127.0.0.1,litfoundry.example.com,litfoundry.internal
```

### LITFOUNDRY_CORS_ORIGINS

**Type:** Comma-separated list of URLs
**Default:** (empty; same-origin only)

**Purpose:** Allowed origins for Cross-Origin Resource Sharing (CORS).

**Details:**
- Empty by default, which restricts CORS to same-origin requests only
- Can be set to allow specific external domains
- Each entry should be a full URL including scheme: `https://example.com`
- Does not apply to same-origin requests (always allowed)

**Security note:** Only set this if you have a specific reason to allow cross-origin requests (e.g., a separate frontend domain). Same-origin is the default and most secure.

**Example (single external domain):**
```
LITFOUNDRY_CORS_ORIGINS=https://app.example.com
```

**Example (development with multiple origins):**
```
LITFOUNDRY_CORS_ORIGINS=http://localhost:3000,http://localhost:8080
```

### LITFOUNDRY_CATALOG_PATH

**Type:** Path (file)
**Default:** `{LITFOUNDRY_DATA_ROOT}/catalog.sqlite`

**Purpose:** Custom path to the catalogue database file.

**Details:**
- Normally, you do not need to set this; the catalogue is stored in the data root
- Only use this if you have a specific reason to store the catalogue on a different filesystem
- The path must be on a local disk (not a network share)
- `litfoundry init` creates this file if it doesn't exist

**Example:**
```
LITFOUNDRY_CATALOG_PATH=/var/lib/litfoundry/catalog.sqlite
```

## Platform-Specific Setup

### Windows

**Default data root:** `%PROGRAMDATA%\LitFoundry`

Example paths:
- `C:\ProgramData\LitFoundry` (standard)
- `C:\Program Files\LitFoundry` (not recommended; many apps have issues here)

**Permissions:**
- `litfoundry init` applies an NTFS ACL with inheritance disabled
- Grants access to `SYSTEM`, `Administrators`, and the service account
- Use `litfoundry status` to check for ACL inheritance issues

**Example `.env` for Windows development:**
```
LITFOUNDRY_DATA_ROOT=C:\Users\%USERNAME%\AppData\Local\LitFoundry
LITFOUNDRY_RUN_MODE=workstation
LITFOUNDRY_PORT=5080
```

### macOS

**Default data root:** `~/Library/Application Support/LitFoundry`

Example:
- `/Users/alice/Library/Application Support/LitFoundry` (single-user)

**Permissions:**
- `litfoundry init` sets mode `0700` (rwx for owner only)
- Owned by the user running the command

**System-wide installation (not v1):** Post-v1 roadmap includes system-wide mode with data root at `/Library/Application Support/LitFoundry`.

**Example `.env` for macOS development:**
```
LITFOUNDRY_DATA_ROOT=/Volumes/DataDisk/LitFoundry
LITFOUNDRY_RUN_MODE=workstation
LITFOUNDRY_PORT=5080
```

### Linux

**Default data root:** `/var/lib/litfoundry`

Example paths:
- `/var/lib/litfoundry` (standard system package)
- `/srv/litfoundry` (alternative for non-packaged)
- `/home/litfoundry/data` (development)

**Permissions:**
- `litfoundry init` sets mode `0700` (rwx for owner only)
- Typically owned by the `litfoundry` service user

**Systemd service example** (for reference; full service files are in `packaging/`):
```ini
[Service]
Environment="LITFOUNDRY_DATA_ROOT=/var/lib/litfoundry"
Environment="LITFOUNDRY_RUN_MODE=server"
Environment="LITFOUNDRY_PORT=5080"
Environment="LITFOUNDRY_TRUSTED_PROXIES=127.0.0.1"
Environment="LITFOUNDRY_ALLOWED_HOSTS=localhost,127.0.0.1,litfoundry.internal"
```

**Example `.env` for Linux development:**
```
LITFOUNDRY_DATA_ROOT=/tmp/litfoundry
LITFOUNDRY_RUN_MODE=workstation
LITFOUNDRY_PORT=5080
```

## Reverse Proxy Setup

LitFoundry is designed to run behind a reverse proxy (e.g., Caddy, nginx) that handles TLS. The proxy forwards requests to `127.0.0.1:5080`.

### Caddy Example

See `packaging/caddy/Caddyfile.example` for a complete example. In brief:

```caddy
litfoundry.example.internal {
    reverse_proxy 127.0.0.1:5080
}
```

Then set:
```
LITFOUNDRY_TRUSTED_PROXIES=127.0.0.1
LITFOUNDRY_ALLOWED_HOSTS=localhost,127.0.0.1,litfoundry.example.internal
```

### nginx Example

```nginx
server {
    server_name litfoundry.example.internal;
    listen 443 ssl http2;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://127.0.0.1:5080;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $server_name;
        proxy_set_header Host $host;
    }
}
```

Then set:
```
LITFOUNDRY_TRUSTED_PROXIES=127.0.0.1
LITFOUNDRY_ALLOWED_HOSTS=localhost,127.0.0.1,litfoundry.example.internal
```

## Initialization

Run `litfoundry init` to create and initialize the data root:

```bash
litfoundry init
# or
LITFOUNDRY_DATA_ROOT=/var/lib/litfoundry litfoundry init
```

This:
1. Creates the data root directory
2. Creates subdirectories: `logs/`, `secret_material/`, `projects/`, `trash/`, `backup_staging/`
3. Creates the catalogue database at the latest schema version
4. Applies restrictive permissions
5. Marks the root as initialized (idempotent)

## Running the Server

```bash
litfoundry serve
# or with options:
LITFOUNDRY_RUN_MODE=server LITFOUNDRY_PORT=5080 litfoundry serve
```

## Status Check

```bash
litfoundry status
```

Exits with code 0 if healthy, non-zero if there are issues. Checks:
- Data root existence and permissions
- Catalogue database accessibility and schema version

## Troubleshooting

### "Network drive ... is not supported"

**Cause:** The data root is on a network filesystem.

**Solution:** Move the data root to a local disk. LitFoundry requires local filesystems for database performance and correctness.

### "UNC paths are not supported"

**Cause:** The data root is a UNC path (`\\server\share\litfoundry`).

**Solution:** Use a local disk path instead.

### "Access denied" or "Permission denied"

**Cause:** The data root was initialized by a different user or permissions were misconfigured.

**Solution:** Re-run `litfoundry init` as the appropriate user, or check with `litfoundry status`.

### "Host header did not match"

**Cause:** The request `Host` header is not in `LITFOUNDRY_ALLOWED_HOSTS`.

**Solution:** Add the hostname to `LITFOUNDRY_ALLOWED_HOSTS` (or to the reverse proxy's `Host` header rewriting).

## Security Considerations

1. **Restrict the data root:** Always use `litfoundry init` to create the data root with proper permissions.
2. **Use HTTPS:** Run behind a TLS-terminating reverse proxy (e.g., Caddy with an organizational certificate or Let's Encrypt).
3. **Trusted proxies:** Carefully configure `LITFOUNDRY_TRUSTED_PROXIES`; an empty list is safest.
4. **Firewall:** Ensure `127.0.0.1:5080` is not exposed to untrusted networks.
5. **Secret material:** The `secret_material/` directory contains encryption keys; back it up securely and never commit it to version control.

## Further Reading

- See `packaging/caddy/Caddyfile.example` for reverse proxy configuration
- See `openspec/changes/m1-platform-foundation/design.md` for architectural rationale
