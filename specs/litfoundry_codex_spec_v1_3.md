# LitFoundry — Codex Implementation Specification

**Version:** 1.3 (20 October 2026)  
**Status:** Implementation-ready design and acceptance contract (official LitFoundry naming, local and optional Active Directory sign-in, scheduled full backups)  
**Product:** **LitFoundry** — *From literature to insight.*  
**Licence:** GNU General Public License v3 (see `LICENSE`)  
**Target:** Multi-user, LAN-hosted, cross-platform bibliometric and PRISMA research application

## 0. Instructions to Codex

Implement this application in an incremental, test-driven series of vertical slices. This document is the product and architectural source of truth. Do not replace the specified stack, omit security controls, generate placeholder bibliometric results, or assume access to paid bibliographic APIs. When an external dependency or API is uncertain, isolate it in an adapter, verify its installed interface, document the finding, and retain an operational manual-import path. Implement migrations and tests with each slice. Do not use an LLM service as a mandatory dependency. All end-user and administrator features must be available through the web GUI and through versioned REST endpoints, except the host-only operations in Section 18.1 (bootstrap token, admin password recovery, migration and full restore execution), which are deliberately CLI-only. In v1, full backups are also CLI-only (Section 0.2).

**Priority levels:** MUST = release requirement; SHOULD = desirable and testable improvement; MAY = later enhancement.

### 0.1 Official product name and naming contract (binding)

- **Public product name:** **LitFoundry** (exact capitalisation). **Tagline:** *From literature to insight.* **Product description:** Open-source software for systematic literature reviews, PRISMA workflows and bibliometric analysis. Use these consistently in the application header, login/setup, administrator console, help/about screen, installer, documentation, project manifests, ZIP metadata and error-report headers.
- **Canonical machine-readable identifier:** `litfoundry` (lowercase ASCII). Python distribution and import package: `litfoundry`; repository name: `litfoundry`; CLI executable: `litfoundry`; production OS service ID: `litfoundry`, a supervisor that runs the `litfoundry-server` and `litfoundry-worker` processes (these names also identify the processes in logs); application data directory: `LitFoundry` on Windows/macOS and `litfoundry` on Linux. Do not create new identifiers named `brm`, `pybrm`, `bibliometric-research-manager`, or `appctl`.
- **Python packaging:** `pyproject.toml` declares a distribution named `litfoundry`, exposes `[project.scripts] litfoundry = "litfoundry.cli:main"`, and packages code under `src/litfoundry/`. The Flask application factory should be imported from `litfoundry.app` (or an explicitly documented stable submodule). All documentation and tests must use these names.
- **Network/deployment:** Example HTTPS hostname `litfoundry.example.internal`; localhost-only Waitress endpoint stays `127.0.0.1:5080`, proxied by Caddy. Configuration environment variables should use the `LITFOUNDRY_` prefix, including `LITFOUNDRY_DATA_ROOT`; include a cross-platform configuration reference. The example hostname is a placeholder, not a hard-coded DNS dependency.
- **Data storage:** Keep the stable generic SQLite filenames `catalog.sqlite` and `project.sqlite` and versioned REST prefix `/api/v1` unchanged. Choose cross-platform default data roots appropriate for service permissions: Windows `%PROGRAMDATA%\LitFoundry` for service mode; Linux `/var/lib/litfoundry`; macOS `/Library/Application Support/LitFoundry` for system-wide mode, with user-scoped alternatives for non-service development. `litfoundry init` and the installers must set restrictive permissions on the data root (service identity and host administrators only); on Windows, do not rely on inherited `%PROGRAMDATA%` permissions, which give every local user read access. Never embed host-specific paths in portable project ZIPs.
- **Archive names:** Single-project exports use `litfoundry_project_<project_uuid>_<YYYYMMDD_HHMMSSZ>.zip`, and full-system backups use `litfoundry_full_<YYYYMMDD_HHMMSSZ>_<run_uuid_short>.zip`. All ZIP manifests include `"product": "litfoundry"`, `"product_name": "LitFoundry"`, plus the documented export/backup format version; imports validate the identifier and version before changes. Descriptive report names and figure titles may mention PRISMA, bibliometrics and the project title.
- **Reserved account:** The special local administrator username remains literally `admin` and is **not** renamed to `litfoundry` or an email address.
- **Compatibility:** There is no requirement to accept archives produced by the previously proposed, unimplemented `brm` naming scheme. If an earlier development build exists, provide an explicit migration/alias plan rather than silently reusing or overwriting files.

### 0.2 Release scope (v1)

Every requirement in this specification is **MUST** for the v1 release unless the table below marks it **SHOULD** (planned for the next release) or **MAY** (later enhancement). Build SHOULD and MAY features behind the same interfaces so they can be added without rework, and write their tests when they are built.

| Feature | Priority | What v1 provides instead |
|---|---|---|
| Scheduled full backups: scheduler (16.2), backup settings and admin screens (16.1), retention and rotation (16.4), `/admin/backups/*` endpoints | SHOULD | Manual full backup, verification and offline restore from the CLI (`litfoundry backups create --destination PATH`, `backups verify`, `restore`), using the snapshot algorithm (16.3) and restore workflow (16.5) |
| Linux and macOS packages, with systemd and launchd services | SHOULD | Windows installer and Windows Service. Linux and macOS run from a venv; CI runs the full test suite on all three |
| Scopus Search API adapter | SHOULD | Scopus CSV/BibTeX/RIS import; the Scopus query is still compiled for copying into Scopus |
| Web of Science API Expanded adapter | SHOULD | WoS Starter API (MUST) plus WoS export-file import |
| ASReview import/export | SHOULD | None |
| Co-citation and bibliographic coupling (analyses 6–7) | SHOULD | None |
| Research maturity table (analysis 10) | SHOULD | None |
| Topic clusters and thematic evolution (analysis 8) | MAY | None; needs its own specification first |
| TOTP second factor for `admin` | MAY | Per-IP throttling and host-only password recovery |
| Personal-data export and pseudonymisation tooling | MAY | Documentation of what personal data is stored; the admin handles requests manually |
| Multiple AD domains; Windows SSO/Kerberos | MAY | One AD domain with username/password sign-in |
| PyBibX and BibFusion connectors; email notifications | MAY | None |

Optional Active Directory sign-in, OpenAlex and WoS Starter API search, query compilers for all sources, file imports, deduplication, full PRISMA screening, analyses 1–5 and 9, reports, project export/import and the Windows installer are MUST.

## 1. Product scope and explicit decisions

LitFoundry enables registered users to maintain multiple independent literature-research projects. Users sign in with a LitFoundry username and password; optionally, the administrator can also connect one Microsoft Active Directory domain so that pre-provisioned directory users sign in with their AD credentials. The built-in `admin` is always a local LitFoundry account. The system supports scheduled, verified, retained full-installation ZIP backups. Within a project, they define keyword groups and filters, enable OpenAlex / Scopus / Web of Science independently, inspect source-specific queries, execute and import searches, deduplicate records, conduct PRISMA-guided screening including full-text eligibility, freeze corpora, run bibliometric analyses, publish diagrams and reports, and download/import self-contained project ZIP archives. All history, decisions, raw records, normalisation, and analysis provenance persist across restarts.

Binding decisions (details in Sections 5 and 16):

1. **LAN:** One server installation accepts browser connections from multiple computers on an internal network. HTTPS is required in LAN deployments. Internet publication databases remain separate outbound dependencies.
2. **Public projects:** 'Public' means discoverable by **all authenticated users of this installation**, not anonymous internet viewers. A public project has default `viewer` or `editor` access for all registered users. The owner may also grant individual exceptions. Anonymous users cannot view any project data.
3. **Project storage:** Each project is a folder containing its own SQLite database (`project.sqlite`) plus project artifacts. A separate central `catalog.sqlite` manages users, settings, project discovery, sharing and job scheduling. **No single per-user project database**.
4. **Accounts:** Only the built-in `admin` account creates and disables users. Local accounts, including `admin`, sign in with a username and a LitFoundry-managed password, and local sign-in is always available. If the admin configures the optional Active Directory connection, pre-provisioned AD users sign in with their directory account name and AD password. No self-registration or just-in-time AD provisioning.
5. **Credentials:** Admin-managed shared source credentials; each user may optionally supply a per-source personal override. Effective credential = user's enabled override, else shared default, else unavailable. Never export secrets.
6. **Review method:** Complete PRISMA identification, screening, optional retrieval and full-text eligibility (when genuinely performed), exclusion accounting, versioned included sets, plus bibliometric analysis.
7. **Operating systems:** Windows, Linux and macOS, with CI on all three. v1 ships a packaged installer for Windows; Linux and macOS packages follow (Section 0.2).
8. **Distribution:** Python virtual environment for development and independently packaged distributions for end users. The packaged app can act as a LAN server; other users need only browsers. **Additional requirement:** Administrator-configured scheduled ZIP backups of the complete installation data, with destination selection, date/time filenames and count-based retention (scheduling and retention are SHOULD; v1 provides manual CLI backups, Section 0.2).
9. **Trust model:** The administrator is fully trusted. The admin can read and change every project in the application (audited) and, through the server host and full backups, all stored data and credentials. Users are told this on the About screen and in the documentation.

### Roles

- **Admin:** A single, reserved account that always signs in with username exactly `admin` and a LitFoundry-managed password, never through AD. Creates, disables and resets local users, pre-provisions AD users, configures the optional AD connection, shared source credentials, proxy/network settings, scheduled full backups and system diagnostics. Has full owner-equivalent access to every project (see Project rights); every admin change inside a project, and each admin opening of a project the admin does not own, is audited. Admin-access entries go to the catalogue `audit_events` table (with `project_id`), which the backup write barrier exempts, so admin reads never fail during a backup.
- **User:** Either a local account (username and LitFoundry-managed password) or a directory-backed AD account, pre-provisioned by the admin. Owns and edits projects and sees projects to which the account has access.

### Project rights

| Action | Admin | Owner | Explicit editor / public-edit | Explicit viewer / public-view |
|---|---|---|---|---|
| Discover and read | Yes | Yes | Yes | Yes |
| Download permitted result tables/figures | Yes | Yes | Yes | Yes |
| Edit strategy, records, screening | Yes | Yes | Yes | No |
| Run searches/analyses | Yes | Yes | Yes | No |
| Export full project ZIP (raw data included) | Yes | Yes | No | No |
| Manage shares and ownership | Yes | Yes | No | No |
| Delete / archive project | Yes | Yes | No | No |

Access resolution: admin (full access, audited) > owner > explicit per-user ACL (`editor`, `viewer`, `deny`) > public default (`editor`, `viewer`, or none) > deny. The `deny` exception lets an owner exclude an account from an otherwise public project; it never applies to the admin. A disabled account always denies access. Privileges must be checked on **every** API and background job and again when generating download links.

## 2. Technology and licensing

| Layer | Required components |
|---|---|
| Server | Python 3.12+, Flask with application factory and Blueprints; Waitress WSGI for cross-platform serving |
| Persistence | SQLAlchemy 2.x + SQLite with WAL, foreign keys, busy timeout |
| Migration | Flask-Alembic for the catalogue. For the project *template* schema, use Alembic's programmatic API against each `project.sqlite`, passing the connection through `Config.attributes` (Alembic's documented pattern for sharing a connection); an explicit orchestrator applies project migrations to every project |
| Security | Flask-JWT-Extended, Flask-CORS, Argon2id, audited permission checks, CSRF, login throttling, `ldap3` (LGPL-3.0, GPLv3-compatible) for the optional Active Directory connection via LDAPS/StartTLS. ldap3 releases rarely (latest stable 2.9.1, July 2021; 2.10 is at release-candidate stage), so pin it and run the AD test suite on every supported Python version |
| Frontend | Vue 3 **runtime-only production build** (no in-browser template compiler); components are plain ES modules using render functions (`h()`), with no Vue SFC, Vite or Node runtime; Axios; Tailwind CSS compiled into a local static stylesheet; all vendor files served locally |
| Data APIs | Direct HTTPS REST adapter for OpenAlex (PyAlex is not used in the worker because its API key setting is module-global); HTTPS adapter for the Clarivate Web of Science Starter API; file imports for Scopus, WoS and OpenAlex. SHOULD: Scopus Search API adapter and WoS API Expanded adapter (Section 0.2) |
| Science | pandas, numpy, scipy, NetworkX, RapidFuzz, Biblium behind an adapter; optional PyBibX/BibFusion as separately tested adapters |
| Screening | Native persistence/reviewer interface; ASReview interoperable import/export, no mandatory embedded ASReview server |
| Diagrams | `prisma-flow` (PyPI `prisma-flow`, import `prismaflow`, BSD-3-Clause; alpha, first released May 2026, so pin an exact version) behind an adapter, with a native SVG fallback, for PRISMA SVG and validations |
| Visualization | Apache ECharts (Apache-2.0) for interactive network graphs and charts, including SVG/Canvas rendering; backend SVG/PNG exports where feasible |
| Tests | pytest, pytest-flask/httpx (as relevant), Playwright for Python (`pytest-playwright`), lint/typecheck, integration fixtures |
| Packaging | PyInstaller one-folder distribution built on each target OS (Windows in v1; Linux and macOS are SHOULD, Section 0.2); platform launcher, optional service installation |
| Full backup | Standard `sqlite3.Connection.backup()` for SQLite snapshots; Python standard-library `zipfile` (ZIP64, deflate) for unencrypted archives; built-in scheduled-job coordinator with persisted due-times |
| LAN HTTPS | Caddy TLS reverse proxy (recommended, separately installed/optionally bundled where licence permits), serving a stable internal DNS name; Waitress on loopback |

