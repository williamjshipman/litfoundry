# LitFoundry — Codex Implementation Specification

**Version:** 1.2 (19 October 2026)  
**Status:** Implementation-ready design and acceptance contract (official LitFoundry naming, authentication, scheduled full backups)  
**Product:** **LitFoundry** — *From literature to insight.*  
**Target:** Multi-user, LAN-hosted, cross-platform bibliometric and PRISMA research application

## 0. Instructions to Codex

Implement this application in an incremental, test-driven series of vertical slices. This document is the product and architectural source of truth. Do not replace the specified stack, omit security controls, generate placeholder bibliometric results, or assume access to paid bibliographic APIs. When an external dependency or API is uncertain, isolate it in an adapter, verify its installed interface, document the finding, and retain an operational manual-import path. Implement migrations and tests with each slice. Do not use an LLM service as a mandatory dependency. All features must be available through the web GUI and through versioned REST endpoints.

**Priority levels:** MUST = release requirement; SHOULD = desirable and testable improvement; MAY = later enhancement.

### 0.1 Official product name and naming contract (binding)

- **Public product name:** **LitFoundry** (exact capitalisation). **Tagline:** *From literature to insight.* **Product description:** Open-source software for systematic literature reviews, PRISMA workflows and bibliometric analysis. Use these consistently in the application header, login/setup, administrator console, help/about screen, installer, documentation, project manifests, ZIP metadata and error-report headers.
- **Canonical machine-readable identifier:** `litfoundry` (lowercase ASCII). Python distribution and import package: `litfoundry`; repository name: `litfoundry`; CLI executable: `litfoundry`; production service IDs: `litfoundry-server` and `litfoundry-worker`; application data directory: `LitFoundry` on Windows/macOS and `litfoundry` on Linux. Do not create new identifiers named `brm`, `pybrm`, `bibliometric-research-manager`, or `appctl`.
- **Python packaging:** `pyproject.toml` declares a distribution named `litfoundry`, exposes `[project.scripts] litfoundry = "litfoundry.cli:main"`, and packages code under `src/litfoundry/`. The Flask application factory should be imported from `litfoundry.app` (or an explicitly documented stable submodule). All documentation and tests must use these names.
- **Network/deployment:** Example HTTPS hostname `litfoundry.example.internal`; localhost-only Waitress endpoint stays `127.0.0.1:5080`, proxied by Caddy. Configuration environment variables should use the `LITFOUNDRY_` prefix, including `LITFOUNDRY_DATA_ROOT` and `LITFOUNDRY_FRONTEND_ASSET_MODE`; include a cross-platform configuration reference. The example hostname is a placeholder, not a hard-coded DNS dependency.
- **Data storage:** Keep the stable generic SQLite filenames `catalog.sqlite` and `project.sqlite` and versioned REST prefix `/api/v1` unchanged. Choose cross-platform default data roots appropriate for service permissions: Windows `%PROGRAMDATA%\LitFoundry` for service mode; Linux `/var/lib/litfoundry`; macOS `/Library/Application Support/LitFoundry` for system-wide mode, with user-scoped alternatives for non-service development. Never embed host-specific paths in portable project ZIPs.
- **Archive names:** Single-project exports use `litfoundry_project_<project_uuid>_<YYYYMMDD_HHMMSSZ>.zip`, and full-system backups use `litfoundry_full_<YYYYMMDD_HHMMSSZ>_<run_uuid_short>.zip`. All ZIP manifests include `"product": "litfoundry"`, `"product_name": "LitFoundry"`, plus the documented export/backup format version; imports validate the identifier and version before changes. Descriptive report names and figure titles may mention PRISMA, bibliometrics and the project title.
- **Reserved account:** The special local administrator username remains literally `admin` and is **not** renamed to `litfoundry` or an email address.
- **Compatibility:** There is no requirement to accept archives produced by the previously proposed, unimplemented `brm` naming scheme. If an earlier development build exists, provide an explicit migration/alias plan rather than silently reusing or overwriting files.

## 1. Product scope and explicit decisions

LitFoundry enables registered users to maintain multiple independent literature-research projects. Authentication is administrator-configurable for local email/password, Microsoft Active Directory, or both; a reserved local `admin` login is always available. The system supports scheduled, verified, retained full-installation ZIP backups. Within a project, they define keyword groups and filters, enable OpenAlex / Scopus / Web of Science independently, inspect source-specific queries, execute and import searches, deduplicate records, conduct PRISMA-guided screening including full-text eligibility, freeze corpora, run bibliometric analyses, publish diagrams and reports, and download/import self-contained project ZIP archives. All history, decisions, raw records, normalisation, and analysis provenance persist across restarts.

Eight original binding decisions (extended by authentication and backup requirements in Sections 5 and 16):

1. **LAN:** One server installation accepts browser connections from multiple computers on an internal network. HTTPS is required in LAN deployments. Internet publication databases remain separate outbound dependencies.
2. **Public projects:** 'Public' means discoverable by **all authenticated users of this installation**, not anonymous internet viewers. A public project has default `viewer` or `editor` access for all registered users. The owner may also grant individual exceptions. Anonymous users cannot view any project data.
3. **Project storage:** Each project is a folder containing its own SQLite database (`project.sqlite`) plus project artifacts. A separate central `catalog.sqlite` manages users, settings, project discovery, sharing and job scheduling. **No single per-user project database**.
4. **Accounts:** Only the built-in local `admin` account creates/disables users; ordinary local users log in using an email address and AD users use a directory account name. Admin configures whether email, AD or both methods are enabled. No self-registration or just-in-time AD provisioning.
5. **Credentials:** Admin-managed shared source credentials; each user may optionally supply a per-source personal override. Effective credential = user's enabled override, else shared default, else unavailable. Never export secrets.
6. **Review method:** Complete PRISMA identification, screening, optional retrieval and full-text eligibility (when genuinely performed), exclusion accounting, versioned included sets, plus bibliometric analysis.
7. **Operating systems:** Windows, Linux and macOS, including CI and packaging for each.
8. **Distribution:** Python virtual environment for development and independently packaged distributions for end users. The packaged app can act as a LAN server; other users need only browsers. **Additional requirement:** Administrator-configured scheduled ZIP backups of the complete installation data, with destination selection, date/time filenames and count-based retention.

### Roles

- **Admin:** A single, reserved account that always signs in with username exactly `admin` and a local password (even in AD-only mode). Creates, disables and resets local users, pre-provisions AD accounts, configures login methods/directory settings, shared credentials, proxy/network settings, scheduled full backups and system diagnostics. Admin does not implicitly read private project content through normal project APIs; an administrator with server and backup access remains a highly privileged operator.
- **User:** Either a local-email account or a directory-backed AD account, pre-provisioned by the admin. Owns and edits projects and sees projects to which the account has access.

### Project rights

| Action | Owner | Explicit editor / public-edit | Explicit viewer / public-view |
|---|---|---|---|
| Discover and read | Yes | Yes | Yes |
| Download permitted result tables/figures | Yes | Yes | Yes |
| Edit strategy, records, screening | Yes | Yes | No |
| Run searches/analyses | Yes | Yes | No |
| Export full project ZIP (raw data included) | Yes | No | No |
| Manage shares, ownership, credentials | Owner only | No | No |
| Delete / archive project | Owner only | No | No |

Access resolution: owner > explicit per-user ACL (`editor`, `viewer`, `deny`) > public default (`editor`, `viewer`, or none) > deny. The `deny` exception enables an owner to exclude an account from an otherwise public project. A disabled account always denies access. Privileges must be checked on **every** API and background job and again when generating download links.

## 2. Technology and licensing

| Layer | Required components |
|---|---|
| Server | Python 3.12+, Flask with application factory and Blueprints; Waitress WSGI for cross-platform serving |
| Persistence | SQLAlchemy 2.x + SQLite with WAL, foreign keys, busy timeout |
| Migration | Flask-Alembic for central and *template* project schema; explicit orchestrator applies project migrations to each `project.sqlite` |
| Security | Flask-JWT-Extended, Flask-CORS, Argon2id, audited permission checks, CSRF, login throttling, `ldap3` (LGPL-3.0-or-later; commercial use permitted subject to notices) for Active Directory via LDAPS/StartTLS |
| Frontend | Vue 3 **CDN-distributed production global build**, plain JS modules/components without Vue SFC/Vite/Node runtime; Axios; Tailwind CSS compiled into a local static stylesheet |
| Data APIs | PyAlex/OpenAlex, pybliometrics/Scopus, HTTPS adapter to Clarivate Web of Science API Expanded; file import alternatives |
| Science | pandas, numpy, scipy, NetworkX, Biblium behind an adapter; optional PyBibX/BibFusion as separately tested adapters |
| Screening | Native persistence/reviewer interface; ASReview interoperable import/export, no mandatory embedded ASReview server |
| Diagrams | `prisma-flow` for PRISMA SVG and validations |
| Visualization | Apache ECharts (Apache-2.0) for interactive network graphs and charts, including SVG/Canvas rendering; backend SVG/PNG exports where feasible |
| Tests | pytest, pytest-flask/httpx (as relevant), Playwright, lint/typecheck, integration fixtures |
| Packaging | PyInstaller one-folder distribution built separately on Windows/macOS/Linux; platform launcher, optional service installation |
| Full backup | Standard `sqlite3.Connection.backup()` for SQLite snapshots; `pyzipper` or vetted equivalent for WinZip AES-256 encrypted ZIP archives; built-in scheduled-job coordinator with persisted due-times |
| LAN HTTPS | Caddy TLS reverse proxy (recommended, separately installed/optionally bundled where licence permits), serving a stable internal DNS name; Waitress on loopback |