LitFoundry is licensed under the GNU GPL v3 (see `LICENSE`). Every dependency bundled into a distributed package must be GPLv3-compatible (for example MIT, BSD, Apache-2.0, LGPL-3.0 or GPL-3.0); exclude GPL-2.0-only components, licences that forbid commercial use, and data or model files with non-commercial terms. Binary distributions must ship licence texts and notices and offer the corresponding source for LitFoundry and the bundled copyleft components. Require a checked-in lockfile or constraints file, licence inventory and SBOM, and run an automated licence review before packaging; do not assume all transitive dependencies of Biblium/PyBibX are compatible. Verify pinned package versions and their redistribution notices before release. Avoid bundling large optional ML dependencies (PyBibX pulls in transformer and topic-model stacks) unless enabled.

**Frontend build constraint:** Use the Vue 3 runtime-only production build (`vue.runtime.esm-browser.prod.js`); never ship the full build, because in-browser template compilation uses `new Function()` and would require `'unsafe-eval'` in the CSP. Write every component as a plain ES module whose `setup()` returns a render function built with `h()`: no `template` strings, in-DOM templates or Vue SFCs. The CSP is `script-src 'self'`, with no `'unsafe-eval'` and no inline scripts. Vendor Vue, Axios and ECharts as exact-version, checksum-verified local copies in `frontend/vendor/` (fetched by a pinned script, with their licences) and always serve those copies, in development and in packages; the GUI never loads code from a CDN. Import Vue as the self-contained `vue.runtime.esm-browser.prod.js` module by relative path, and load Axios and ECharts as their classic global builds (`axios.min.js`, `echarts.min.js`) with `<script src>` before the application module; do not use import maps, which require an inline script. Because vue-router's browser ESM build imports bare `'vue'`, implement client routing as a small in-house History-API router module. Compile Tailwind into static CSS using a pinned standalone Tailwind CLI; Tailwind only detects complete class names, so `h()` calls must use full literal class strings, never class names assembled from fragments. No Node application server or Node build step is required.

## 3. Deployment topology

```text
Browser on workstation A/B/C
         | HTTPS on private LAN, e.g. https://litfoundry.example.internal/
         v
Caddy reverse proxy on application host (LAN interface :443)
         | HTTP loopback only
         v
Waitress -> Flask REST API + static SPA (127.0.0.1:5080)
         |                |
         |                +--> central catalog.sqlite (identity, directory config, ACL, backup schedule, jobs)
         +--> services --> project-specific project.sqlite + project files
         |
         +--> local worker process(es) -> OpenAlex / WoS Starter (v1), Scopus / WoS Expanded (SHOULD) via outbound HTTPS
         +--> optional AD adapter -> Active Directory domain controller via LDAPS/StartTLS
         +--> backup scheduler/worker -> timestamped ZIP on admin-configured server path
```

- The **Flask service listens on localhost** (`127.0.0.1:5080`) behind the TLS reverse proxy; the **reverse proxy** listens on the LAN. Never expose Flask's development server or Waitress plaintext endpoint on the LAN in production.
- Use a stable internal DNS hostname, TLS certificates trusted by client computers (organisation CA or Caddy internal CA whose root has been explicitly trusted), restricted inbound firewall rule, and HTTPS-only cookies. Document CA trust distribution for Windows/macOS/Linux and browsers. Caddy `tls internal` is possible but clients do not automatically trust that CA.
- Configure explicit trusted proxy IPs and forwarded headers, host allowlist, request limits and CSP. Set secure-cookie flags. Same-origin SPA and `/api/v1` makes CORS unnecessary for normal use; retain Flask-CORS but enable **only** on allowlisted origins for special development deployments, with credentials and no wildcard.
- Provide the CLI in Section 18.1 and a package launcher. Installer does not need to install on client PCs. Default port, data root and DNS host are configurable.
- **Workstation mode** (one user on one machine): Waitress binds `127.0.0.1` only, with no Caddy and no LAN access, and the browser runs on the same host at `http://localhost:5080`. All authentication, authorisation and CSRF rules still apply; cookies may omit the `Secure` flag only in this mode and only while bound to loopback. Any access from another computer requires server mode (Caddy + HTTPS).
- The server should continue serving existing projects without internet; online searches fail clearly and can be retried. The GUI never loads code from a CDN.

## 4. Data layout and persistence

```text
<data_root>/
  catalog.sqlite                # central accounts, access, queue, global settings
  secret_material/              # master key and session signing key; OS-permission protected; never served; excluded from project exports; included in full backups
  backup_staging/               # transient consistent snapshots; never recurse into the backup destination
  trash/                        # deleted projects awaiting purge
  logs/
  projects/
    <project_uuid>/
      project.sqlite            # ALL project-specific relational records
      manifest.json             # portable schema/export info (non-secret)
      sources/<search_run_uuid>/<source>/raw/
      imports/
      attachments/              # optionally uploaded full texts
      figures/
      reports/
      exports/                  # generated project ZIPs; expire (Section 15); excluded from full backups
      temp/                     # excluded from project exports and full backups
```

The administrator must configure a backup destination outside `<data_root>` (there is no default destination); backups are generated on the server and placed there, not downloaded to the browser as a directory. Only the server host owns/mounts SQLite files. **Never store active SQLite databases on SMB/NFS shares**. Use a local disk with appropriate backup; distribute backups over a network if necessary. UUIDs form directory names; project folders are named by project UUID only and ownership is recorded solely in the catalogue, so transferring ownership never moves files. User-supplied titles are metadata only. Refuse unsafe symlinks, relative paths, `..`, archive traversal and attempts to escape `data_root`.

### 4.1 Central catalogue schema (minimum)

- `users(id UUID PK, account_type [local|active_directory], username_normalized nullable, display_name, contact_email nullable, password_hash nullable, must_change_password, role [admin|user], active, session_version, created_at, last_login_at)`. `username_normalized` is required and unique for `local` accounts and null for AD accounts. Local usernames are lowercased and must match `^[a-z0-9][a-z0-9._-]{1,63}$`, so they never contain `@` or `\` and cannot be mistaken for AD identifiers. The username `admin` is reserved for the single built-in account, which is the only account with `role=admin` (enforce with a partial unique index). Contact email is informational, never a login identifier.
- `directory_identity_bindings(id UUID, user_id UNIQUE FK, object_sid UNIQUE, object_guid nullable, samaccountname_normalized, upn_normalized, last_directory_sync_at, directory_status, created_at)`; the immutable AD SID, not a name or email address, links a directory account to its pre-provisioned LitFoundry user.
- `directory_config(id single_row, enabled, domain_dns_name, netbios_name, upn_suffixes_json, server_hosts_json, base_dn, service_account_identity, service_account_secret_ref, tls_mode [ldaps|starttls], ca_bundle_ref, timeouts_json, revalidation_interval_minutes, revalidation_grace_minutes, revision, updated_at)`; one optional AD domain. The service account is required whenever `enabled=true`. Stores only safe configuration and secret references, never a plaintext password.
- `auth_settings(id single_row, password_policy_json, access_token_minutes, refresh_token_hours, throttle_policy_json, revision, updated_at)`; local sign-in is always enabled and has no switch. Any change that must invalidate sessions (for example disabling AD) increments `revision`.
- `login_throttle(key, window_start, failure_count, blocked_until)`; keys cover source IP and `(provider, normalized identifier)`.
- `system_settings(key PK, value_json, updated_at)`; no clear-text credentials.
- `source_credentials(id, scope [global|user], user_id nullable, provider, secret_ref, enabled, updated_at)`
- `project_directory(id UUID PK, owner_user_id FK, title, public_access [none|viewer|editor], state [provisioning|ready|archived|quarantined|deleting|error], relative_path, imported_from_json nullable, created_at, updated_at, project_schema_version, latest_indexed_revision)`; the catalogue is the only record of ownership. `public_access` values `none`, `viewer` and `editor` are shown in the UI as Private, Public view and Public edit.
- `project_acl(project_id, user_id, role [viewer|editor|deny], created_by, updated_at)`
- `jobs(id UUID PK, project_id, requester_id, type, status [queued|running|partial|completed|failed|cancelling|cancelled], idempotency_key UNIQUE nullable, correlation_id, priority, not_before, scope_json, args_json, progress_json, lease_owner, lease_expires_at, heartbeat_at, attempt, max_attempts, cancellation_requested, created_at, started_at, finished_at, last_error_code)`; `scope_json` holds the write scope (Section 9).
- `refresh_tokens(jti PK, user_id, family_id, issued_at, expires_at, revoked_at nullable, replaced_by nullable)`. Access tokens are short-lived and checked against `users.session_version` and `auth_settings.revision` on every request, so no access-token blocklist is needed.
- `active_writers(id, process_id, operation, project_id nullable, started_at, heartbeat_at)`; in-flight application-data write units, used by the backup write barrier (Section 16.3).
- `backup_settings(id single_row, enabled, frequency [daily|weekly|monthly], local_time_hhmm, iana_timezone, weekday nullable, monthday nullable, destination_server_path, series_id, retain_count, include_logs, missed_run_grace_minutes, retry_policy_json, next_due_at_utc, last_attempted_at_utc, revision, updated_by, updated_at)`; all modifications require the `admin` account. `series_id` changes whenever the destination changes.
- `backup_runs(id UUID PK, series_id, occurrence_key UNIQUE nullable, scheduled_for_utc, started_at, completed_at, status [queued|running|completed|failed|cancelled], destination_file, archive_sha256, archive_bytes, source_snapshot_id, error_code, validation_json, rotation_json, initiated_by [schedule|admin|cli], created_at)`; scheduled runs set `occurrence_key`, which prevents duplicates. Persist run history outside the backup archive and include a copy in its manifest.
- `system_leases(name UNIQUE, owner, expiry, fencing_token)` for maintenance/backup/migration locks and single-scheduler coordination.
- `audit_events(id, actor_id, project_id nullable, action, details_json, timestamp)`

Create unique constraints and indexes for normalized usernames, AD SIDs, the reserved admin singleton, project owner, public state, ACL, job states and idempotency keys, schedule due-time and occurrence keys, and maintenance leases. Never return secrets or password hashes from REST endpoints.

### 4.2 Per-project schema (minimum)

- `project_info(id, title, description, objectives, research_questions_json, created_at, updated_at, revision)`; ownership is recorded only in the catalogue.
- `source_selections(provider, enabled, source_options_json)`
- `keyword_spec_versions(id, project_id, ast_json, scope_json, rationale, created_by, created_at, immutable)`
- `query_versions(id, spec_id, provider, generated_query, override_query nullable, effective_query, compiler_version, validation_json)`
- `search_runs(id, spec_id, status, started_at, ended_at, created_by)`
- `source_runs(id, search_run_id nullable, provider, origin [api|file_import], query_version_id nullable, executed_request_json, requested_by, credential_scope_used [personal|shared|none], status, reported_count, retrieved_count, completeness [complete|partial], missing_required_fields_count, error_code nullable, checksum, cursor_state, started_at, ended_at, created_at)`; file imports use `origin=file_import`, no query version and `credential_scope_used=none`
- `raw_records(id, source_run_id, provider, provider_record_id, raw_file_ref, raw_sha256, imported_at)`
- `works(id, canonical_title, abstract, year, date, doi_normalized, journal, work_type, language, merged_into_work_id nullable, metadata_json, revision)`; work rows are never deleted, and a merged work keeps its ID and points to the retained work
- `work_identifiers(work_id, scheme, value)`
- `work_sources(work_id, raw_record_id, selected_fields_json, confidence)`
- `authors`, `affiliations`, `work_authors`, `work_affiliations`, `keywords`, `work_keywords`, `work_references`, `citation_counts` with source/provenance where available (do not name a table `references`, which is an SQL keyword)
- `duplicate_candidates(id, work_a, work_b, score, factors_json, status [pending|merged|rejected|deferred])` and `merge_decisions(id, actor_id, timestamp, originals_json, retained_work_id, decision, reason, reversible_event_ref)`
- `review_protocol_versions(id, method [systematic|scoping|bibliometric], criteria_json, reviewer_policy_json, created_by, created_at)`
- `screening_rounds(id, stage, reviewer_policy_json, started_at, closed_at)`
- `record_screening_decisions(id, work_id, stage [title_abstract|full_text], reviewer_id, decision [include|exclude|uncertain], reason_code nullable, notes, round_id, version, timestamp)`
- `retrieval_attempts(id, work_id, report_id, outcome [retrieved|not_retrieved|not_sought], reason, actor_id, timestamp)`
- `attachments(id, sha256, size, mime, original_filename, relative_path, uploaded_by, uploaded_at)`
- `full_text_reports(id, work_id, attachment_id nullable, external_link nullable, metadata_json)` (allow many reports per study where applicable)
- `study_groups(id, label, details)` and `study_work_links(study_id, work_id)` (separate records, reports, works and studies)
- `screening_resolutions(id, work_id, stage, final_decision, resolved_by, timestamp, reason_code)`
- `corpus_snapshots(id, label, protocol_version_id, selected_search_runs_json, created_by, created_at, hash, frozen)` and `corpus_members(corpus_id, work_id, study_id nullable)`; `hash` is SHA-256 over a canonical serialisation (sorted member IDs, protocol version ID, selected search-run IDs) and excludes the project UUID, so it survives export/import rekeying
- `keyword_normalization_rules(id, pattern, replacement, rule_type, enabled, revision)`
- `analysis_runs(id, corpus_id, engine, analysis_type, parameters_json, software_versions_json, input_hash, status, queued_at, started_at, finished_at, created_by)`
- `artifacts(id, analysis_run_id nullable, kind, relative_path, sha256, size, mime, created_at)`
- `prisma_snapshots(id, corpus_id, counts_json, exclusions_json, overrides_json, validation_json, generated_at)`
- `project_audit_events(id, actor_id, action, details_json, timestamp)`
- `project_people(user_id PK, display_name, origin [local|imported], imported_label nullable, first_seen_at)`; a snapshot of every account that has acted in the project. Reviewer and actor IDs in the project database refer to this table, because foreign keys cannot cross into the catalogue.

Use immutable source runs and append-only reviewer/audit histories. Editable normalized records need integer `revision` for optimistic concurrency (`If-Match`/ETag or version field). Preserve field-level provenance and conflicting-source values. Use server-generated UTC timestamps and stable UUIDs. Source counts distinguish retrieved *records*, reports and included *studies*.

### 4.3 Project creation, routing and migration

1. Authenticated creator requests a project. Insert central directory row `provisioning`, create temporary project folder and project DB from latest migration, write manifest, atomically rename staging folder (same filesystem), mark `ready`. On failure, remove the staging folder and the catalogue row; `error` is reserved for an existing project found to be damaged.
2. Every API request resolves the project UUID through the central catalogue, authorises the current user, then opens **only that project's** scoped SQLAlchemy session. Use short-lived sessions. Project engines use `NullPool`, applying PRAGMAs on each connect, so no idle connections are held between operations: Windows cannot rename or move a folder while any process holds a file in it open. An LRU cache may keep engine objects; before opening a project, each process re-checks `project_directory.state` and refuses normal operations on projects that are `deleting`, `quarantined` or `error`.
3. Cross-database writes cannot be atomic. Use explicit workflow states, idempotency keys and a reconciliation command; never assume a single transaction can span `catalog.sqlite` and project DB.
4. Alembic (Section 2) manages versioned schema scripts for `catalog` and the **project database template**. Authentication and backup catalogue revisions must be migrated with the central schema. A migration coordinator acquires a global maintenance lock, backs up databases, then applies project migrations sequentially with verification and schema-version recording. Do not register hundreds of dynamically created per-project engines as fixed Flask binds. Test rollback/restore if a migration fails.
5. Deletion is two-stage: mark directory `deleting`, revoke access/cancel jobs, wait (bounded) for in-flight operations on the project to end, move the project folder to `<data_root>/trash/` and eventually purge it. Provide owner confirmation and a backup/export opportunity. Archiving (`archived`) makes a project read-only without deleting it.

## 5. Authentication and authorization

### 5.1 Sign-in methods

| Method | Who | Identifier | Password check | Account creation |
|---|---|---|---|---|
| Local (always available) | The built-in `admin` and all local users | Username such as `jsmith` (case-insensitive; character rules in Section 4.1) | Argon2id hash stored by LitFoundry | Admin creates the account and sets an initial password that must be changed at first sign-in |
| Active Directory (optional) | Pre-provisioned AD users | `DOMAIN\jsmith`, UPN such as `jsmith@corp.example.org`, or bare `jsmith` | TLS-protected bind to the configured domain | Admin looks up the AD account through the service account and binds its SID to a new LitFoundry user |

- Local sign-in cannot be disabled. AD sign-in is available only while an AD connection is configured, has passed its connection test and is enabled (Section 5.3).
- A local account has exactly one normalised username. Contact email is optional and informational; it is never a login identifier, and no mail transport or email verification is assumed. Display name is separate from the username.
- When AD is enabled, the sign-in form shows a method selector (`LitFoundry account` / `Active Directory`) and the request carries an explicit `provider`. A local `jsmith` and an AD `jsmith` are separate accounts; there is no automatic linking, merging or privilege inheritance between them.
- AD users have no LitFoundry password; local password change and reset apply only to local accounts.
- Only admin-created accounts can sign in. A correct AD password for an account without a LitFoundry binding is denied, and AD groups never grant LitFoundry roles in this release.

Illustrative login request bodies (responses never return credentials):

```json
{"provider":"local", "identifier":"jsmith", "password":"<user-supplied>"}
```

```json
{"provider":"active_directory", "identifier":"CORP\\jsmith", "password":"<user-supplied>"}
```

`provider` defaults to `local` when omitted. The administrator signs in as `{"provider":"local", "identifier":"admin", ...}`; the `active_directory` provider rejects the identifier `admin`. Never accept a caller-supplied `role`, `user_id`, SID, DN, LDAP filter or server address as proof of identity. Sign-in methods are server-configured, not client-controlled flags.

### 5.2 Built-in administrator and first-run bootstrap

- On first run, with no administrator present, everything except health and bootstrap is locked and the UI shows `/setup`. The first and only administrator is the local account `admin`: the username is fixed, not editable and never an AD account.
- Setup requires a single-use, short-lived bootstrap token plus a strong new password; there is no factory default password. `litfoundry init` (or the first service start) generates the token, prints it on the interactive console when there is one, and writes it to `<data_root>/bootstrap-token.txt`, readable only by the service identity and host administrators. The token is never logged, and the file is deleted when the token is consumed or expires; `litfoundry bootstrap-token` issues a new one while setup is pending. Consume the token atomically under a unique database constraint.
- After setup, bootstrap never succeeds again. A lost admin password is reset with the host-only, audited `litfoundry admin reset-password` command, which requires OS access to the data root.
- `admin` cannot be deleted, renamed or disabled, and no second admin-role account can be created in this release. Admin password changes are audited.
- `admin` always works when the domain is unreachable or AD is disabled. Failed `admin` sign-ins are throttled per source IP with exponential backoff, never by locking the account, so an attacker cannot lock out the only administrator.

### 5.3 Optional Active Directory connection

LitFoundry supports one AD domain. Use `ldap3` as the cross-platform LDAP client behind an `IdentityProvider`/`ActiveDirectoryAdapter` abstraction. The admin configures it under Admin → Authentication → Active Directory: domain DNS name, NetBIOS name, UPN suffixes, domain controller FQDNs, Base DN, TLS mode, CA bundle, timeouts, revalidation interval and grace period, and a **required** read-only service account. AD sign-in cannot be enabled until the configuration passes the connection test. Secret fields are write-only in the UI and API. Multiple domains are a future enhancement.

**Security rules:**

1. **TLS:** Require LDAPS or StartTLS with certificate-chain and hostname validation. Plaintext simple binds and disabled certificate verification are forbidden in server mode. Store the service-account password in the server secret store (Section 17). Set finite connect/read timeouts, connect only to the configured domain controllers, and do not follow referrals elsewhere.
2. **Look up first:** Using the service account, resolve the identifier to exactly one user object with escaped filter values and an allowlist of requested attributes (`objectSid`, `objectGUID`, `sAMAccountName`, `userPrincipalName`, `userAccountControl`, `msDS-User-Account-Control-Computed`, display name). Accept `DOMAIN\name` only for the configured NetBIOS name, UPNs only in the configured suffixes, and bare `sAMAccountName`. Reject ambiguous matches. Match account names case-insensitively while preserving their display spelling.
3. **Check provisioning before the password:** If the resolved SID has no active LitFoundry binding, or the AD account is disabled or locked, fail **without** binding as the user, so LitFoundry never adds bad-password counts to accounts that cannot use it. Return the same generic error, with similar timing, as for a wrong password.
4. **Verify the password:** Bind as the resolved user over the validated TLS connection. Reject empty passwords; anonymous or unauthenticated binds never count as success. Never store, log, replay or reuse the password after the request. Close connections on success and error paths.
5. **Throttling:** Throttle per source IP and per identifier, and keep the per-identifier limit below the domain's lockout threshold (configurable; default 3 failures per identifier per 15 minutes). The admin screen states that the limit must stay under the domain threshold.
6. **Revalidation:** Every `revalidation_interval_minutes` (default 15), re-check active AD users through the service account. On disable, lockout, deletion or SID change, revoke the user's sessions. If the domain cannot be reached for longer than the grace period, deny mutations and require a fresh sign-in once it is reachable; never fail open indefinitely.
7. **Diagnostics:** Report domain unreachable, certificate failure and service-account failure as distinct admin-only diagnostic events; sign-in responses stay generic. Log provider, resolved LitFoundry user ID when known and outcome, never credentials or full LDAP payloads.
8. **Disabling AD** blocks AD sign-in and revokes all AD users' sessions (via `auth_settings.revision`). AD users' projects remain, and the admin can still open them or transfer ownership.
9. No browser-integrated Windows SSO/Kerberos in this release; it may be added later as a separate adapter.

**Provisioning AD users:** Admin → Users → New → Active Directory searches through the service account, shows the matching account (name, UPN, SID) for confirmation, then creates the LitFoundry user and its SID binding with no LitFoundry password. At most one LitFoundry user may be bound to a SID. Rebinding requires an explicit, audited admin action with collision checks. Converting an account between local and AD is an explicit, audited admin action; ownership and ACLs reference the user UUID and are unaffected.

### 5.4 Sessions and authorization

Use Flask-JWT-Extended access cookies (`HttpOnly`, `Secure` except in workstation mode on loopback (Section 3), `SameSite=Lax`) with double-submit CSRF protection on unsafe methods; Axios sends `X-CSRF-TOKEN`. Access tokens are short-lived (default 15 minutes). A narrow-path refresh cookie carries a rotating refresh token recorded in `refresh_tokens`; reuse of a rotated token revokes its whole family, and logout revokes the family. JWT identity is the immutable user UUID with a `provider` claim; never treat a login name or AD group as authorization by itself. Never store tokens in localStorage or sessionStorage.

On every protected request, check the account's active state, `session_version`, `auth_settings.revision` and project access (Section 1). Disabling an account, changing or resetting a password, disabling AD and revoking project access take effect on the next request. Audit admin sign-ins, authentication configuration changes, binding changes, sign-in failures, account disablement and password resets.

The admin can create and disable accounts, reset local passwords and revoke sessions, and has full owner-equivalent access to every project (Section 1). Disabling an account does not delete its projects; the admin can transfer their ownership. The About screen and documentation state that the admin can see and change everything (Section 1, decision 9).

### 5.5 Admin settings and user provisioning UX

**Admin → Authentication:** password policy, session lifetimes, throttling, the optional AD connection (enable/disable, domain controllers, LDAPS/StartTLS, CA trust, Base DN, service account, revalidation), connection test with sanitised results, and audit history.

**Admin → Users:** list accounts; create a local account (username, display name, optional contact email, initial password with forced change); create an AD account (search, confirm, bind); enable/disable; reset local passwords; revoke sessions; transfer ownership of a user's projects. Account type is read-only after creation except through the explicit conversion action.

**Sign-in page:** username and password, with the method selector only when AD is enabled; neutral failure messages; service diagnostics only for the admin. `/auth/methods` tells the frontend whether AD is available, and `/auth/me` returns the user UUID, provider and role.

### 5.6 Shared bibliographic API credential precedence

For each bibliographic provider: (1) the job requester's enabled personal credential, if present; (2) the enabled shared credential set by the admin; (3) none. The UI shows the origin (`personal`, `shared`, `not configured`) but never the secret. Credential management is the same for local and AD accounts. Job runs record the credential scope for provenance, never the secret. A job never uses another user's personal credential, including when the admin runs it.

## 6. Project sharing

Visibility states (UI labels) Private, Public view and Public edit correspond to `public_access` values `none`, `viewer` and `editor`, managed on a sharing screen available to the owner and the admin. Public means any **authenticated** enabled account. Public edit requires an explicit warning and confirmation. The owner can additionally invite/grant/revoke per-user `viewer` or `editor` access and apply an explicit `deny`; the ACL policy in Section 1 is authoritative. Show effective permissions and a full change log. Editors run outbound API searches with their own credential override, otherwise the shared defaults; never use another user's personal secret. Background jobs recheck permissions before starting and before persisting results. Conflict detection is mandatory for collaborative edits and screening resolutions.

## 7. Keyword strategy and source-specific queries

### 7.1 Strategy editor

Editable groups of terms/phrases, OR within groups, AND between groups, nested AND/OR/NOT groups, quotation, year range, publication types, language, optional subject scope, and source selection toggles. Provide keyword synonyms and an exclusion group. Allow preview, manual source-specific override, test count (if available) and an explanation of what cannot be translated. Preserve AST, generated query, user override, actually executed URL/parameters, query compiler version, access scope, search timestamp and export checksum.

**Canonical stored form** (`ast` is stored in `keyword_spec_versions.ast_json`, `scope` in `scope_json`):

```json
{
  "ast": {
    "op": "and",
    "children": [
      {"op": "or", "children": [
        {"type": "phrase", "value": "digital twin"},
        {"type": "phrase", "value": "machine learning"}
      ]},
      {"op": "or", "children": [
        {"type": "phrase", "value": "mineral processing"},
        {"type": "term", "value": "flotat*", "wildcard": true}
      ]},
      {"op": "not", "children": [
        {"type": "term", "value": "medical"}
      ]}
    ]
  },
  "scope": {"fields": "title_abstract_keywords", "year_from": 2015, "year_to": 2026, "document_types": [], "languages": []}
}
```

Boolean nodes have `op` (`and`, `or`, `not`) and `children`; a `not` node has exactly one child and is valid only as a child of an `and` node (meaning AND NOT). Leaves have `type` (`term` or `phrase`), `value` and optional flags such as `wildcard`. Publish the grammar as a JSON Schema (`docs/query-ast.schema.json`) and validate every stored AST against it.

### 7.2 Compilers

- Scopus: compile appropriate `TITLE-ABS-KEY(...)` plus valid Scopus `PUBYEAR` filters and supported source filters; escaping and wildcard syntax must be tested. In v1 the Scopus query is offered for copying into Scopus's own interface, followed by a file import; the API adapter is SHOULD.
- WoS Starter (v1): compile `TS=(...)` combined with a `PY=` year range and `DT=` document types into the `q` parameter. Only the Starter field tags are available (TI, IS, SO, VL, PG, CS, PY, FPY, DOP, AU, AI, UT, DO, DT, PMID, OG, TS, SUR), so there is no language filter; declare that in the capability descriptor. WoS Expanded (SHOULD) uses the same `TS=` syntax with its full tag set against the versioned, configured endpoint. Validate supported operators and API entitlement.
- OpenAlex: compile to `search.title_abstract_keywords` (or `search.title_and_abstract`, per scope) plus work filters, with URL encoding; store exact scope/semantics. OpenAlex stems search terms, and wildcards and fuzzy terms require the unstemmed `.exact` parameter variant, so a query that mixes stemmed terms and wildcards cannot be compiled into one request: reject it with an explanation rather than silently changing its meaning. OpenAlex may use broader search/keyword semantics, so do **not** promise identical recall across sources. Request URLs are limited to about 4 KB; send the API key in the `Authorization` header, not the URL. When a query is too long, split only in a mathematically equivalent manner: partition the children of an OR node that is not inside a NOT and take the union of the results. **Never** split AND operands, or OR groups inside a NOT, and union them. Deduplicate the union by OpenAlex ID; the `reported_count` of a split query is the size of the deduplicated union, never the sum of sub-query counts. For untranslatable logic, require an explicit warning/error, not silently broaden results.

Provide source capability descriptors to the UI (wildcards, field scope, language, document types, dates, query length, count, cursor, quoted terms). Validated grammar must handle escaped quotes and avoid injection or malformed source syntax. All query previews display warnings and generated/overridden query side by side. Disabled providers MUST generate zero API calls.

## 8. External source adapters and imports

Interface (typed Protocol or ABC):

```python
class SourceAdapter(Protocol):
    source_id: str
    def capabilities(self) -> SourceCapabilities: ...
    def validate_credentials(self, credentials: Credentials) -> ValidationResult: ...
    def compile(self, spec: SearchSpec) -> CompiledQuery: ...
    def estimate(self, query: CompiledQuery, credentials: Credentials) -> CountEstimate: ...
    def retrieve_page(self, query: CompiledQuery, credentials: Credentials, cursor: str | None) -> SourcePage: ...
    def normalize(self, raw_record: dict) -> NormalizedRecord: ...