Require a checked-in lockfile or constraints file, licence inventory and SBOM. For LDAP use the LGPL licence obligations (not GPL prohibition of business use); pyzipper is MIT-licensed. Verify pinned package versions and their redistribution notices before release. Exclude libraries that prohibit commercial usage. **Do not assume all transitive dependencies of Biblium/PyBibX are appropriate for proprietary redistribution**; run an automated licence review before packaging. Avoid bundling large optional ML dependencies unless enabled.

**Frontend build constraint:** Develop using exact version-pinned CDN URLs for `vue.global.prod.js` and Axios. The packaged LAN distribution must also contain locally mirrored copies of those exact licensed artifacts and default to serving those local copies, so disconnected client browsers work without CDN access. Provide a documented setting `LITFOUNDRY_FRONTEND_ASSET_MODE=local|cdn` (default local in package, CDN allowed in development). CDN mode must pin versions and use SRI where supported; no unversioned `@latest` URLs. Do not use Vue single-file components or Tailwind Play CDN. Compile Tailwind into static CSS using a pinned standalone Tailwind CLI or equivalent build-only tool. No Node application server is required.

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
         +--> local worker process(es) -> OpenAlex / Scopus / WoS via outbound HTTPS
         +--> login adapter -> Active Directory domain controller via LDAPS/StartTLS
         +--> backup scheduler/worker -> encrypted, timestamped ZIP on server-admin target path
```

- The **Flask service listens on localhost** (`127.0.0.1:5080`) behind the TLS reverse proxy; the **reverse proxy** listens on the LAN. Never expose Flask's development server or Waitress plaintext endpoint on the LAN in production.
- Use a stable internal DNS hostname, TLS certificates trusted by client computers (organisation CA or Caddy internal CA whose root has been explicitly trusted), restricted inbound firewall rule, and HTTPS-only cookies. Document CA trust distribution for Windows/macOS/Linux and browsers. Caddy `tls internal` is possible but clients do not automatically trust that CA.
- Configure explicit trusted proxy IPs and forwarded headers, host allowlist, request limits and CSP. Set secure-cookie flags. Same-origin SPA and `/api/v1` makes CORS unnecessary for normal use; retain Flask-CORS but enable **only** on allowlisted origins for special development deployments, with credentials and no wildcard.
- Provide `litfoundry serve`, `litfoundry worker`, `litfoundry status`, `litfoundry migrate`, `litfoundry backups create`, `litfoundry restore` and a package launcher. Installer does not need to install on client PCs. Default port, data root and DNS host are configurable.
- The server should continue serving existing projects without internet; online searches fail clearly and can be retried. Never depend on the CDN to render the packaged GUI.

## 4. Data layout and persistence

```text
<data_root>/
  catalog.sqlite                # central accounts, access, queue, global settings
  secret_material/              # OS protected; never served or exported
  backups/                     # default local destination (may be on another disk/share)
  backup_staging/               # secure transient consistent snapshots; never recurse into backups
  logs/
  projects/
    <owner_user_uuid>/
      <project_uuid>/
        project.sqlite          # ALL project-specific relational records
        manifest.json           # portable schema/export info (non-secret)
        sources/<search_run_uuid>/<source>/raw/
        imports/
        attachments/            # optionally uploaded full texts
        figures/
        reports/
        exports/
        temp/                   # excluded from ZIP