```

Each adapter must preserve raw payload, response schema/version, original query and pagination state. Map errors to typed codes (`AUTH_REQUIRED`, `ACCESS_DENIED`, `INVALID_QUERY`, `RATE_LIMITED`, `SOURCE_UNAVAILABLE`, `PARTIAL_RESULTS`, `UNSUPPORTED_FILTER`, etc.). Use bounded retries and exponential backoff for retryable failures only. Prevent outbound SSRF: endpoints/hosts hardcoded or allowlisted by provider config, no arbitrary URLs from users. Adapters pass credentials with each request; never put credentials into module-global library configuration (such as `pyalex.config` or pybliometrics' configuration) inside a shared worker, because concurrent jobs can belong to different users.

**OpenAlex:** direct HTTPS REST adapter, published-date filters, relevant metadata and cited work IDs, rate-limit compliance and cursor pagination; report records lacking abstracts or references. Cursor paging beyond the first page needs an API key, so LitFoundry treats the key as required; send it as an `Authorization: Bearer` header. Usage is metered in dollars: a free key includes $1 of usage per day (reset at midnight UTC), search calls cost more than list/filter calls (at the time of writing $1 versus $0.10 per 1,000 calls), and each response reports its cost in the `X-RateLimit-Credits-Used` header. Verify current terms before release. The key is a source credential like any other (shared default plus personal override). Record the cost of every call, show the estimated number of calls before a search runs (pages × sub-queries), and enforce a configurable daily budget per key (`SOURCE_BUDGET_EXCEEDED`) so one user cannot exhaust a shared key.

**Scopus:** v1 imports Scopus CSV, BibTeX and RIS exports (include cited references in the export for co-citation and coupling). The query compiler still generates the Scopus query so users can run it in Scopus's own interface before exporting. The Scopus Search API adapter is SHOULD (Section 0.2); access depends on Elsevier API entitlement and export policies. pybliometrics keeps its API keys (`pybliometrics.cfg` or `init()`) and its response cache (under the user's home directory by default) process-wide, so the adapter must either run each Scopus job in its own subprocess with its own configuration and a cache under the project's `temp/`, or call the Scopus REST API directly. Abstracts and references through the API depend on the institution's entitlement level.

**Web of Science:** v1 uses the **Web of Science Starter API** (`GET https://api.clarivate.com/apis/wos-starter/v1/documents` with `db=WOS`, key in the `X-ApiKey` header, `limit` up to 50 records per page, page-number paging). Daily quotas depend on the key's plan (at the time of writing: Free Trial 50 requests/day without times-cited data; Institutional Member 5,000/day; Institutional Integration 20,000/day; verify current terms); record calls per key and apply the same budget mechanism as OpenAlex. Starter returns basic metadata only: UT, identifiers (DOI, ISSN, PMID), title, document type, source details, authors, author keywords and times cited. It returns **no abstracts, cited references, Keywords Plus or author addresses**. Therefore: (1) enrich Starter records by DOI from OpenAlex using batched DOI filter requests, keeping field-level provenance so enriched fields are attributed to OpenAlex; (2) flag records that still lack an abstract in the screening queue; (3) analyses that need references, affiliations or countries use WoS export files or other sources and report coverage. If the API cannot page through all `reported_count` results, mark the run `partial`. The **API Expanded** adapter (full records) is SHOULD (Section 0.2); never use the retired Lite API. Support official WoS export formats (plain text, BibTeX, tab-delimited) with validation; export files remain the route to full records with cited references.

**Manual import:** Upload `.bib`, `.ris`, `.csv`, documented WoS `.txt`, and OpenAlex JSON. Validate file format, sizes, encoding, duplicates, content security and schema; identify source and import event. Imports create provenance-preserving source runs and participate in PRISMA counts. Treat licensed record files as restricted when exporting.

Every source run saves `reported_count`, `retrieved_count`, `completeness` (`complete|partial`), status, `error_code`, `started_at`/`ended_at`, identifiers, `missing_required_fields_count`, `checksum` and the exact executed request (`executed_request_json`). API counts are **not** evidence that all records were actually retrieved. Users may choose a corpus only with an explicit acknowledgement if any source run is partial.

## 9. Background jobs and process safety

Place queue metadata in `catalog.sqlite` so idle workers can find jobs without scanning every project DB. Run a **separate worker process**, not Flask request threads. On startup, reclaim expired leases and idempotently retry/reconcile jobs. Jobs support `queued`, `running`, `partial`, `completed`, `failed`, `cancelling`, `cancelled`, have user/project identity, structured progress and log correlation ID. Use lease expiration/heartbeat, job idempotency keys (`jobs.idempotency_key`) and bounded retries. A job may be cancelled at checkpoints, not by corrupting an open database transaction.

Background jobs that write to a project declare a write scope in `jobs.scope_json`: `append` (adds new rows only, e.g. a search import), `records` (a listed set of work IDs, e.g. a dedup merge or bulk screening update) or `project` (whole-project operations such as migration). At most one `records` or `project` job holds a project's write lease at a time; `append` jobs can run alongside it. Interactive single-record edits (screening decisions, record edits) do not take the lease: they use short transactions and optimistic concurrency, and return `409 RECORD_LOCKED` when they touch a work held by a running `records` job, or `409 PROJECT_BUSY` during a `project` job. Every job write is a checkpoint at which the job honours cancellation and the backup write barrier (Section 16.3). Read-only analyses should run on consistent snapshots and can be parallelised within CPU/memory limits. Use WAL, `PRAGMA foreign_keys=ON`, busy timeouts, short transactions, bounded thread-safe SQLAlchemy sessions, explicit SQLite backup API for live snapshots. Avoid writing to project DB concurrently from arbitrary background threads. Enforce per-user and global concurrency and quota budgets. Return `202` with a job ID for nontrivial operations; Vue polls `/jobs/{id}` (2–5s, slower in background tabs).

## 10. Normalisation and deduplication

Raw source records are append-only. Canonical `works` keep title, abstract, dates, DOI, language, document type, journal, authors, affiliations, keywords, source-specific citations, and cited references. Preserve **field-level provenance**, conflicts and retrieval date. Never sum Scopus/WoS/OpenAlex citation counts as if unique; display them with source/date and clearly label derived summaries.

Dedup stages: normalized DOI; other persistent IDs; normalized exact title with year/authors; fuzzy candidate matching with RapidFuzz using blocking keys (for example publication year ± 1 and normalised title prefixes or n-grams), never all-pairs comparison, so 50,000 records stay within the job budget; manual review of uncertain cases. Different conference and journal versions may be distinct. Provide compare/merge/reject/undo UI and auditable merge events. Mark work-to-source membership to calculate source overlap and PRISMA removal counts accurately. A merge must not destroy original raw records or historical review decisions, and never deletes `works` rows (see `works.merged_into_work_id`), so frozen corpora stay resolvable.

## 11. Full PRISMA screening

- Support review protocols with research questions, inclusion/exclusion criteria, review type, scope dates, databases and search dates. Preserve immutable protocol versions.
- Identification uses source-run provenance and reports source-specific retrieved records, removed duplicates and additional identified records.
- Title/abstract stage includes `include`, `exclude`, `uncertain`, notes and structured reason codes; configurable single or dual independent reviewers and adjudication. Decisions are independent reviewer events; conflicts require a resolution record.
- Eligibility includes status of reports sought, retrieved/unavailable, full text reviewed and explicit reason(s) for exclusion. Works, reports and studies are different entities; don't assume 1:1 for every study.
- Support PDFs/attachments uploaded by authorised users with storage limits and validated MIME/content. Application does not circumvent paywalls; an external link may be stored instead.
- Frozen corpus contains an immutable set of included work/study IDs, inputs, review protocol, full screening-resolution ledger and SHA-256 for reproducibility. Later edits create a new version; completed analyses refer to the original snapshot.
- PRISMA count engine derives counts from recorded events and stages. Allow manual corrections only as separately recorded, justified adjustments. Validate conservation/reconciliation before diagram generation. If no full-text screening was conducted, do not fabricate that stage or claim full systematic-review compliance.
- Use `prisma-flow` to generate SVG/JSON/PNG (when available), plus machine-readable exclusion table. Distinguish PRISMA 2020 guideline from bibliography mapping, and provide disclosure text in reports.
- Optional ASReview interoperability (SHOULD, Section 0.2): export deduplicated screening input CSV, import labelled results with work IDs and reviewer provenance, require human adjudication. Do not imply AI prioritisation guarantees complete recall.

## 12. Bibliometrics, analytical provenance and reports

Primary engine: **Biblium**, integrated through an internal `BibliometricsEngine` adapter. Validate engine capabilities at runtime, pin version, and provide tested pandas/NetworkX fallback for essential calculations. Do not call undocumented Biblium interfaces without a smoke test. Make optional PyBibX and BibFusion connectors replaceable and licence-gated.

Analyses (MUST unless marked; see Section 0.2):

1. Annual publication counts and trends.
2. Productive authors, journals/sources, institutions and countries.
3. Citation rankings with source/date, citations per year and coverage warnings.
4. Coauthorship collaboration networks.
5. Keyword frequency and co-occurrence networks.
6. Co-citation network (only when cited references are available). *SHOULD.*
7. Bibliographic coupling (only when cited references are available). *SHOULD.*
8. Topic clusters and temporal keyword/thematic evolution. *MAY; needs its own specification before implementation.*
9. Source/database overlap and metadata completeness.
10. Research maturity review table using optional human-labelled validation categories (theoretical, simulation, historic data, pilot, industrial advisory, closed-loop, sustained industrial use). These are annotations, **not** conclusions that can be inferred automatically from counts. *SHOULD.*

Expose thresholds, normalization, network type, similarity measure, clustering parameters, time slicing, keyword dictionary version and graph size. Explicitly fail or warn if prerequisite fields are absent. Outputs include paginated tables, interactive graphs (zoom/filter/hover/select), SVG/PNG/CSV/JSON export, and a versioned HTML report with methods, sources, limitations and methodological notes. Never treat citation counts as direct quality scores. Every artifact records corpus hash, parameters, engine/software versions, timestamp, creator and file checksum.

## 13. Frontend information architecture

- **Setup/Login:** gated fixed-`admin` bootstrap page; sign-in form with username and password, plus a `LitFoundry account` / `Active Directory` selector shown only when AD is enabled; local password change only for local users; login/logout.
- **Home:** owned projects, shared-with-me projects, all registered-visible projects (the admin sees every project), filters, cards/tables, create button, recent jobs.
- **New project wizard:** title, aims, keywords, date/document types, selected sources, review mode.
- **Project workspace tabs:** Overview; Search strategy; Source queries; Search history/results; Normalise & duplicates; Protocol; Screen titles/abstracts; Full-text eligibility; PRISMA; Bibliometrics; Reports; Files; Sharing; History/settings.
- **Search editor:** draggable/editable Boolean groups; enabled sources as switches; generated/override query panels; warnings/test counts; dry-run and execute; validation/credential status.
- **Records:** server-paginated filterable table, record detail drawer, per-source provenance, citations, reference lists, source overlaps.
- **Dedup:** side-by-side candidate pairs and confidence reasons; accept/reject/undo; bulk safe-actions.
- **Screening:** keyboard shortcuts; independent reviewer decisions and reconciliation; exclusion reasons; progress and per-stage counts; full-text availability and attachments.
- **PRISMA:** stages/counts, validation diagnostics, preview SVG, download.
- **Bibliometrics:** corpus selector, parameter form, dashboard and graph view, sortable tables, downloaded artifacts.
- **Sharing:** (owner and admin) private/public-view/public-edit selector with warning, explicit ACL editor with user lookup; audit feed and permission preview.
- **Export:** ZIP export job with progress and authenticated download.
- **Admin:** user creation (local or pre-provisioned AD), password resets, session revocation and ownership transfer; optional AD connection configuration and connection test; shared API keys, status and usage; hostname/proxy information; scheduled full-backup configuration/status/history/manual trigger/retention (SHOULD; v1 backups are CLI-only); migration and restore status (execution is CLI-only, Section 18.1); logs/job health and audit feed (no secret values displayed).
- **About:** product name, tagline, version, licence and the administrator trust disclosure (Section 1, decision 9).

Use the Vue 3 Composition API with the runtime-only build: each component is an ES module whose `setup()` returns a render function built with `h()` (Section 2); no `template` option, in-DOM templates or `.vue` files. Axios instance uses same-origin `/api/v1`, credentials, CSRF interceptor, typed API error conversion. Client routing uses the in-house History-API router module with a server SPA fallback. Server-side pagination/filtering for larger corpora (e.g. 50,000+ works). Include keyboard navigation, accessibility labels, responsive layout, job progress, loading/retry/error/empty states and confirmation for destructive actions. Never render untrusted bibliographic HTML: setting `innerHTML` for metadata is prohibited; pass metadata as text children of `h()`.

## 14. REST API contract

All routes begin `/api/v1`, return JSON except protected binary downloads, use UUIDs, structured error codes, UTC ISO-8601 times, pagination and `If-Match` for conflicts. Version schemas with OpenAPI and request/response models (Marshmallow/Pydantic or explicit equivalent) without replacing Flask/SQLAlchemy.

| Method | Path | Purpose |
|---|---|---|
| GET | `/setup/status` | Whether admin setup required; no secrets |
| POST | `/setup/admin` | One-time admin bootstrap, local bootstrap token required |
| GET | `/auth/methods` | Available sign-in methods (whether AD is enabled); no secrets |
| POST | `/auth/login`, `/auth/refresh`, `/auth/logout` | JWT-cookie session operations |
| GET | `/auth/me` | User UUID, provider, role and permissions |
| PUT | `/auth/password` | Change own local password and revoke other sessions |
| GET,POST | `/admin/users` | Admin list/create local or AD-bound users |
| PATCH | `/admin/users/{user_id}` | Update display name or contact email; enable/disable; convert account type |
| POST | `/admin/users/{user_id}/reset-password` | Reset a local user's password (forced change at next sign-in) |
| POST | `/admin/users/{user_id}/revoke-sessions` | Revoke all of the user's sessions |
| POST | `/admin/users/{user_id}/transfer-projects` | Transfer ownership of the user's projects to another user |
| GET,PUT | `/admin/auth-settings` | Password policy, session lifetimes, throttling |
| GET,PUT,DELETE | `/admin/ad-directory` | View, configure, enable/disable or remove the single AD connection; secret fields write-only |
| POST | `/admin/ad-directory/test` | LDAPS/StartTLS connectivity, certificate and service-account test |
| POST | `/admin/ad-directory/resolve-user` | Look up an AD account for pre-provisioning |
| GET | `/admin/audit-events` | System audit feed (filterable, paginated) |
| GET,PUT | `/admin/source-credentials/{provider}` | Shared source credentials, status and usage |
| GET,PUT | `/me/source-credentials/{provider}` | Personal overrides/status |
| GET | `/users/lookup` | Minimal user search (display name, username) for sharing dialogs; rate-limited |
| GET,POST | `/projects` | List authorised projects / create |
| GET,PATCH,DELETE | `/projects/{project_id}` | View/update/delete (two-stage, Section 4.3) |
| POST | `/projects/{project_id}/archive`, `/projects/{project_id}/unarchive` | Archive or unarchive (owner or admin) |
| POST | `/projects/{project_id}/transfer-ownership` | Transfer ownership (owner or admin) |
| GET,PUT | `/projects/{project_id}/sharing` | Public mode and per-account ACL |
| GET | `/projects/{project_id}/audit-events` | Project change log |
| GET,POST | `/projects/{project_id}/protocols` | Protocol revisions |
| GET,PUT | `/projects/{project_id}/search-strategy` | Keyword/group current draft |
| POST | `/projects/{project_id}/queries/preview` | Per-source compilations, warnings, estimated API calls |
| GET,POST | `/projects/{project_id}/search-runs` | History / launch async search |
| GET | `/projects/{project_id}/search-runs/{run_id}` | Status/count/completeness |
| POST | `/projects/{project_id}/source-imports` | Source file upload + background import |
| GET | `/projects/{project_id}/records` | Search/sort/filter/paginate |
| GET | `/projects/{project_id}/records/{record_id}` | Detail/source provenance |
| GET | `/projects/{project_id}/duplicates` | Candidate queue |
| POST | `/projects/{project_id}/duplicates/decisions` | Merge/reject/undo |
| GET,PUT | `/projects/{project_id}/keyword-rules` | Keyword normalisation rules |
| GET,POST | `/projects/{project_id}/screening/decisions` | Retrieve/add reviewer decisions |
| POST | `/projects/{project_id}/screening/resolutions` | Final arbitration |
| GET,POST | `/projects/{project_id}/screening/asreview` | Export ASReview input CSV / import labelled results |
| GET,POST | `/projects/{project_id}/retrieval-attempts` | Record report retrieval outcomes |
| GET,POST | `/projects/{project_id}/studies` | Study groups and work links |
| GET,POST | `/projects/{project_id}/attachments` | List / upload full-text reports securely |
| GET,DELETE | `/projects/{project_id}/attachments/{attachment_id}` | Authorised download / delete |
| GET,POST | `/projects/{project_id}/corpora` | List/freeze corpus versions |
| GET | `/projects/{project_id}/prisma/{corpus_id}` | Validated counts/stages |
| POST | `/projects/{project_id}/prisma/{corpus_id}/adjustments` | Record a justified manual count adjustment |
| POST | `/projects/{project_id}/prisma/{corpus_id}/export` | Generate SVG/JSON |
| GET,POST | `/projects/{project_id}/analyses` | List/start analyses |
| GET | `/projects/{project_id}/analyses/{analysis_id}` | Analysis status/config/results |
| POST | `/projects/{project_id}/reports` | Generate a versioned HTML report |
| GET | `/projects/{project_id}/artifacts` | List artifacts |
| GET | `/projects/{project_id}/artifacts/{artifact_id}` | Authorised artifact retrieval |
| GET,POST | `/projects/{project_id}/exports` | Export history / enqueue ZIP export |
| GET | `/projects/{project_id}/exports/{export_id}/download` | Secure ZIP download |
| POST | `/project-imports` | Import a previously exported project ZIP as a new private project owned by the caller |
| GET | `/jobs` | Caller's recent jobs (admin: all jobs) |
| GET | `/jobs/{job_id}` | Progress/state/log summary |
| POST | `/jobs/{job_id}/cancel` | Idempotent cancellation |
| GET | `/health/live` | Minimal unauthenticated liveness |
| GET | `/health/ready` | Admin-only detailed readiness |
| GET,PUT | `/admin/backups/settings` | Admin view/configure schedule, server-side destination and retention |
| POST | `/admin/backups/test-destination` | Check destination permissions, free space and reachability with a probe file; never reads other files |
| GET,POST | `/admin/backups/runs` | History (size, file name, validation, failure status) / enqueue an on-demand full backup |
| POST | `/admin/backups/runs/{run_id}/verify` | Verify ZIP integrity, manifest checksums and SQLite integrity in temporary staging; no live changes |
| GET | `/admin/backups/runs/{run_id}/manifest` | Download the archive manifest |
| POST | `/admin/backups/runs/{run_id}/restore-check` | Dry-run restore validation; no live changes |
| POST | `/admin/backups/prune` | Preview (`dry_run=true`) or apply retention pruning |

The `/admin/backups/*` endpoints and `/projects/{project_id}/screening/asreview` are SHOULD (Section 0.2). For a long job: `POST` returns `202 Accepted` with `{job_id,status,links:{status}}`. Standard errors include `VALIDATION_ERROR`, `UNAUTHENTICATED`, `FORBIDDEN`, `CONFLICT`, `RECORD_LOCKED`, `PROJECT_BUSY`, `MAINTENANCE_IN_PROGRESS`, `AUTH_PROVIDER_DISABLED`, `DIRECTORY_UNAVAILABLE`, `AD_IDENTITY_AMBIGUOUS` (admin configuration only), `SOURCE_ACCESS_DENIED`, `SOURCE_RATE_LIMITED`, `SOURCE_BUDGET_EXCEEDED`, `SOURCE_PARTIAL`, `JOB_FAILED`, `BACKUP_DESTINATION_UNAVAILABLE`, `BACKUP_VALIDATION_FAILED`, `EXPORT_RESTRICTED`; include stable `request_id` and no stacktrace/private key.