```

A system administrator may set an external backup destination independently from `<data_root>`; backups are generated on the server and placed there, not downloaded to the browser as a directory. Only the server host owns/mounts SQLite files. **Never store active SQLite databases on SMB/NFS shares**. Use a local disk with appropriate backup; distribute backups over a network if necessary. UUIDs form directory names; user-supplied titles are metadata only. Refuse unsafe symlinks, relative paths, `..`, archive traversal and attempts to escape `data_root`.

### 4.1 Central catalogue schema (minimum)

- `users(id UUID PK, account_type [admin_local|email_local|active_directory], login_email_normalized nullable, display_name, password_hash nullable, role [admin|user], active, session_version, created_at, last_login_at)`; unique case-insensitive local email and exactly one reserved admin login `admin`; **only** `admin_local` can hold the system admin role.
- `directory_identity_bindings(id UUID, user_id UNIQUE FK, directory_id FK, object_sid UNIQUE within directory, object_guid nullable, samaccountname_normalized, upn_normalized, last_directory_sync_at, directory_status, created_at)`; immutable AD SID is the primary match to a pre-provisioned user account, not an email address.
- `directory_configs(id UUID, domain_label, domain_dns_name, netbios_name, server_hosts_json, base_dn, service_bind_identity, bind_secret_ref, tls_mode [ldaps|starttls], ca_bundle_ref, enabled, timeouts_json, updated_at)`; only safe configuration and references, never plaintext password.
- `auth_settings(id single_row, enable_local_email, enable_active_directory, default_ad_directory_id nullable, revision, updated_at)`; at least one ordinary login method enabled; **reserved admin always works** irrespective of these booleans.
- `system_settings(key PK, value_json, updated_at)`; no clear-text credentials.
- `source_credentials(id, scope [global|user], user_id nullable, provider, secret_ref, enabled, updated_at)`
- `project_directory(id UUID PK, owner_user_id FK, title, public_access [none|viewer|editor], state [provisioning|ready|deleting|error], relative_path, created_at, updated_at, project_schema_version, latest_indexed_revision)`
- `project_acl(project_id, user_id, role [viewer|editor|deny], created_by, updated_at)`
- `jobs(id UUID PK, project_id, requester_id, type, status, args_json, progress_json, lease_owner, lease_expires_at, attempt, max_attempts, cancellation_requested, created_at, started_at, finished_at, last_error_code)`
- `sessions_or_revoked_tokens(jti, user_id, expires_at)` plus session invalidation semantics.
- `backup_settings(id single_row, enabled, frequency [daily|weekly|monthly], local_time_hhmm, iana_timezone, weekday nullable, monthday nullable, destination_server_path, retain_count, encryption_secret_ref, include_logs, revision, updated_by, updated_at)`; all modifications require the `admin` account.
- `backup_runs(id UUID PK, scheduled_for_utc, started_at, completed_at, status [queued|running|completed|failed|cancelled], destination_file, archive_sha256, archive_bytes, source_snapshot_id, error_code, validation_json, rotation_json, initiated_by [schedule|admin|cli], created_at)`; persist run history outside the backup archive and include a copy in its manifest.
- `system_leases(name UNIQUE, owner, expiry, fencing_token)` for maintenance/backup/migration locks and single-scheduler coordination.
- `audit_events(id, actor_id, project_id nullable, action, details_json, timestamp)`

Create unique constraints and indexes for normalized login emails, directory+SID, reserved admin singleton, project owner, public state, ACL, job states, schedule due-time and maintenance leases. Never return secrets or password hashes from REST endpoints.

### 4.2 Per-project schema (minimum)

- `project_info(id, owner_id, title, description, objectives, research_questions_json, created_at, updated_at, revision)`
- `source_selections(provider, enabled, source_options_json)`
- `keyword_spec_versions(id, project_id, ast_json, scope_json, rationale, created_by, created_at, immutable)`
- `query_versions(id, spec_id, provider, generated_query, override_query nullable, effective_query, compiler_version, validation_json)`
- `search_runs(id, spec_id, status, started_at, ended_at, created_by, source_run_ids_json)`
- `source_runs(id, search_run_id, provider, query_version_id, credential_scope_used [shared|personal], status, count_reported, count_retrieved, cursor_state, result_completeness, created_at)`
- `raw_records(id, source_run_id, provider, provider_record_id, raw_file_ref, raw_sha256, imported_at)`
- `works(id, canonical_title, abstract, year, date, doi_normalized, journal, work_type, metadata_json, revision)`
- `work_identifiers(work_id, scheme, value)`
- `work_sources(work_id, raw_record_id, selected_fields_json, confidence)`
- `authors`, `affiliations`, `work_authors`, `work_affiliations`, `keywords`, `work_keywords`, `references`, `citations` with source/provenance where available
- `duplicate_candidates(id, work_a, work_b, score, factors_json, status)` and `merge_decisions(id, actor_id, timestamp, originals_json, retained_work_id, decision, reason, reversible_event_ref)`
- `review_protocol_versions(id, method [systematic|scoping|bibliometric], criteria_json, reviewer_policy_json, created_by, created_at)`
- `record_screening_decisions(id, work_id, stage [title_abstract|full_text], reviewer_id, decision [include|exclude|uncertain], reason_code nullable, notes, round_id, version, timestamp)`
- `retrieval_attempts(id, work_id, report_id, outcome [retrieved|not_retrieved|not_sought], reason, actor_id, timestamp)`
- `full_text_reports(id, work_id, attachment_id, metadata_json)` (allow many reports per study where applicable)
- `study_groups(id, label, details)` and `study_work_links(study_id, work_id)` (separate records, reports, works and studies)
- `screening_resolutions(id, work_id, stage, final_decision, resolved_by, timestamp, reason_code)`
- `corpus_snapshots(id, label, included_work_ids_file_or_join, protocol_version_id, selected_search_runs_json, created_by, created_at, hash, frozen)`; use join table for large sets
- `keyword_normalization_rules(id, pattern, replacement, rule_type, enabled, revision)`
- `analysis_runs(id, corpus_id, engine, analysis_type, parameters_json, software_versions_json, input_hash, status, timestamps, created_by)`
- `artifacts(id, analysis_run_id nullable, kind, relative_path, sha256, size, mime, created_at)`
- `prisma_snapshots(id, corpus_id, counts_json, exclusions_json, overrides_json, validation_json, generated_at)`
- `project_audit_events(id, actor_id, action, details_json, timestamp)`

Use immutable source runs and append-only reviewer/audit histories. Editable normalized records need integer `revision` for optimistic concurrency (`If-Match`/ETag or version field). Preserve field-level provenance and conflicting-source values. Use server-generated UTC timestamps and stable UUIDs. Source counts distinguish retrieved *records*, reports and included *studies*.

### 4.3 Project creation, routing and migration

1. Authenticated creator requests a project. Insert central directory row `provisioning`, create temporary project folder and project DB from latest migration, write manifest, atomically rename staging folder (same filesystem), mark `ready`. On failure mark error or clean up.
2. Every API request resolves project UUID through central catalogue, authorises the current user, then opens **only that project's** scoped SQLAlchemy session. Use short-lived sessions and an LRU engine cache, with per-project connection limits and explicit disposal.
3. Cross-database writes cannot be atomic. Use explicit workflow states, idempotency keys and a reconciliation command; never assume a single transaction can span `catalog.sqlite` and project DB.
4. Flask-Alembic manages versioned schema scripts for `catalog` and **project database template**. Authentication and backup catalogue revisions must be migrated with the central schema. A migration coordinator acquires a global maintenance lock, backs up databases, then applies project migrations sequentially with verification and schema-version recording. Do not register hundreds of dynamically created per-project engines as fixed Flask binds. Test rollback/restore if a migration fails.
5. Deletion is two-stage: mark directory `deleting`, revoke access/cancel jobs, move project folder to controlled trash and eventually purge it. Provide owner confirmation and a backup/export opportunity.

## 5. Account setup, email/Active Directory authentication and authorization

### 5.1 Reserved built-in administrator and initial bootstrap

- On first run, with no administrator present, all application operations other than health and bootstrap are locked. Show `/setup`. The **only** first account is `admin`; its username is literally `admin`, permanently reserved, not editable, not an email address and **never authenticated through AD**. Its password is local Argon2id only.
- Require the server-console/package-launcher-generated single-use short-lived bootstrap token plus a strong new password; do not accept a user-chosen alternative admin username. Consume token atomically under a unique database constraint. There is no factory default password. After setup, bootstrap never succeeds again without a separate audited host-only recovery CLI.
- `admin` stays available for emergency administration when LDAP/domain controllers are unreachable or either/both ordinary-user login methods are disabled. Prevent deletion/renaming/disablement of the built-in account through API, and prevent creating a second `admin`-role account in this release. Admin password change and host-only recovery are auditable; recovery CLI requires OS service/data permissions.
- The login page may offer an explicit **Administrator** selection or accept the exact literal username `admin` in an admin-specific mode; `admin` cannot authenticate using the local-email or AD provider and must never be routed to a directory bind. The administrator is always authenticated with the stored local password hash.

### 5.2 Configurable ordinary-user login providers

The administrator can select **Local email only**, **AD only** or **Both** in an authenticated administrator Settings → Authentication screen. There is no self-service registration. Changing modes requires explicit confirmation, audits the before/after values and immediately blocks newly attempted logins through disabled methods; previously issued sessions for a disabled provider are revoked via `session_version`/auth-policy revision. This must not impact `admin`.

| Provider mode | Login identifier | Credential verification | User creation |
|---|---|---|---|
| `email_local` | Email address such as `alice@example.org` (stored with documented case-insensitive normalization) | Argon2id local password hash | Admin creates local account, assigns initial/reset password securely; can require change at first login |
| `active_directory` | `DOMAIN\alice`, UPN such as `alice@corp.example.org`, or unqualified `alice` only when one eligible directory makes it unambiguous | TLS-protected AD bind (LDAP client) | Admin pre-provisions directory-backed account by resolving the chosen directory identity and binding its immutable SID to application user UUID |
| Both enabled | Explicit login-method tab/select (`Email address` / `Active Directory`); `admin` separate | Selected provider only | Admin provisions or maintains distinct accounts |

Do **not** automatically infer provider from `@`: an AD UPN resembles an email address, so when both are enabled the request must explicitly include `provider`. A login identity that exists with both providers represents separate local accounts unless admin deliberately provisions an explicit, audited identity-linking feature later. No automatic email-based merging or privilege inheritance.

- Local-email accounts store exactly one normalised unique login email. Validate full address syntax but do not assume a mail transport or automatic email verification exists; admin is responsible for verifying identities. Display name is distinct from email. Local password change/reset routes apply only to local users, not AD passwords.
- Directory users use a UUID application principal for all ownership/ACL/audit references, and a domain-scoped immutable AD SID for login identity binding; account name, UPN and email are mutable display/search attributes. Never use UPN or email alone to transfer project ownership.
- At most one account may be bound to a given `(directory_id, object_sid)`. Bindings are created/changed only by admin after an authenticated directory lookup; account rebinding requires explicit audit and collision/ownership safeguards.
- AD users do not have application password hashes or app-managed password resets. When the domain is unavailable, the AD login fails with a generic actionable service-unavailable message; it must not fall back to accepting cached credentials or the user's local-email password. The `admin` login remains operational.
- Only administrator-created users may log in. Successful directory authentication is **not** permission to auto-register/join projects. New users are `role=user`; AD groups never confer built-in app admin rights in this release.

### 5.3 Directory configuration and binding

Use `ldap3` as the cross-platform LDAP client, behind an `IdentityProvider`/`ActiveDirectoryAdapter` abstraction. Support one or more explicitly configured AD directory profiles, each with domain/NetBIOS aliases, LDAP server FQDNs, connection timeouts, Base DN and optional service lookup identity. An admin may configure and test each profile without exposing secrets to the browser.

**Security rules:**

1. Require **LDAPS or StartTLS with certificate-chain and hostname validation**. A non-TLS simple bind and disabling verification are forbidden in production. Store service account credentials in the same encrypted server secret store as bibliographic API keys; recommend a read-only directory lookup service identity. Set finite connect/read timeouts, safe referral policies and explicit server allowlists.
2. Locate candidate users via read-only LDAP query (escaped filter values, allowlisted attribute names, minimum requested attributes). Resolve `sAMAccountName`, `userPrincipalName` and `objectSid`. Use an exact match of eligible account and domain; reject ambiguous matches. Check status/disabled/lockout indicators as available.
3. Verify the supplied password using an AD-supported authentication bind over a validated TLS channel for the resolved user. Never save, log, replay or use the supplied password after the request. Reject empty passwords; do not permit anonymous bind to count as success. Ensure connection cleanup in success/error paths. Do not blindly trust caller-supplied DN, LDAP filters, SID or domain.
4. After successful bind, map `directory_id + objectSid` to one active pre-provisioned application user; no such binding means **access denied**, even if the AD password is correct. Return equivalent generic error responses for unknown user, incorrect password and disabled account to reduce account enumeration.
5. Capture `last_directory_sync_at` and refresh directory account eligibility periodically for active AD sessions (configurable short validation interval, proposed 15 minutes). On detected disable/rebind/delete, revoke application sessions. If directory status cannot be revalidated after the configured grace interval, deny privileged mutations and require reauthentication; do not fail open indefinitely.
6. Explicitly mark missing domain connectivity and mismatched certificate as different *admin diagnostic events*, but do not reveal internal directory details on login responses. Log safe metadata (provider, resolved app user ID when known, outcome), not credentials or full LDAP payloads.
7. Treat AD account names case-insensitively for lookup where AD semantics require it, while preserving original display spelling. Cross-domain unqualified names are rejected unless unambiguous. Support `DOMAIN\samAccountName`, UPN, and a bare `samAccountName` only where configured and unambiguous.
8. No browser-integrated Windows SSO/Kerberos is required for v1.1. This is a username/password login form authenticated against AD, not automatic desktop-domain login. Windows SSO can be considered as a future adapter.

### 5.4 JWT sessions and authorization

Use Flask-JWT-Extended JWT access cookies (`HttpOnly`, `Secure`, `SameSite=Lax` or `Strict`) and CSRF double-submit protection on unsafe methods; Axios sends `X-CSRF-TOKEN`. Keep short-lived access credentials, optional narrow-path refresh cookie, rotating/revocable refresh tokens and explicit logout. JWT identity is the immutable application user UUID, with a `provider` claim for session review; never treat a login name or AD group as authorization by itself.

On protected requests, check account active state, session version, authentication-policy revision and project ACL. Disabling an account, changing permitted auth methods or revoking project permission must take effect promptly. Throttle login attempts per account/IP; audit admin logins, provider configuration changes, directory binding changes, login failures and account disablement. Never store JWTs in localStorage/sessionStorage.

The built-in administrator can create/disable accounts and reset **local** passwords but cannot automatically open private projects through ordinary research APIs. Admin's authority over backups, restore and host files is a separate high-privilege data-access boundary that must be disclosed and audited. Account disablement does not delete projects; ownership recovery is a separately approved, audited procedure.

### 5.5 Admin settings and user provisioning UX

**Admin → Authentication:** provider toggles, directory profiles (domain, servers, LDAPS/StartTLS, CA trust, Base DN, lookup service account), password policy, connectivity test with sanitised error, session expiry/revalidation settings and audit history. Disallow disabling both ordinary login methods without a clear warning; `admin` remains usable regardless.

**Admin → Users → New account:** choose `Local email` or `Active Directory`. For local users, enter unique email, display name and secure initial password/reset workflow; for directory users, choose domain and search/resolve the AD account, confirm the displayed SID-derived identity, create the mapped user and assign no application password. Show provider as read-only after provisioning except via explicit admin migration, with confirmation about ownership and ACLs.

**Login:** selectable `Email address` and `Active Directory` forms based on enabled providers, plus a distinct `Administrator` choice accepting the fixed username `admin`; no user self-registration. Login failure uses neutral messaging; service-down diagnostics appear only to admin. `/auth/me` returns provider and app user UUID for frontend rendering.

The login endpoint always receives an explicit `provider` field; illustrative request bodies (do not return credentials in responses):

```json
{"provider":"local_email", "identifier":"alice@example.org", "password":"<user-supplied>"}
```

```json
{"provider":"active_directory", "identifier":"CORP\\alice", "password":"<user-supplied>"}
```

```json
{"provider":"admin_local", "identifier":"admin", "password":"<admin-supplied>"}
```

The `admin_local` provider must reject any identifier other than the literal `admin`; other providers must reject that reserved bare identifier. Never accept a `role`, `user_id`, `directory_sid` or arbitrary LDAP server address supplied by the caller as proof of identity. Login methods are server-configured, not client-controlled flags.


### 5.6 Shared bibliographic API credential precedence (unchanged)

For each bibliographic provider: (1) enabled personal credential for the current job requester, if present; (2) enabled administrator global credential; (3) none. UI shows origin (`personal`, `shared`, `not configured`) but not secret. Credential management is independent of whether the account uses local-email or AD authentication. Job runs persist the credential scope for provenance but never the secret itself.

## 6. Project sharing

Visibility states: `private`, `public_view` and `public_edit`, visible in a clear owner-only sharing screen. Public means any **authenticated** enabled account. Public edit requires an explicit warning and confirmation. Owner can additionally invite/grant/revoke per-user `viewer` or `editor` and apply explicit `deny`; ACL policy in Section 1 is authoritative. Show effective permissions and a full change log. Editors can run outbound API searches using their own credential override, otherwise shared defaults; never use the owner's personal secret on an editor's behalf. Background jobs recheck permissions before starting and before persisting results. Conflict detection is mandatory for collaborative edits and screening resolutions.

## 7. Keyword strategy and source-specific queries

### 7.1 Strategy editor

Editable groups of terms/phrases, OR within groups, AND between groups, nested AND/OR/NOT groups, quotation, year range, publication types, language, optional subject scope, and source selection toggles. Provide keyword synonyms and an exclusion group. Allow preview, manual source-specific override, test count (if available) and an explanation of what cannot be translated. Preserve AST, generated query, user override, actually executed URL/parameters, query compiler version, access scope, search timestamp and export checksum.

**Canonical AST example**:

```json
{
  "op": "and",
  "children": [
    {"op": "or", "terms": [{"type": "phrase", "value": "digital twin"}, {"type": "phrase", "value": "machine learning"}]},
    {"op": "or", "terms": [{"type": "phrase", "value": "mineral processing"}, {"type": "term", "value": "flotation"}]}
  ],
  "filters": {"year_from": 2015, "year_to": 2026, "document_types": [], "languages": []}
}
```

### 7.2 Compilers

- Scopus: compile appropriate `TITLE-ABS-KEY(...)` plus valid Scopus `PUBYEAR` filters and supported source filters; escaping and wildcard syntax must be tested.
- WoS: compile `TS=(...)` and a valid publication-year filter; API Expanded request is constructed against the versioned, configured endpoint. Validate supported query operators and API entitlement.
- OpenAlex: compile boolean expression for supported `search.title_abstract_keywords` and appropriate work filters with URL encoding; store exact scope/semantics. OpenAlex may use broader search/keyword semantics, so do **not** promise identical recall across sources. The request URL has a finite length; split only in a mathematically equivalent manner (e.g. partition OR branches and take union), **never** split AND operands and union them. For untranslatable logic, require an explicit warning/error, not silently broaden results.

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

Each adapter must preserve raw payload, response schema/version, original query and pagination state. Map errors to typed codes (`AUTH_REQUIRED`, `ACCESS_DENIED`, `INVALID_QUERY`, `RATE_LIMITED`, `SOURCE_UNAVAILABLE`, `PARTIAL_RESULTS`, `UNSUPPORTED_FILTER`, etc.). Use bounded retries and exponential backoff for retryable failures only. Prevent outbound SSRF: endpoints/hosts hardcoded or allowlisted by provider config, no arbitrary URLs from users.

**OpenAlex:** PyAlex/HTTPS REST, published-date filters, relevant metadata and cited work IDs, rate-limit compliance, cursor pagination; report records lacking abstracts or references. Use configured API key when required/available.

**Scopus:** pybliometrics plus manual CSV/BibTeX. Access is contingent on Elsevier API entitlement and export policies. Search by EID and source metadata, preserve references if available.

**Web of Science:** Clarivate **API Expanded** HTTP adapter, not deprecated WoS Lite. Support official WoS export formats (BibTeX/plain text) with validation when no API access is available.

**Manual import:** Upload `.bib`, `.ris`, `.csv`, documented WoS `.txt`, and OpenAlex JSON. Validate file format, sizes, encoding, duplicates, content security and schema; identify source and import event. Imports create provenance-preserving source runs and participate in PRISMA counts. Treat licensed record files as restricted when exporting.

Every source run saves `reported_count`, `retrieved_count`, `complete|partial`, status, errors, retrieval start/end, identifiers, count of missing required fields, a checksum and exact query. API counts are **not** evidence that all records were actually retrieved. Users may choose a corpus only with an explicit acknowledgement if any source run is partial.

## 9. Background jobs and process safety

Place queue metadata in `catalog.sqlite` so idle workers can find jobs without scanning every project DB. Run a **separate worker process**, not Flask request threads. On startup, reclaim expired leases and idempotently retry/reconcile jobs. Jobs support `queued`, `running`, `partial`, `completed`, `failed`, `cancelling`, `cancelled`, have user/project identity, structured progress and log correlation ID. Use lease expiration/heartbeat, job idempotency keys and bounded retries. A job may be cancelled at checkpoints, not by corrupting an open database transaction.

Only one mutating operation may hold a write lease for a project at once (search import, dedup merge, screening bulk update, etc.). Read-only analyses should run on consistent snapshots and can be parallelised within CPU/memory limits. Use WAL, `PRAGMA foreign_keys=ON`, busy timeouts, short transactions, bounded thread-safe SQLAlchemy sessions, explicit SQLite backup API for live snapshots. Avoid writing to project DB concurrently from arbitrary background threads. Enforce per-user and global concurrency and quota budgets. Return `202` with a job ID for nontrivial operations; Vue polls `/jobs/{id}` (2–5s, slower in background tabs).

## 10. Normalisation and deduplication

Raw source records are append-only. Canonical `works` keep title, abstract, dates, DOI, language, document type, journal, authors, affiliations, keywords, source-specific citations, and cited references. Preserve **field-level provenance**, conflicts and retrieval date. Never sum Scopus/WoS/OpenAlex citation counts as if unique; display them with source/date and clearly label derived summaries.

Dedup stages: normalized DOI; other persistent IDs; normalized exact title with year/authors; fuzzy candidate matching with RapidFuzz; manual review of uncertain cases. Different conference and journal versions may be distinct. Provide compare/merge/reject/undo UI and auditable merge events. Mark work-to-source membership to calculate source overlap and PRISMA removal counts accurately. A merge must not destroy original raw records or historical review decisions.

## 11. Full PRISMA screening

- Support review protocols with research questions, inclusion/exclusion criteria, review type, scope dates, databases and search dates. Preserve immutable protocol versions.
- Identification uses source-run provenance and reports source-specific retrieved records, removed duplicates and additional identified records.
- Title/abstract stage includes `include`, `exclude`, `uncertain`, notes and structured reason codes; configurable single or dual independent reviewers and adjudication. Decisions are independent reviewer events; conflicts require a resolution record.
- Eligibility includes status of reports sought, retrieved/unavailable, full text reviewed and explicit reason(s) for exclusion. Works, reports and studies are different entities; don't assume 1:1 for every study.
- Support PDFs/attachments uploaded by authorised users with storage limits and validated MIME/content. Application does not circumvent paywalls; an external link may be stored instead.
- Frozen corpus contains an immutable set of included work/study IDs, inputs, review protocol, full screening-resolution ledger and SHA-256 for reproducibility. Later edits create a new version; completed analyses refer to the original snapshot.
- PRISMA count engine derives counts from recorded events and stages. Allow manual corrections only as separately recorded, justified adjustments. Validate conservation/reconciliation before diagram generation. If no full-text screening was conducted, do not fabricate that stage or claim full systematic-review compliance.
- Use `prisma-flow` to generate SVG/JSON/PNG (when available), plus machine-readable exclusion table. Distinguish PRISMA 2020 guideline from bibliography mapping, and provide disclosure text in reports.
- Optional ASReview interoperability: export deduplicated screening input CSV, import labelled results with work IDs and reviewer provenance, require human adjudication. Do not imply AI prioritisation guarantees complete recall.

## 12. Bibliometrics, analytical provenance and reports

Primary engine: **Biblium**, integrated through an internal `BibliometricsEngine` adapter. Validate engine capabilities at runtime, pin version, and provide tested pandas/NetworkX fallback for essential calculations. Do not call undocumented Biblium interfaces without a smoke test. Make optional PyBibX and BibFusion connectors replaceable and licence-gated.

Required analyses:

1. Annual publication counts and trends.
2. Productive authors, journals/sources, institutions and countries.
3. Citation rankings with source/date, citations per year and coverage warnings.
4. Coauthorship collaboration networks.
5. Keyword frequency and co-occurrence networks.
6. Co-citation network (only when cited references are available).
7. Bibliographic coupling (only when cited references are available).
8. Topic clusters and temporal keyword/thematic evolution.
9. Source/database overlap and metadata completeness.
10. Research maturity review table using optional human-labelled validation categories (theoretical, simulation, historic data, pilot, industrial advisory, closed-loop, sustained industrial use). These are annotations, **not** conclusions that can be inferred automatically from counts.

Expose thresholds, normalization, network type, similarity measure, clustering parameters, time slicing, keyword dictionary version and graph size. Explicitly fail or warn if prerequisite fields are absent. Outputs include paginated tables, interactive graphs (zoom/filter/hover/select), SVG/PNG/CSV/JSON export, and a versioned HTML report with methods, sources, limitations and methodological notes. Never treat citation counts as direct quality scores. Every artifact records corpus hash, parameters, engine/software versions, timestamp, creator and file checksum.

## 13. Frontend information architecture

- **Setup/Login:** gated fixed-`admin` bootstrap page; login-method selector (Email / Active Directory / Administrator); local password change only for local users; login/logout.
- **Home:** owned projects, shared-with-me projects, all registered-visible projects, filters, cards/tables, create button, recent jobs.
- **New project wizard:** title, aims, keywords, date/document types, selected sources, review mode.
- **Project workspace tabs:** Overview; Search strategy; Source queries; Search history/results; Normalise & duplicates; Protocol; Screen titles/abstracts; Full-text eligibility; PRISMA; Bibliometrics; Reports; Files; Sharing; History/settings.
- **Search editor:** draggable/editable Boolean groups; enabled sources as switches; generated/override query panels; warnings/test counts; dry-run and execute; validation/credential status.
- **Records:** server-paginated filterable table, record detail drawer, per-source provenance, citations, reference lists, source overlaps.
- **Dedup:** side-by-side candidate pairs and confidence reasons; accept/reject/undo; bulk safe-actions.
- **Screening:** keyboard shortcuts; independent reviewer decisions and reconciliation; exclusion reasons; progress and per-stage counts; full-text availability and attachments.
- **PRISMA:** stages/counts, validation diagnostics, preview SVG, download.
- **Bibliometrics:** corpus selector, parameter form, dashboard and graph view, sortable tables, downloaded artifacts.
- **Sharing:** private/public-view/public-edit selector with warning, explicit ACL editor; audit feed and permission preview.
- **Export:** ZIP export job with progress and authenticated download.
- **Admin:** user creation (email or pre-provisioned AD), selectable authentication modes, AD directory configuration/connection test, shared API keys/status, hostname/proxy information, scheduled full-backup configuration/status/history/manual trigger/retention, migration/restore controls, logs/job health (no secret values displayed).

Use Vue 3 Composition API supported by browser global build, organise components as ES modules with `setup()` or options objects; no `.vue` SFC files. Axios instance uses same-origin `/api/v1`, credentials, CSRF interceptor, typed API error conversion. Client route state via URL/history API and server SPA fallback. Server-side pagination/filtering for larger corpora (e.g. 50,000+ works). Include keyboard navigation, accessibility labels, responsive layout, job progress, loading/retry/error/empty states and confirmation for destructive actions. Avoid rendering untrusted bibliographic HTML (`v-html` prohibited for metadata).

## 14. REST API contract

All routes begin `/api/v1`, return JSON except protected binary downloads, use UUIDs, structured error codes, UTC ISO-8601 times, pagination and `If-Match` for conflicts. Version schemas with OpenAPI and request/response models (Marshmallow/Pydantic or explicit equivalent) without replacing Flask/SQLAlchemy.

| Method | Path | Purpose |
|---|---|---|
| GET | `/setup/status` | Whether admin setup required; no secrets |
| POST | `/setup/admin` | One-time admin bootstrap, local bootstrap token required |
| POST | `/auth/login`, `/auth/refresh`, `/auth/logout` | JWT-cookie session operations |
| GET | `/auth/me` | User identity and permissions |
| PUT | `/auth/password` | Change password and revoke old sessions |
| GET,POST | `/admin/users` | Admin list/create local-email or bound AD users |
| PATCH | `/admin/users/{user_id}` | Admin disable/reset/update; AD passwords cannot be reset here |
| GET,PUT | `/admin/auth-settings` | Read/change enabled ordinary login providers; `admin` unaffected |
| GET,POST | `/admin/ad-directories` | Admin list/add directory profiles; sanitize all secret fields |
| PATCH,DELETE | `/admin/ad-directories/{directory_id}` | Update/disable directory profile with binding safeguards |
| POST | `/admin/ad-directories/{directory_id}/test` | Secure LDAPS/StartTLS connectivity and certificate test |
| POST | `/admin/ad-directories/{directory_id}/resolve-user` | Lookup prospective AD identity for manual pre-provisioning |
| GET | `/auth/methods` | Enabled public login methods; always expose Administrator choice |
| GET,PUT | `/admin/source-credentials/{provider}` | Global source secrets/status |
| GET,PUT | `/me/source-credentials/{provider}` | Personal overrides/status |
| GET,POST | `/projects` | List authorised projects / create |
| GET,PATCH,DELETE | `/projects/{project_id}` | View/update/delete |
| GET,PUT | `/projects/{project_id}/sharing` | Public mode and per-account ACL |
| GET,POST | `/projects/{project_id}/protocols` | Protocol revisions |
| GET,PUT | `/projects/{project_id}/search-strategy` | Keyword/group current draft |
| POST | `/projects/{project_id}/queries/preview` | Per-source compilations, warnings |
| GET,POST | `/projects/{project_id}/search-runs` | History / launch async search |
| GET | `/projects/{project_id}/search-runs/{run_id}` | Status/count/completeness |
| POST | `/projects/{project_id}/imports` | Source file upload + background import |
| GET | `/projects/{project_id}/records` | Search/sort/filter/paginate |
| GET | `/projects/{project_id}/records/{record_id}` | Detail/source provenance |
| GET | `/projects/{project_id}/duplicates` | Candidate queue |
| POST | `/projects/{project_id}/duplicates/decisions` | Merge/reject/undo |
| GET,POST | `/projects/{project_id}/screening/decisions` | Retrieve/add reviewer decisions |
| POST | `/projects/{project_id}/screening/resolutions` | Final arbitration |
| POST | `/projects/{project_id}/reports/attachments` | Upload full-text report securely |
| GET,POST | `/projects/{project_id}/corpora` | List/freeze corpus versions |
| GET | `/projects/{project_id}/prisma/{corpus_id}` | Validated counts/stages |
| POST | `/projects/{project_id}/prisma/{corpus_id}/export` | Generate SVG/JSON |
| GET,POST | `/projects/{project_id}/analyses` | List/start analyses |
| GET | `/projects/{project_id}/analyses/{analysis_id}` | Analysis status/config/results |
| GET | `/projects/{project_id}/artifacts/{artifact_id}` | Authorised artifact retrieval |
| POST | `/projects/{project_id}/exports` | Enqueue ZIP export |
| GET | `/projects/{project_id}/exports/{export_id}/download` | Secure ZIP download |
| POST | `/projects/imports` | Owner imports previously exported project ZIP |
| GET | `/jobs/{job_id}` | Progress/state/log summary |
| POST | `/jobs/{job_id}/cancel` | Idempotent cancellation |
| GET | `/health/live` | Minimal unauthenticated liveness |
| GET | `/health/ready` | Admin-only detailed readiness |
| GET,PUT | `/admin/backups/settings` | Admin view/configure schedule, server-side destination and retention |
| POST | `/admin/backups/test-destination` | Check destination permissions, disk/share reachability; avoid arbitrary file read |
| GET | `/admin/backups/runs` | History, size, file name, validation and failure status |
| POST | `/admin/backups/run` | Enqueue a full on-demand backup using configured settings |
| POST | `/admin/backups/{run_id}/verify` | Verify archive manifest, checksum and decryptability without live overwrite |
| POST | `/admin/backups/{run_id}/restore-check` | Dry-run backup restore validation; no live changes |

For a long job: `POST` returns `202 Accepted` with `{job_id,status,links:{status}}`. Standard errors include `VALIDATION_ERROR`, `UNAUTHENTICATED`, `FORBIDDEN`, `CONFLICT`, `AUTH_PROVIDER_DISABLED`, `DIRECTORY_UNAVAILABLE`, `AD_IDENTITY_AMBIGUOUS` (admin configuration only), `SOURCE_ACCESS_DENIED`, `SOURCE_RATE_LIMITED`, `SOURCE_PARTIAL`, `JOB_FAILED`, `BACKUP_DESTINATION_UNAVAILABLE`, `BACKUP_VALIDATION_FAILED`, `EXPORT_RESTRICTED`; include stable `request_id` and no stacktrace/private key.

## 15. Export/import and archival

### Complete ZIP export

Owner requests export; create a consistent database snapshot through SQLite backup API after coordinating writers (never raw-copy an open SQLite/WAL file), freeze artifact inventory, calculate SHA-256 hashes, and ZIP **only** the selected project's data. Include `manifest.json`, `project.sqlite`, `sources`, `imports`, `attachments`, `reports`, `figures`, `metadata/provenance.json`, `metadata/checksums.json` and licence/reuse notice. Exclude source credentials, admin/user catalogue, JWTs, OS secrets, private runtime logs, caches, temp files and unrelated projects. Use the canonical `litfoundry_project_<project_uuid>_<YYYYMMDD_HHMMSSZ>.zip` download name and include `product`/`product_name` branding in the manifest. Provide export history, timestamp, archive format version, schema version and source-analysis provenance. Do not mutate the live project or store absolute machine paths in the archive. Enforce owner permission again on download; avoid unauthenticated permanent URLs.

### Import/restore

Treat ZIP as untrusted: validate size and file count, entry types, path traversal, symlinks, compression bombs and manifest/checksums. Stage extraction in a quota-limited temporary directory, migrate included `project.sqlite` if needed, rekey **project UUID and owner ID** for the importing account, preserve original reviewer attribution as non-login provenance (map foreign reviewer IDs to imported reviewer labels), reset ACL/public visibility to private, clear job leases and never import credentials. Atomically register the new project in the central catalogue. Preserve original provenance IDs in explicit imported-from fields; do not overwrite existing projects. Include import/export roundtrip tests. Export licensed-source raw records only with an explicit rights warning; offer metadata-only export if contractual terms require it.

## 16. Administrator-managed scheduled full-installation backups

**Scope and distinction:** Project ZIP exports in Section 15 remain owner-controlled, single-project portability files. This section specifies an entirely separate **administrative full-system backup** of the central catalogue, **every project folder/database regardless of sharing permission**, and all persistent installation data needed for disaster recovery. Backups are privileged snapshots, not public downloads and not project exports.

### 16.1 Configurable schedule and destination

Admin → Settings → Backups must provide all controls below; no non-admin API or UI is permitted to change them.

| Setting | Type / validation | Default or rule |
|---|---|---|
| `enabled` | Boolean | Disabled until an admin explicitly configures a destination and recovery passphrase |
| `frequency` | `daily`, `weekly`, `monthly` | Propose daily; prevent unsupported/invalid recurrences |
| `local_time_hhmm` | `HH:MM`, 24-hour | Admin-selected time, e.g. `23:00` |
| `iana_timezone` | IANA identifier, e.g. `Africa/Johannesburg` | Server's detected timezone, display explicitly |
| `weekday` / `monthday` | When required by frequency | Valid weekday or 1–28 day-of-month to avoid ambiguous skips |
| `destination_server_path` | Absolute **server-side** folder path, supports Windows UNC (`\\server\share\folder`) and mounted Linux/macOS directories | Must not be beneath application data/projects or staging, or equal to archive input paths |
| `retain_count` | Integer ≥ 1, admin-specified maximum number of **verified successful** full-system backups at this destination | Suggest 7 as first-run value |
| `encryption_secret_ref` | Protected secret-store reference for a recovery passphrase | **Required** for scheduled full backups containing secrets |
| `include_logs` | Boolean | On by default for complete operational recovery; redact secret material in logs |

Server machine OS permissions determine writable paths. A browser folder chooser cannot pick a server filesystem location reliably: provide a text path field plus **Test destination**; show resolved server path, status, free space when available and last successful write test. Do not accept upload paths, arbitrary URL schemes or destinations under the managed project tree. For Windows Services prefer UNC shares over mapped drive letters; document service identity and SMB permissions. For Linux/macOS mounted volumes document path availability after reboot and credentials. A network share **may store ZIP backups** even though live SQLite files must remain on local disk. Prevent backup loops by excluding previous backups, backup staging, imported archives and temp files from archive inputs.

Illustrative administrator settings payload (all properties validated; encryption secret handled through a write-only protected input rather than returning it):

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

For Windows, use a native absolute path or UNC share; do not interpret the example Linux path as mandatory. The backend must return a redacted status rather than a recovery passphrase. Explicit schedule edits reset/recalculate the next due occurrence and record policy revision.

Date/time filenames must be safe across Windows, Linux and macOS and include a collision-resistant suffix:

`litfoundry_full_YYYYMMDD_HHMMSSZ_<run_uuid_short>.zip`

For example `litfoundry_full_20261019_230000Z_a94fc21e.zip`; the timestamp is **UTC** and must match `manifest.json`. Store human-readable local schedule and UTC execution time in the run record. Never place `:` in filenames.

### 16.2 Scheduling engine and duplicate-run prevention

Use a built-in scheduler coordinator in a **single elected worker/supervisor process** (or a vetted scheduler such as APScheduler wrapped by an application-owned lease). Persist the recurrence definition and `next_due_at_utc`/`last_attempted_at_utc` state in the central catalogue. Never register a new in-memory recurring job separately in every Waitress worker or every background worker.

At each due time, atomically acquire an expiring/fenced global `full-backup` lease in `catalog.sqlite`; create one `backup_runs` entry and enqueue a `system_full_backup` job. Use a unique schedule-occurrence key to prevent duplicate backups after service restart, clock adjustment or multiple worker processes. Scheduled backups execute with the **system service identity**, even if no administrator is logged in; the authenticated admin identity is only required for configuration and manual requests. Do not put encryption passphrases in job arguments or logs.

Define missed-run behavior: after downtime, trigger **at most one** overdue backup at service restart (configurable grace), advance next due time, and show skipped occurrences in the admin log; no uncontrolled catch-up burst. Handle daylight saving time gaps/duplicates deterministically (run once for a due local day, record computed UTC). Enforce one full backup at a time; prevent simultaneous schema migration, full restore and competing maintenance operations.

### 16.3 Consistent full snapshot and ZIP creation algorithm

A full backup must be consistent across the **central catalog, all per-project SQLite DBs, their file trees and relevant secrets**. A Python `shutil.copyfile()` of a live WAL-mode `.sqlite` file is **not acceptable**. Use `sqlite3.Connection.backup()` for each database.

1. Allocate `backup_run_id`, determine the complete input inventory of all `ready` and transitional projects, and verify path containment. Record active running jobs, schema/app versions and source archive provenance policy.
2. Acquire a **global application-level write barrier** preventing new mutations in any catalog/project database and persistent project file store; pause/reschedule workers and web mutating routes at safe transaction boundaries. Coordinated application writes, including uploads, must respect this barrier. If jobs cannot be quiesced within a configured timeout, fail safely without pruning previous backups. Reading can continue where consistent.
3. Under the write barrier, create consistent SQLite snapshots with the SQLite online backup API, including `catalog.sqlite` and **all** per-project `project.sqlite` databases. Run `PRAGMA integrity_check` on snapshots. Stage immutable copies of all persistent project artifacts, raw records, imports, attachments, figures, reports, exports, manifests, administrative non-secret configuration files and relevant operational logs. For complete cross-database/file consistency, **do not release the barrier until a point-in-time file snapshot is frozen**. A direct copy is acceptable for immutable artifacts or coordinated file writes; if files can change, copy all under the barrier or use a proven filesystem snapshot facility. Do not assume SQLite backup alone makes files consistent.
4. Include encrypted server secret-store material required to restore shared/per-user API keys, AD lookup credentials and JWT/signing/encryption configuration, in a portable re-importable representation. Do **not** rely exclusively on machine-bound Windows DPAPI/keychain credentials: cross-machine disaster recovery must be possible with the archive and separate passphrase. Never include uncontrolled OS private keys or TLS-CA private keys unless a documented organisational policy explicitly authorises them; document required external CA/hostname reconfiguration.
5. Release the write barrier **only after** the complete staged snapshot is frozen and verified. Resume normal jobs promptly. Package the snapshot in a timestamped ZIP **outside** any input path. ZIP assembly/compression and copying to the destination should occur outside the barrier. Record snapshot start/finish UTC times and consistency marker.
6. Create an archive `manifest.json` with `product="litfoundry"`, `product_name="LitFoundry"`, format version, run ID, source hostname, app version, UTC timestamp, catalogue/project schema versions, all project UUIDs and paths, inventory sizes, and SHA-256 checksums for every included file. Include `backup_metadata/checksums.json`, `backup_metadata/configuration.json` (safe metadata), audit provenance, and a restore README. Archive entries use relative safe paths only.
7. Encrypt all ZIP entries using **AES-256 WinZip AES format** (e.g. verified `pyzipper.AESZipFile` with `WZ_AES`, `nbits=256`). Secure full-system backup encryption is mandatory; no `ZipCrypto`, plaintext sensitive entries or passwords embedded in the ZIP. Warning: stock Windows Explorer or Python `zipfile` may not support WinZip AES; the application restore command **must** support this format. Password-based ZIP encryption is only as strong as the recovery passphrase; enforce a high-entropy passphrase and require that the admin save it in an offline/independent secure location. Store only an encrypted passphrase reference/credential in the host secret store for unattended backups, not cleartext config/SQLite. The archive may reveal filenames/metadata in ZIP headers; if filename confidentiality is required, provide a future whole-archive encryption mode.
8. Write archive initially to a `.partial` file **in the target directory** (or a controlled local staging destination if network share limitations require), flush and close it, verify it can be reopened/decrypted and compare archive payload checksums to the staged manifest. Recompute final ZIP SHA-256. Rename to final `.zip` on the destination filesystem when possible, verify its existence/readability and log size/checksum. Persist completed run only after verification. Remove stale `.partial` files in a separate housekeeping pass.
9. Destroy secure staging copies using normal best-effort file deletion after successful/failing execution; document SSD/filesystem secure-deletion limitations and restrict staging permissions. Stage beneath an OS-protected directory with quotas and disk-space checks. If source archive content violates a Scopus/WoS redistribution policy, present the admin a compliance warning; system backup for disaster recovery is not automatically permission for external publication or redistribution.

If a required database/file is missing, damaged or unreadable, **fail the backup** rather than silently omitting a project. Record a redacted error and alert the admin within the application (optional system email notifications are future enhancement). Preserve all prior valid backups. Track storage consumption and avoid unbounded temp data.

### 16.4 Retention, rotation and failure handling

- Rotate backups only **after** a new full backup is successfully created, decrypted/verified, and committed as `completed`. If the new job fails at any point, do not delete any older backups.
- Retain the most recent `retain_count` verified successful full-system archives that were created by this application **for the same configured destination and backup series**; sort by UTC creation/run timestamp, not filename lexical quirks. Delete older archives only if they match the managed backup catalogue and manifest/run-ID identity. Never delete unrelated `.zip` files or files in subdirectories.
- If retention is lowered by admin, preview the count and affected managed archives. Defer deletion until the next successful run or a separately confirmed **Prune now** operation that first checks existing good archives. Failed/partial archives do not count towards successful backup retention; clean orphan `.partial` files under a separate age threshold after confirming no run owns them.
- On destination/share unavailable, full disk, missing encryption key, bad passphrase, timeout, consistency lock conflict or corrupt archive, set `failed`, preserve older backups, publish an admin-visible warning on the dashboard and status endpoint, and retry only according to configured bounded policy. Do not claim success before final verification.
- A destination change begins a new retention series by default; never automatically delete backups from an old destination. Changing retention requires administrator authorisation and creates an audit event. Never delete the only valid restore point unless an admin explicitly confirms a recovery-impact warning.
- Record last attempt, last success, next due, duration, archive bytes, backup size, number of projects, checksum and error summary in Admin → Backups. Offer **Run backup now**, **Test destination**, **Verify backup**, **Download manifest**, and a guarded **Prune now**. Non-admin users must not learn filesystem paths, backup inventory or system data.

### 16.5 Restore and disaster-recovery workflow

Implement host-side `litfoundry backups list|verify|create`, `litfoundry restore --archive PATH --dry-run`, and `litfoundry restore --archive PATH --confirm` CLI commands, plus an admin GUI to inspect and dry-run verification. **Do not allow a web POST to replace live databases during normal Flask operation**; the actual restore runs in an exclusive offline/maintenance process with a human confirmation and an application outage warning.

Restore steps: (1) stop/pause Waitress, worker(s), backup scheduler and any live writers; (2) verify archive AES decryption using passphrase supplied securely, full checksum manifest, expected schema versions, path safety and decompression quotas; (3) stage extracted data outside live data root; (4) check SQLite `PRAGMA integrity_check`, foreign keys and application catalogue-to-project directory consistency; (5) optionally migrate copies using the supported migration coordinator; (6) create a safety backup of the existing data root; (7) atomically move staged installation data into place where the filesystem permits, otherwise use an explicitly rollback-capable staged replacement; (8) reinstate secret material into the destination OS secret store using the recovery passphrase, update host-specific Caddy/CA paths as necessary, revoke prior sessions where prudent and restart; (9) run post-restore smoke checks before accepting new writes. If any verification fails, preserve the original installation. Do not overwrite data during `--dry-run`.

Document restore-to-same-machine and restore-to-new-machine steps for Windows, Linux and macOS. Test with at least two users, shared AD configuration, multiple projects, original data files, shared API credentials and pending jobs (reset stale leases and prevent immediate uncontrolled job reruns). Clearly state that source API entitlements, organisation CA trust and AD connectivity depend on the new environment. Provide an admin-run quarterly restore-test reminder/status (no background notification required).

### 16.6 Backup test and acceptance matrix

- Enabling backups without destination, positive retention count, valid recurrence/timezone or encrypted recovery passphrase is rejected.
- Non-admin users cannot read/change backup settings, trigger full backup, see destination/path, view audit logs or perform restore by guessing API endpoints.
- Run a backup while another user edits a project, writes an attachment and a search worker adds records: snapshot reconciliation and `integrity_check` pass without a missing/mixed project manifest.
- Backup catalogue and every project folder/database are present, including disabled-user and private projects. Auth settings, directory identity bindings, and portable protected secret material are restorable.
- With scheduled daily/weekly/monthly mode, demonstrate due-time calculation, restart recovery, DST behavior, exactly-once occurrence and no duplicate run with two worker processes.
- Verify filename pattern and UTC timestamp against run metadata; test Windows UNC, Linux mount, macOS directory and unavailable destination with mocks/on-host fixtures.
- With `retain_count=3`, four successful backups leave three; a subsequent failed backup leaves the same three; unrelated ZIPs remain untouched; moving the destination does not prune the old destination.
- Deliberately corrupt an archive, project database or manifest, or supply the wrong password: verification fails, no backup is marked completed, retention does not run, live data unchanged.
- Full encrypted backup can be restored on a different OS host in test fixtures with the recovery passphrase; login modes, users, ACLs, per-project DBs, search data and reports persist and credentials remain protected.
- Automated integration tests cover backup locking, staging cleanup, pruning idempotency, interrupted `.partial` recovery, interrupted restore rollback, and password redaction in logs/configs/archive metadata.

## 17. Operational and security controls

- TLS on LAN, firewall restricted to trusted subnets, stable hostname and trusted CA. `Secure`, `HttpOnly`, `SameSite` cookies; CSRF on unsafe HTTP methods. Never run LAN production with Flask debug server or HTTP-only authentication.
- Restrict forwarded headers to configured reverse proxy; allowed-host and origin checks; CSP, clickjacking controls, MIME type headers, HTTPS-only redirect and no credentials in URL.
- Built-in `admin` with permanent local username and password, email-local/AD/both admin-selectable provider modes, Argon2id local passwords, LDAPS/StartTLS domain verification and account-to-SID binding, strong bootstrap, login throttling, admin-only registration, session invalidation, logout, audit of privilege changes.
- Encryption-at-rest of API secrets with separate master key; effective credential uses job requester's override, then shared; never owner's personal secret for editor jobs.
- Strict file upload/download authorisation; MIME and signature validation, size quotas, path containment, safe ZIP import. Optionally scan uploaded full-text files per organisation policy.
- External HTTP only to approved bibliographic API domains. TLS verification on outbound requests; retry timeouts. No arbitrary URLs, server-side HTML fetching or open redirects.
- No SQLite in cloud sync folders or direct network filesystems. System-wide **scheduled and manual AES-encrypted full ZIP backups**, all databases and persistent files, under a global write barrier with SQLite online snapshots, admin-only destination/schedule/retention settings, verified completion before rotation, and tested cross-platform offline restore; see Section 16.
- Logs use request/job/project IDs and structured safe summaries; redact secrets, auth tokens, raw full-text and search API credentials. Admin health endpoint requires authentication.
- Capacity budgets and quotas (projects/user, API calls, storage, archive size, jobs/user, workers). Configurable defaults with documented safe values.
- Handle process termination and machine reboot: leases expire, recover partial jobs, no phantom success, no orphaned catalogue entries; bounded data corruption risk.
- Provide security notes explaining that app-level project isolation is not an OS filesystem security boundary against a server administrator or compromised service identity.

## 18. Packaging and distribution

Development: `python -m venv`, `pip install -e .[dev]`, `litfoundry init`, `litfoundry serve`, `litfoundry worker`, CLI for migration, secure directory lookup tests, backup, and offline restore. Use `pyproject.toml` with the `litfoundry` console-script entry point and environment-driven `LITFOUNDRY_` configuration with sample `.env.example`; secret keys are **not** in `.env.example` or source control.

Release: package and sign distributions as **LitFoundry**, with executable/launcher name `litfoundry` and service identifiers `litfoundry-server` / `litfoundry-worker`. Use platform-native PyInstaller `onedir` packages for **Windows x86_64, Linux x86_64 and macOS arm64/x86_64** where CI runners are available. Build separately on each OS; do not assume cross-compile. Distribute launcher + Waitress/Flask + worker + static UI assets + migration scripts + licence inventory. Code signing/notarisation is strongly recommended for organisational deployment. Configure local data root outside immutable binaries (Windows `%PROGRAMDATA%\LitFoundry` or user app data for non-service mode; Linux `/var/lib/litfoundry` or XDG; macOS `/Library/Application Support/LitFoundry` or user Application Support); no SQLite database inside PyInstaller extraction directories. Choose explicit server vs workstation mode at installation.

Document HTTPS proxy setup and firewall configuration, AD controller/CA trust prerequisites, and the server service account's filesystem/UNC backup write access. Start/stop Flask, worker and optional Caddy via a single supervisor/launcher; include a service-install script for Windows Service (suitable wrapper), systemd on Linux and launchd on macOS. Caddy may be an independently installed prerequisite where packaging/certificate permissions complicate distribution. Verify launch on a clean machine for each platform, including fonts, plotting, migrations, SQLite and browser assets.

## 19. Testing and acceptance criteria

**Mandatory automated test groups:**

1. Bootstrap fixed username `admin`, token, concurrent first admin attempts, denial after setup, inability to rename/create a second app admin, Argon2id hash, local password reset/session revocation; `admin` always works when AD is down or local-email mode is off.
2. Local-email-only, AD-only and both-provider modes; distinct provider selection for email-looking UPN, unique emails and `directory_id + SID` bindings, pre-provision-only AD accounts, wrong-password/unknown-user/locked-out AD, TLS/CA failure, LDAP injection and login rate limits, directory outage, active-directory account disable/session revocation; then multiuser project ACL matrix including public_view, public_edit, explicit deny, revocation and forged URL/API access.
3. Per-project database location/URI checks; no cross-project read/write with forged UUID/path; creation/deletion recovery.
4. Central/project migration from prior fixture versions, backup, restart and failed migration recovery.
5. Query AST compiler fixtures (AND/OR/NOT, nested quotes, years, OpenAlex request length and equivalent query partitioning); disabled source produces zero calls.
6. API source adapter fixtures for success/auth failure/quota/pagination/partial/interruption; no live paid credentials in CI.
7. File import/normalise provenance, duplicate pair suggestions and reversible merges; conference/journal false positive case.
8. Dual reviewer screening, full-text retrieval, reasons, adjudication and PRISMA reconciliation, including metadata-only mode.
9. Analysis engine smoke tests with a small known network and deterministic counts; flag missing reference coverage; corpus hash/version reproducibility.
10. Background jobs run/cancel/reclaim/partial failure and permission revocation while queued.
11. Single-project ZIP export/import roundtrip (schema, hashes, artifacts, private default), traversal/zip-bomb rejection, secret exclusion, and separately **full-system encrypted scheduled backup** with all project DBs/files and catalogue, write-barrier consistency, verified archive, backup retention, corrupted/missing destinations and cross-platform offline restore.
12. Playwright end-to-end GUI: bootstrap fixed `admin`, admin selects email/AD/both and pre-provisions test accounts, local/AD login, admin sets backup schedule/path/retention and runs/inspects backup, user creates project, searches with fixtures, dedup, screen, PRISMA SVG, analysis, sharing, export/import, logout.
13. Packaging smoke tests on Windows, Linux and macOS; browser UI remains usable without external CDN internet access.
14. Security tests for CSRF, origin/host policy, auth on every download, XSS in imported titles and denial of unsafe file paths.

**Functional performance targets** (baseline, not guarantees): UI pages with 50,000 records use server pagination; typical project dashboard returns under 2 seconds on a modern LAN machine; no bibliographic API call blocks a Flask request thread; a failed source does not discard other sources' results; project files and results survive restart. Run load tests with multiple simultaneous viewers/editors and at least 10,000 source records as a first performance gate.

**Definition of done:** On a clean Windows, Linux or macOS host, a correctly branded LitFoundry installation can be started as a server; a unique built-in `admin` is created safely on first use and signs in locally regardless of enabled ordinary login methods; administrator can configure email-only, AD-only or combined sign-in and pre-provision both account types; at least two users access through separate LAN browsers over HTTPS; projects remain physically separate folders with project SQLite databases; public viewer/editor permissions operate as defined; searches/CSV imports, versioned deduplication, complete screening and PRISMA SVG work; bibliometric result and source provenance are reproducible; a project ZIP is exported and imported into a new private project; migrations, timestamped encrypted full-system scheduled backups to an admin-specified server-side location with configurable count-based retention, and full offline backup/recovery are verified; no user secrets leak into project exports or unencrypted logs.

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
    decisions.md
  src/litfoundry/
    app.py
    config.py
    api/              # Blueprints/request schemas only
    auth/             # email-local, reserved admin, Active Directory and authorization services
    catalog/          # shared SQLite models/repositories
    projects/         # project CRUD/engine routing/migrations
    queries/          # AST grammar and three query compilers
    sources/          # source adapters/import parsers
    processing/       # canonical records/dedup/provenance
    review/           # PRISMA/screening/corpus services
    bibliometrics/    # Biblium adapter + fallback/exports
    jobs/             # queue, worker, locks and progress
    export/           # per-project ZIP snapshots and imports
    backups/          # full system snapshot, encryption, schedule, retention, verify, restore
    cli.py
  migrations/
    catalog/
    project/
  frontend/
    index.html
    js/               # Vue 3 modules/component objects + Axios
    css/              # Tailwind source and built CSS
    vendor/           # exact version-pinned offline copies of Vue/Axios
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
  scripts/
  LICENSES/
```