## 15. Export/import and archival

### Complete ZIP export

The owner or admin requests export; create a consistent database snapshot through SQLite backup API after coordinating writers (never raw-copy an open SQLite/WAL file), freeze artifact inventory, calculate SHA-256 hashes, and ZIP **only** the selected project's data. Include `manifest.json`, `project.sqlite`, `sources`, `imports`, `attachments`, `reports`, `figures`, `metadata/provenance.json`, `metadata/checksums.json` and licence/reuse notice. Exclude source credentials, admin/user catalogue, JWTs, OS secrets, private runtime logs, caches, temp files and unrelated projects. Use the canonical `litfoundry_project_<project_uuid>_<YYYYMMDD_HHMMSSZ>.zip` download name and include `product`/`product_name` branding in the manifest. Provide export history, timestamp, archive format version, schema version and source-analysis provenance. Do not mutate the live project or store absolute machine paths in the archive. Enforce export permission (owner or admin) again on download; avoid unauthenticated permanent URLs. Export ZIPs in `exports/` expire after a configurable period (default 7 days) and are then deleted by housekeeping; they are not included in full backups.

### Import/restore

Treat ZIP as untrusted: validate size and file count, entry types, path traversal, symlinks, compression bombs and manifest/checksums. Stage extraction in a quota-limited temporary directory, migrate included `project.sqlite` if needed (reject archives whose schema is newer than this installation supports), rekey the **project UUID** and make the importing account the owner, keep reviewer and actor IDs unchanged (a `project_people` row whose ID matches no account on this installation is marked `origin=imported` and kept as non-login provenance), reset ACL/public visibility to private, clear job leases and never import credentials. Atomically register the new project in the central catalogue. Preserve original provenance IDs in explicit imported-from fields; do not overwrite existing projects. Include import/export roundtrip tests. Export licensed-source raw records only with an explicit rights warning; offer metadata-only export if contractual terms require it.

## 16. Administrator-managed scheduled full-installation backups

**Scope and distinction:** Project ZIP exports in Section 15 remain single-project portability files controlled by the owner or admin. This section specifies an entirely separate **administrative full-system backup** of the central catalogue, **every project folder/database regardless of sharing permission**, stored secrets and all persistent installation data needed for disaster recovery. Backups are privileged snapshots, not public downloads and not project exports.

**Backups are not encrypted.** A full backup contains every project, the catalogue and the secrets needed for a seamless restore: the secret-store master key with the encrypted source API keys and AD service-account password, and the session signing key. Anyone who can read a backup file can read everything in the installation. The destination must therefore be restricted by OS or share permissions to the LitFoundry service identity and the administrators who need it, and the admin UI says so next to the destination field. This follows the trust model in Section 1, decision 9.

**Release scope (Section 0.2):** v1 requires manual full backups from the CLI (`litfoundry backups create --destination PATH`, `backups verify`, `backups list`): the snapshot and packaging algorithm (16.3), verification, and the restore workflow (16.5). The CLI applies the destination rules of 16.1 (an absolute path outside `<data_root>`). Scheduling (16.2), the admin settings and screens (16.1), retention and rotation (16.4) and the `/admin/backups/*` endpoints are SHOULD.

### 16.1 Configurable schedule and destination

Admin → Backups must provide all controls below; no non-admin API or UI is permitted to change them.

| Setting | Type / validation | Default or rule |
|---|---|---|
| `enabled` | Boolean | Disabled until an admin configures and successfully tests a destination |
| `frequency` | `daily`, `weekly`, `monthly` | Propose daily; prevent unsupported/invalid recurrences |
| `local_time_hhmm` | `HH:MM`, 24-hour | Admin-selected time, e.g. `23:00` |
| `iana_timezone` | IANA identifier, e.g. `Africa/Johannesburg` | Server's detected timezone, display explicitly |
| `weekday` / `monthday` | When required by frequency | Valid weekday or 1–28 day-of-month to avoid ambiguous skips |
| `destination_server_path` | Absolute **server-side** folder path, supports Windows UNC (`\\server\share\folder`) and mounted Linux/macOS directories | No default. Must be outside `<data_root>` and not equal to or beneath staging, temp or export paths |
| `retain_count` | Integer ≥ 1, maximum number of **verified successful** full-system backups kept in the current series | Suggest 7 as first-run value |
| `include_logs` | Boolean | On by default for complete operational recovery; secrets and tokens are redacted in logs |

Server machine OS permissions determine writable paths. A browser folder chooser cannot pick a server filesystem location reliably: provide a text path field plus **Test destination**; show resolved server path, status, free space when available and last successful write test. Test destination writes and deletes a uniquely named probe file and never reads or lists unrelated files. Do not accept upload paths, arbitrary URL schemes or destinations inside `<data_root>`. For Windows Services prefer UNC shares over mapped drive letters; document service identity and SMB permissions. For Linux/macOS mounted volumes document path availability after reboot and credentials. A network share **may store ZIP backups** even though live SQLite files must remain on local disk. Prevent backup loops by excluding previous backups, backup staging, imported archives, project export ZIPs and temp files from archive inputs.

Illustrative administrator settings payload (all properties validated):

```json
{
  "enabled": true,
  "frequency": "daily",
  "local_time_hhmm": "23:00",
  "iana_timezone": "Africa/Johannesburg",
  "destination_server_path": "/mnt/secure-backups/litfoundry",
  "retain_count": 7,
  "include_logs": true
}
```

For Windows, use a native absolute path or UNC share; do not interpret the example Linux path as mandatory. Explicit schedule edits reset/recalculate the next due occurrence and record policy revision. Changing the destination assigns a new `series_id`.

Date/time filenames must be safe across Windows, Linux and macOS and include a collision-resistant suffix:

`litfoundry_full_YYYYMMDD_HHMMSSZ_<run_uuid_short>.zip`

For example `litfoundry_full_20261019_230000Z_a94fc21e.zip`; the timestamp is **UTC** and must match `manifest.json`. Store human-readable local schedule and UTC execution time in the run record. Never place `:` in filenames.

### 16.2 Scheduling engine and duplicate-run prevention

Use a built-in scheduler coordinator in a **single elected worker/supervisor process** (or a vetted scheduler such as APScheduler wrapped by an application-owned lease). Persist the recurrence definition and `next_due_at_utc`/`last_attempted_at_utc` in `backup_settings`. Never register a recurring job separately in each web-server thread or each `litfoundry worker` process.

At each due time, atomically acquire an expiring/fenced global `full-backup` lease in `catalog.sqlite`; create one `backup_runs` entry with a unique `occurrence_key` for that schedule occurrence and enqueue a `system_full_backup` job. The occurrence key prevents duplicate backups after service restart, clock adjustment or multiple worker processes. Scheduled backups execute with the **system service identity**, even if no administrator is logged in; the authenticated admin identity is only required for configuration and manual requests. Do not put secrets in job arguments or logs.

Define missed-run behavior: after downtime, trigger **at most one** overdue backup at service restart (configurable grace), advance next due time, and show skipped occurrences in the admin log; no uncontrolled catch-up burst. Handle daylight saving time gaps/duplicates deterministically (run once for a due local day, record computed UTC). Enforce one full backup at a time; prevent simultaneous schema migration, full restore and competing maintenance operations.

### 16.3 Consistent full snapshot and ZIP creation algorithm

A full backup must be consistent across the **central catalogue, all per-project SQLite databases and their file trees**. A Python `shutil.copyfile()` of a live WAL-mode `.sqlite` file is **not acceptable**; use `sqlite3.Connection.backup()` for each database.

**Precondition: write-once project files.** Every persistent project file (raw source payloads, imports, attachments, figures, reports, artifacts) is written to a temporary name, flushed, atomically renamed into place and never modified afterwards. Files are removed only by housekeeping (trash purge, export expiry), which does not run while a backup holds the `full-backup` lease. Because files never change in place, they can be copied after the write barrier is released.

1. **Inventory.** Allocate the run ID and list the projects to include. `ready` and `archived` projects are included; `quarantined` projects are included as raw file copies and flagged in the manifest; `provisioning` projects and projects in trash are excluded; a project in `error` fails the backup until the admin repairs or quarantines it. Verify path containment. Record running jobs and schema/app versions.
2. **Write barrier.** Set the global `write-barrier` lease in `system_leases` to `draining`. Every process checks the barrier before starting an application-data write unit (a mutating web request, a job write checkpoint, an upload commit) and registers each unit in `active_writers`. New write units wait briefly, then fail with `503 MAINTENANCE_IN_PROGRESS` and `Retry-After`. Background jobs pause at their next write checkpoint; network retrieval may continue, buffering to the job's temp area up to a limit. Jobs are not required to finish. When `active_writers` is empty the barrier becomes `frozen`; if it does not drain within the configured timeout, fail safely without pruning previous backups.
   - **Exempt operational writes:** the barrier protects application data only. These stay writable throughout: `jobs` lease/heartbeat/progress fields, `refresh_tokens`, `login_throttle`, `audit_events`, `users.last_login_at`, `system_leases`, `active_writers` and `backup_runs`. The backup captures whatever state they had at snapshot time, and restore resets them (Section 16.5).
3. **Snapshot under the barrier.** Copy `catalog.sqlite` and every included `project.sqlite` into staging with the SQLite online backup API, and record each project's file inventory (relative path and size). Then release the barrier and let paused jobs resume. Keep this step short: no hashing or file copying happens under the barrier.
4. **After release.** Run `PRAGMA integrity_check` and `PRAGMA foreign_key_check` on the snapshots. Copy the inventoried project files into staging and hash them (they cannot have changed; a missing inventoried file fails the run). Copy `secret_material/`, administrative non-secret configuration and, if enabled, logs. Do not include TLS private keys or Caddy CA keys; document reconfiguring certificates and hostname on a new host.
5. **Portable secrets.** Secrets are encrypted at rest in the catalogue with a master key stored as a file in `secret_material/`, protected by OS permissions and not bound to Windows DPAPI or a macOS/Linux keychain, so a backup restores on a different machine without extra steps.
6. **Manifest.** Create `manifest.json` with `product="litfoundry"`, `product_name="LitFoundry"`, format version, run ID, series ID, source hostname, app version, snapshot start/finish UTC times, catalogue/project schema versions, all project UUIDs, relative paths and states (including quarantine flags), inventory sizes, SHA-256 checksums for every included file, and a statement that the archive contains secrets. Include `backup_metadata/checksums.json`, `backup_metadata/configuration.json` (non-secret metadata), audit provenance and a restore README. Archive entries use relative safe paths only.
7. **Package and verify.** Build the ZIP with the standard-library `zipfile` module (ZIP64 enabled, deflate) outside any input path. Write it first to a `.partial` file **in the target directory** (or a controlled local staging destination if network share limitations require), flush and close it, reopen it, check every entry's CRC (`testzip()`) and compare entry checksums with the manifest. Compute the final ZIP SHA-256, rename to the final `.zip` on the destination filesystem when possible, verify existence/readability and log size/checksum. Mark the run `completed` only after verification. Remove stale `.partial` files in a separate housekeeping pass.
8. **Clean up.** Delete staging copies (best-effort deletion; document SSD/filesystem secure-deletion limitations), keep staging beneath an OS-protected directory with restricted permissions, and check free disk space before starting. If archive content includes Scopus/WoS records with redistribution limits, show the admin a compliance warning; a disaster-recovery backup is not permission to publish or redistribute.

If a required database or inventoried file is missing, damaged or unreadable, **fail the backup** rather than silently omitting it, record a redacted error and alert the admin in the application (optional email notifications are a future enhancement). A project whose database is damaged can be **quarantined** by the admin (`state=quarantined`): it becomes unavailable to users, and later backups include its files as raw copies flagged in the manifest instead of failing, so one broken project cannot block every backup. Preserve all prior valid backups. Track storage consumption and avoid unbounded temp data.

### 16.4 Retention, rotation and failure handling

- Rotate backups only **after** a new full backup is successfully created, verified and committed as `completed`. If the new job fails at any point, do not delete any older backups.
- Retain the most recent `retain_count` verified successful archives of the current `series_id`; sort by UTC run timestamp, not filename lexical quirks. Delete older archives only if they match `backup_runs` and the manifest's run ID and series ID. Never delete unrelated `.zip` files or files in subdirectories.
- If retention is lowered by admin, preview the count and affected managed archives. Defer deletion until the next successful run or a separately confirmed **Prune now** operation that first checks existing good archives. Failed/partial archives do not count towards successful backup retention; clean orphan `.partial` files under a separate age threshold after confirming no run owns them.
- On destination/share unavailable, full disk, timeout, write-barrier timeout, consistency check failure or corrupt archive, set `failed`, preserve older backups, publish an admin-visible warning on the dashboard and status endpoint, and retry only according to the configured bounded policy. Do not claim success before final verification.
- A destination change begins a new retention series; never automatically delete backups from an old destination. Changing retention requires administrator authorisation and creates an audit event. Never delete the only valid restore point unless an admin explicitly confirms a recovery-impact warning.
- After a restore, `backup_runs` reflects the restored point in time. The next backup run rescans the destination and re-registers managed archives by manifest run ID and series ID, so archives created after the restored snapshot are still covered by retention.
- Record last attempt, last success, next due, duration, archive bytes, number of projects, checksum and error summary in Admin → Backups. Offer **Run backup now**, **Test destination**, **Verify backup**, **Download manifest** and a guarded **Prune now**. Non-admin users must not learn filesystem paths, backup inventory or system data.

### 16.5 Restore and disaster-recovery workflow

Implement the host-side `litfoundry backups list|verify|create`, `litfoundry restore --archive PATH --dry-run` and `litfoundry restore --archive PATH --confirm` commands (Section 18.1), plus an admin GUI to inspect, verify and dry-run. **Do not allow a web POST to replace live databases during normal Flask operation**; the actual restore runs in an exclusive offline/maintenance process with a human confirmation and an application outage warning.

Restore steps: (1) stop/pause Waitress, worker(s), backup scheduler and any live writers; (2) verify ZIP integrity, the full checksum manifest, expected schema versions, path safety and decompression quotas; (3) stage extracted data outside the live data root; (4) check SQLite `PRAGMA integrity_check`, foreign keys and catalogue-to-project directory consistency; (5) optionally migrate copies using the supported migration coordinator; (6) create a safety backup of the existing data root; (7) atomically move staged installation data into place where the filesystem permits, otherwise use an explicitly rollback-capable staged replacement; (8) restore `secret_material/`, rotate the session signing key so everyone signs in again, clear job leases and hold restored queued jobs for admin review (no immediate uncontrolled reruns), mark restored `running` backup runs as `failed`, update host-specific Caddy/CA paths as necessary and restart; (9) run post-restore smoke checks before accepting new writes. If any verification fails, preserve the original installation. Do not overwrite data during `--dry-run`.

Document restore-to-same-machine and restore-to-new-machine steps for Windows, Linux and macOS. Test with at least two users, an AD configuration, multiple projects, original data files, shared API credentials and pending jobs. Clearly state that source API entitlements, organisation CA trust and AD connectivity depend on the new environment. Provide an admin-run quarterly restore-test reminder/status (no background notification required).

### 16.6 Backup test and acceptance matrix

In v1, run these tests against CLI-created backups; the scheduling, retention and admin-screen tests are written when those SHOULD features are built.

- Enabling backups without a tested destination, a positive retention count or a valid recurrence/timezone is rejected.
- Non-admin users cannot read/change backup settings, trigger full backup, see destination/path, view audit logs or perform restore by guessing API endpoints.
- Run a backup while another user edits a project, writes an attachment and a search worker adds records: snapshot reconciliation and `integrity_check` pass without a missing/mixed project manifest; the search job pauses at a checkpoint and resumes; job heartbeats and token refresh continue during the barrier.
- Backup catalogue and every project folder/database are present, including disabled-user, archived and private projects. Auth settings, AD configuration, identity bindings and secret material are restorable.
- A quarantined project does not block backups; a damaged project that is not quarantined fails the backup with a clear admin error.
- With scheduled daily/weekly/monthly mode, demonstrate due-time calculation, restart recovery, DST behavior, exactly-once occurrence and no duplicate run with two worker processes.
- Verify filename pattern and UTC timestamp against run metadata; test Windows UNC, Linux mount, macOS directory and unavailable destination with mocks/on-host fixtures.
- With `retain_count=3`, four successful backups leave three; a subsequent failed backup leaves the same three; unrelated ZIPs remain untouched; moving the destination does not prune the old destination; archives created after a restored snapshot are re-registered and pruned correctly.
- Deliberately corrupt an archive, project database or manifest: verification fails, no backup is marked completed, retention does not run, live data unchanged.
- A full backup can be restored on a different OS host in test fixtures; login methods, users, ACLs, per-project DBs, search data and reports persist, stored credentials work after restore, and every user must sign in again.
- Automated integration tests cover backup locking, staging cleanup, pruning idempotency, interrupted `.partial` recovery, interrupted restore rollback, and that secrets appear only in the secret-store files (never in logs, configuration metadata or the manifest).

## 17. Operational and security controls

- TLS on LAN, firewall restricted to trusted subnets, stable hostname and trusted CA. `Secure`, `HttpOnly`, `SameSite` cookies; CSRF on unsafe HTTP methods. Never run LAN production with Flask debug server or HTTP-only authentication.
- Restrict forwarded headers to configured reverse proxy; allowed-host and origin checks; CSP, clickjacking controls, MIME type headers, HTTPS-only redirect and no credentials in URL.
- Built-in local `admin` account; always-available local username/password sign-in; optional single-domain AD with a required service account, LDAPS/StartTLS verification and SID binding; Argon2id; strong bootstrap; per-IP and per-identifier throttling (never locking out `admin`); admin-only account creation; session invalidation; logout; audit of privilege changes.
- Encryption at rest of stored secrets (source API keys, AD service-account password) with a master key file in `secret_material/`, which also holds the session signing key: portable, OS-permission protected, included in full backups and never in project exports. The effective credential is the job requester's override, then the shared one; never another user's personal secret.
- Strict file upload/download authorisation; MIME and signature validation, size quotas, path containment, safe ZIP import. Optionally scan uploaded full-text files per organisation policy.
- External HTTP only to approved bibliographic API domains. TLS verification on outbound requests; retry timeouts. No arbitrary URLs, server-side HTML fetching or open redirects.
- No SQLite in cloud sync folders or direct network filesystems. System-wide full ZIP backups (manual from the CLI in v1; scheduled backups are SHOULD) of all databases, persistent files and secrets, under a global write barrier with SQLite online snapshots. Backups are unencrypted, so the destination must be restricted to the service identity and administrators. Admin-only destination/schedule/retention settings, verified completion before rotation, and tested cross-platform offline restore; see Section 16.
- Logs use request/job/project IDs and structured safe summaries; redact secrets, auth tokens, raw full-text and search API credentials. Admin health endpoint requires authentication.
- Capacity budgets and quotas (projects/user, API calls, storage, archive size, jobs/user, workers). Configurable defaults with documented safe values.
- Handle process termination and machine reboot: leases expire, recover partial jobs, no phantom success, no orphaned catalogue entries; bounded data corruption risk.
- Restrictive data-root permissions at install: on Windows an explicit ACL for the service identity and Administrators with inheritance disabled; on Linux/macOS a dedicated service user and mode `0700`.
- Security notes state the trust model: the admin can see and change everything (in the app, on the host and in backups). Project isolation protects users from each other, not from the admin or a compromised service identity. Document what personal data is stored (account names, contact emails, reviewer decisions, audit trails).

## 18. Packaging and distribution

Development: `python -m venv`, `pip install -e .[dev]`, `litfoundry init`, `litfoundry serve`, `litfoundry worker`, CLI for migration, secure directory lookup tests, backup, and offline restore. Use `pyproject.toml` with the `litfoundry` console-script entry point and environment-driven `LITFOUNDRY_` configuration with sample `.env.example`; secret keys are **not** in `.env.example` or source control.

Release: package and sign distributions as **LitFoundry**, with executable/launcher name `litfoundry` and a single OS service `litfoundry` that supervises the `litfoundry-server` and `litfoundry-worker` processes. v1 ships a PyInstaller `onedir` package with a Windows Service install for **Windows x86_64**. Linux x86_64 and macOS arm64/x86_64 packages with systemd and launchd services are SHOULD (Section 0.2); until then those platforms run from a venv, and CI runs the full test suite on all three. Build separately on each OS; do not assume cross-compile. Distribute launcher + Waitress/Flask + worker + static UI assets + migration scripts + licence inventory. Code signing/notarisation is strongly recommended for organisational deployment. Configure local data root outside immutable binaries (Windows `%PROGRAMDATA%\LitFoundry` or user app data for non-service mode; Linux `/var/lib/litfoundry` or XDG; macOS `/Library/Application Support/LitFoundry` or user Application Support); no SQLite database inside PyInstaller extraction directories. Choose explicit server or workstation mode (Section 3) at installation.

Document HTTPS proxy setup and firewall configuration, AD controller/CA trust prerequisites, and the server service account's filesystem/UNC backup write access; the backup destination must be readable only by the service identity and administrators, because backups contain secrets. Start/stop Flask, worker and optional Caddy via a single supervisor/launcher; include a service-install script for Windows Service (suitable wrapper) and, when those packages ship, systemd on Linux and launchd on macOS. Caddy may be an independently installed prerequisite where packaging/certificate permissions complicate distribution. Verify launch on a clean machine for each packaged platform, including fonts, plotting, migrations, SQLite and browser assets.

### 18.1 CLI reference

| Command | Purpose |
|---|---|
| `litfoundry init` | Create the data root with restrictive permissions, the catalogue and a bootstrap token |
| `litfoundry bootstrap-token` | Issue a new first-run token while setup is pending |
| `litfoundry admin reset-password` | Host-only, audited `admin` password recovery |
| `litfoundry serve` | Run Waitress (server mode behind Caddy, or workstation mode on loopback) |
| `litfoundry worker` | Run a background worker |
| `litfoundry supervise` | Run the server and worker processes under one supervisor (used by the OS service) |
| `litfoundry status` | Health, versions, job queue and backup status |
| `litfoundry migrate` | Run catalogue and project migrations under the maintenance lock |
| `litfoundry reconcile` | Repair cross-database workflow states (Section 4.3) |
| `litfoundry backups list\|verify\|create` | Full-backup operations (Section 16); `create` takes `--destination PATH` |
| `litfoundry restore --archive PATH --dry-run\|--confirm` | Offline full restore (Section 16.5) |
| `litfoundry service install\|uninstall` | Install or remove the OS service (Windows Service in v1; systemd and launchd are SHOULD) |

## 19. Testing and acceptance criteria

**Mandatory automated test groups:**

1. Bootstrap fixed username `admin`, token, concurrent first-admin attempts, denial after setup, inability to rename/disable `admin` or create a second admin, Argon2id hash, local password reset/session revocation; `admin` always signs in when AD is down or disabled and cannot be locked out by failed attempts from other IPs.
2. Local username sign-in (character rules, case-insensitivity, forced password change); AD enabled and disabled; AD cannot be enabled without a tested service account; a local `jsmith` and an AD `jsmith` are distinguished by explicit provider; SID binding uniqueness; pre-provision-only AD accounts; unprovisioned, disabled or locked AD accounts are rejected without a user bind; wrong password, unknown user, TLS/CA failure, LDAP injection, throttling below the domain lockout threshold, directory outage, AD account disable and session revocation. Use ldap3's mock strategies for unit tests on all platforms and a Samba AD DC container for integration tests on Linux CI. Then the multi-user project ACL matrix: public_view, public_edit, explicit deny, revocation, admin full access (audited, overrides deny) and forged URL/API access.
3. Per-project database location/URI checks; no cross-project read/write with forged UUID/path; creation/deletion recovery, including deleting a project another process used moments earlier (Windows file locks); ownership transfer leaves files in place.
4. Central/project migration from prior fixture versions, backup, restart and failed migration recovery.
5. Query AST schema validation and compiler fixtures (AND/OR/NOT, nested quotes, years, wildcards); OpenAlex request length, equivalent query partitioning (never splitting AND operands or OR groups inside NOT), deduplicated union counts and rejection of mixed stemmed/wildcard queries; disabled source produces zero calls.
6. API source adapter fixtures (OpenAlex, WoS Starter, DOI enrichment of Starter records) for success/auth failure/quota and budget/pagination/partial/interruption; no live paid credentials in CI.
7. File import/normalise provenance, duplicate pair suggestions with blocking (a 50,000-record fixture stays within budget) and reversible merges that keep work IDs; conference/journal false positive case.
8. Dual reviewer screening, full-text retrieval, reasons, adjudication and PRISMA reconciliation, including metadata-only mode.
9. Analysis engine smoke tests with a small known network and deterministic counts; flag missing reference coverage; corpus hash/version reproducibility.
10. Background jobs run/cancel/reclaim/partial failure, write-scope conflicts (`RECORD_LOCKED`, `PROJECT_BUSY`) and permission revocation while queued.
11. Single-project ZIP export/import roundtrip (schema, hashes, unchanged corpus hash, artifacts, private default, imported reviewers), traversal/zip-bomb rejection, secret exclusion and export expiry; separately, the **full-system backup** created from the CLI with all project DBs/files, catalogue and secret material, write-barrier consistency, verified archive, quarantine, corrupted/missing destinations and cross-platform offline restore (scheduling and retention tests are added with those SHOULD features).
12. Playwright (Python) end-to-end GUI: bootstrap fixed `admin`; admin creates local users and, against the test directory, configures AD and pre-provisions an AD account; local and AD sign-in; user creates project, searches with fixtures, dedup, screen, PRISMA SVG, analysis, sharing, export/import, logout.
13. Installer smoke test on Windows and venv smoke tests on Linux and macOS; the browser UI works with no internet access.
14. Security tests for CSRF, origin/host policy, auth on every download, XSS in imported titles, denial of unsafe file paths, and a strict CSP (`script-src 'self'`, no `unsafe-eval`) with zero violations across the end-to-end suite.