Recommended milestones with mandatory passing tests after each:

- **M1:** Flask/Waitress/Caddy + Vue/Axios/Tailwind + catalog DB + fixed `admin` bootstrap, local email login, provider abstraction and first LAN HTTPS deployment.
- **M2:** Per-project folders/DBs + ACLs/public sharing + migrations + create/edit/delete + background workers; complete AD/LDAP adapter, configuration, admin user pre-provisioning, and login provider policy.
- **M3:** Keyword AST + three compilers + credential precedence + OpenAlex retrieval + manual import + Scopus/WoS adapters.
- **M4:** Record canonicalisation + field provenance + duplicate review + search run/corpus versioning.
- **M5:** Full screening/eligibility + reviewer arbitration + count validation + PRISMA SVG exports.
- **M6:** Bibliometric analytics + interactive visualisations + report and figure generation.
- **M7:** ZIP snapshot/export and safe import, **admin scheduled encrypted full-system backup, retention/verification, offline full restore**, cross-platform packaging, security and performance hardening. Include a backup foundation (consistent DB snapshots and job coordination) from M2 so it is not deferred until launch.

Codex should make small verifiable commits, update `docs/decisions.md` for unavoidable design details, and provide exact commands to run and test each milestone. M1 acceptance tests must verify the `LitFoundry` UI title/tagline, `litfoundry` CLI/import path, environment prefix and Caddy hostname example; M7 must verify branded export/backup filenames and archive manifests. Never report a milestone complete without tests and a short demonstration path.