**Functional performance targets** (baseline, not guarantees): UI pages with 50,000 records use server pagination; typical project dashboard returns under 2 seconds on a modern LAN machine; no bibliographic API call blocks a Flask request thread; a failed source does not discard other sources' results; project files and results survive restart. Run load tests with multiple simultaneous viewers/editors and at least 10,000 source records as a first performance gate.

**Definition of done:** On a clean Windows host, the correctly branded packaged installation (and on Linux or macOS, a venv installation) can be started as a server; a unique built-in `admin` is created safely on first use and always signs in with its local password; the admin can create local username/password accounts and, optionally, connect one AD domain and pre-provision AD accounts; at least two users access through separate LAN browsers over HTTPS; projects remain physically separate folders with project SQLite databases; public viewer/editor permissions and admin access operate as defined; searches/CSV imports, versioned deduplication, complete screening and PRISMA SVG work; bibliometric result and source provenance are reproducible; a project ZIP is exported and imported into a new private project; migrations, timestamped full-system backups created from the CLI, and full offline restore are verified; no user secrets leak into project exports or logs.

## 20. LitFoundry delivery plan and repository layout

```text
litfoundry/
  pyproject.toml
  README.md
  docs/
    architecture.md
    data-model.md
    query-semantics.md
    security.md
    deployment-windows.md
    deployment-linux.md
    deployment-macos.md
    api.openapi.yaml
    query-ast.schema.json
    decisions.md
  src/litfoundry/
    app.py
    config.py
    api/              # Blueprints/request schemas only
    auth/             # local accounts, reserved admin, optional Active Directory, authorization services
    catalog/          # shared SQLite models/repositories
    projects/         # project CRUD/engine routing/migrations
    queries/          # AST grammar and three query compilers
    sources/          # source adapters/import parsers
    processing/       # canonical records/dedup/provenance
    review/           # PRISMA/screening/corpus services
    bibliometrics/    # Biblium adapter + fallback/exports
    jobs/             # queue, worker, locks and progress
    export/           # per-project ZIP snapshots and imports
    backups/          # full system snapshot, schedule, retention, verify, restore
    cli.py
  migrations/
    catalog/
    project/
  frontend/
    index.html
    js/               # Vue 3 runtime-only render-function components, in-house router, Axios client
    css/              # Tailwind source and built CSS
    vendor/           # exact-version, checksum-verified local copies of Vue (runtime-only), Axios and ECharts
  packaging/
    pyinstaller/
    windows/
    linux/
    macos/
    caddy/
    directory/        # LDAP/AD deployment CA and permissions guidance
  tests/
    unit/
    integration/
    e2e/
    fixtures/
  scripts/            # includes the pinned vendor-asset fetch/verify script
  LICENSES/
```

Recommended milestones with mandatory passing tests after each:

- **M1:** Flask/Waitress/Caddy + Vue (runtime-only)/Axios/Tailwind + catalog DB + fixed `admin` bootstrap, local username login, provider abstraction and first LAN HTTPS deployment.
- **M2:** Per-project folders/DBs + ACLs/public sharing/admin access + migrations + create/edit/delete + background workers; optional AD/LDAP adapter with service account, configuration and admin pre-provisioning.
- **M3:** Keyword AST + compilers for all sources (copyable Scopus and WoS queries) + credential precedence + OpenAlex and WoS Starter retrieval with DOI enrichment + file imports (Scopus, WoS, OpenAlex) + call budgets.
- **M4:** Record canonicalisation + field provenance + duplicate review + search run/corpus versioning.
- **M5:** Full screening/eligibility + reviewer arbitration + count validation + PRISMA SVG exports.
- **M6:** Bibliometric analyses 1–5 and 9 + interactive visualisations + report and figure generation.
- **M7:** ZIP snapshot/export and safe import, **manual CLI full backup, verification and offline full restore**, Windows packaging and Windows Service, security and performance hardening. Include a backup foundation (consistent DB snapshots and job coordination) from M2 so it is not deferred until launch.
- **Post-v1 (SHOULD):** scheduled backups with retention and admin screens; Linux and macOS packages and services; Scopus Search API and WoS Expanded adapters; ASReview interoperability; analyses 6, 7 and 10. **MAY:** analysis 8, admin TOTP, personal-data tooling, multiple AD domains, Windows SSO, PyBibX/BibFusion connectors, email notifications.

Codex should make small verifiable commits, update `docs/decisions.md` for unavoidable design details, and provide exact commands to run and test each milestone. M1 acceptance tests must verify the `LitFoundry` UI title/tagline, `litfoundry` CLI/import path, environment prefix, Caddy hostname example and a strict CSP (`script-src 'self'`, no `unsafe-eval`) with zero violations; M7 must verify branded export/backup filenames and archive manifests. Never report a milestone complete without tests and a short demonstration path.

## 21. Primary reference links (implementation verification)

- Vue builds, production deployment and render functions: https://vuejs.org/guide/quick-start.html, https://vuejs.org/guide/best-practices/production-deployment and https://vuejs.org/guide/extras/render-function
- Waitress: https://docs.pylonsproject.org/projects/waitress/en/latest/
- Flask-Alembic: https://flask-alembic.readthedocs.io/en/stable/api/
- Alembic cookbook (sharing a connection with programmatic commands): https://alembic.sqlalchemy.org/en/latest/cookbook.html
- Flask JWT cookie CSRF: https://flask-jwt-extended.readthedocs.io/en/stable/token_locations.html
- LDAP3 AD bind/secure transport: https://ldap3.readthedocs.io/en/latest/bind.html and https://ldap3.readthedocs.io/en/latest/ssltls.html
- ldap3 licence (LGPL, commercial use): https://ldap3.readthedocs.io/en/latest/welcome.html
- Python SQLite online backup: https://docs.python.org/3/library/sqlite3.html#sqlite3.Connection.backup
- Python zipfile (ZIP64): https://docs.python.org/3/library/zipfile.html
- Caddy reverse proxy / internal CA: https://caddyserver.com/docs/caddyfile/directives/reverse_proxy and https://caddyserver.com/docs/caddyfile/options
- Apache ECharts: https://echarts.apache.org/handbook/en/basics/download/
- OpenAlex scoped Boolean search and limits: https://help.openalex.org/api/searching/
- OpenAlex API keys and usage pricing: https://help.openalex.org/api-reference/authentication and https://help.openalex.org/access/pricing/
- Clarivate WoS APIs (Starter, Expanded): https://developer.clarivate.com/apis/wos-starter and https://developer.clarivate.com/apis/wos
- Biblium: https://pypi.org/project/biblium/
- PyBibX: https://github.com/Valdecy/pybibx
- BibFusion: https://github.com/ladmepaz/bibfusion
- prisma-flow: https://github.com/osl-incubator/prismaflow and https://pypi.org/project/prisma-flow/
- PyInstaller commercial-use licence exception: https://pyinstaller.org/en/stable/license.html

## Appendix A. v1.3 change log and open items

### A.1 Product-owner decisions (19–20 October 2026)

1. **Frontend:** Vue runtime-only build with render functions (`h()`); strict CSP (`script-src 'self'`, no `unsafe-eval`).
2. **Sign-in:** Local username/password sign-in is always available and is how `admin` signs in. Active Directory is optional, limited to one domain, and requires a service account. The email-only / AD-only / both modes are removed.
3. **Local identifiers:** Local accounts sign in with usernames, not email addresses.
4. **Trust model:** The admin is fully trusted and has full owner-equivalent access to every project in the application.
5. **Backups:** Full backups are unencrypted and include the stored secrets.
6. **v1 scope:** Active Directory sign-in ships in v1. The following are deferred (Section 0.2):
   - scheduled backups
   - Linux and macOS packages
   - the Scopus API and WoS Expanded adapters
   - ASReview interoperability
   - analyses 6–8 and 10
7. **WoS Starter:** A Web of Science Starter API adapter ships in v1 alongside OpenAlex.
8. **First packaged platform:** Windows.
9. **Admin TOTP:** Not in v1 (MAY).
10. **Personal data:** v1 documents what is stored; export and pseudonymisation tooling is MAY.

### A.2 Defaults chosen while revising (open to change)

- CDN asset mode and `LITFOUNDRY_FRONTEND_ASSET_MODE` are removed, and vendored local copies are always served. A strict CSP would otherwise have to allow a third-party origin, and module imports cannot carry SRI.
- An in-house History-API router replaces vue-router. Vue-router's browser ESM build imports bare `'vue'`, which would need an inline import map.
- Vue is loaded as its runtime ES module; Axios and ECharts as classic global builds.
- Project folders are `projects/<project_uuid>/`, and only the catalogue records ownership.
- Project engines use `NullPool`, so project folders can be moved or deleted on Windows.
- Project migrations use plain Alembic's programmatic API; Flask-Alembic is used for the catalogue only.
- Project files are write-once. Operational catalogue tables are exempt from the backup write barrier, and jobs pause at write checkpoints rather than finishing.
- A `quarantined` project state lets backups proceed past one damaged project.
- Background jobs declare write scopes (`append`, `records`, `project`) instead of taking a single project-wide write lease.
- Project export ZIPs expire after 7 days and are excluded from full backups.
- There is no default backup destination, and it must be outside the data root.
- The session signing key is rotated on restore, so everyone signs in again.
- Cookies use `SameSite=Lax`.
- One OS service, `litfoundry`, supervises the server and worker processes.
- Workstation mode is defined as single-machine, loopback-only use.
- Failed `admin` sign-ins are throttled per IP and never lock the account. AD sign-ins default to 3 failures per identifier per 15 minutes.
- OpenAlex uses a direct REST adapter rather than PyAlex, whose API key setting is module-global.
- OpenAlex and WoS Starter keys get per-key daily budgets, and each search shows an estimated call count first.
- WoS Starter records get abstracts from OpenAlex by DOI.
- Query compilers for all sources stay MUST, so users can run the Scopus and WoS queries in those services and import the export files.
- Priorities for deferred features:
  - SHOULD: analyses 6, 7 and 10, and ASReview.
  - MAY: analysis 8, because it is not yet specified.
- Renames:
  - `references` table → `work_references`
  - `/projects/imports` → `/project-imports`
  - `/projects/{id}/imports` → `/projects/{id}/source-imports`
  - backup run actions moved under `/admin/backups/runs/{run_id}/…`

### A.3 Verification results (20 October 2026) and remaining checks

**Verified:**
- **ldap3:** the latest stable release is 2.9.1 (July 2021); 2.10.2 release candidates continued through April 2026. The spec pins it and requires the AD tests on every supported Python version.
- **Flask-Alembic 3.3:** supports plain SQLAlchemy, but its documentation doesn't show migrating an open-ended set of database files. Projects therefore use plain Alembic.
- **pybliometrics and PyAlex:** both configure API keys process-wide. pybliometrics also caches responses under the user's home directory by default.
- **OpenAlex:**
  - cursor paging beyond the first page needs an API key;
  - a free key includes $1 of usage per day;
  - each response reports its cost in the `X-RateLimit-Credits-Used` header;
  - sources disagree on whether a key is needed for every request.
- **prisma-flow:** version 0.6.1 is alpha; it was first released in May 2026.
- **WoS Starter:**
  - returns no abstracts, cited references, Keywords Plus or author addresses;
  - 50 records per page;
  - key in the `X-ApiKey` header;
  - daily quotas depend on the plan (50, 5,000 or 20,000 requests).
- **Vue 3.5:** ships `vue.runtime.esm-browser.prod.js` and `vue.runtime.global.prod.js`.

**Check before release:**
- Current OpenAlex and WoS Starter pricing and quotas.
- WoS Starter's maximum retrievable records per query, which the portal page doesn't state.
- Whether ldap3 2.10 reaches a stable release.
- Write a specification for analysis 8 before scheduling it.