## 21. Primary reference links (implementation verification)

- Vue CDN and production builds: https://vuejs.org/guide/quick-start.html and https://vuejs.org/guide/best-practices/production-deployment
- Waitress: https://docs.pylonsproject.org/projects/waitress/en/latest/
- Flask-Alembic: https://flask-alembic.readthedocs.io/en/stable/api/
- Flask JWT cookie CSRF: https://flask-jwt-extended.readthedocs.io/en/stable/token_locations.html
- LDAP3 AD bind/secure transport: https://ldap3.readthedocs.io/en/latest/bind.html and https://ldap3.readthedocs.io/en/latest/ssltls.html
- ldap3 licence (LGPL, commercial use): https://ldap3.readthedocs.io/en/latest/welcome.html
- Python SQLite online backup: https://docs.python.org/3/library/sqlite3.html#sqlite3.Connection.backup
- AES ZIP creation/recovery: https://github.com/danifus/pyzipper
- Caddy reverse proxy / internal CA: https://caddyserver.com/docs/caddyfile/directives/reverse_proxy and https://caddyserver.com/docs/caddyfile/options
- Apache ECharts: https://echarts.apache.org/handbook/en/basics/download/
- OpenAlex scoped Boolean search: https://help.openalex.org/api/searching/
- Clarivate WoS API Expanded: https://developer.clarivate.com/apis/wos
- Biblium: https://pypi.org/project/biblium/
- PyBibX: https://github.com/Valdecy/pybibx
- BibFusion: https://github.com/ladmepaz/bibfusion
- prisma-flow: https://github.com/osl-incubator/prismaflow
- PyInstaller commercial-use licence exception: https://pyinstaller.org/en/stable/license.html

