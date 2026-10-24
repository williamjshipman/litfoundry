# LitFoundry v1.3 → OpenSpec map

**Source of truth:** OpenSpec. The changes in `openspec/changes/` are authoritative, as are the main specs in `openspec/specs/` once archived. Where they differ from v1.3, OpenSpec wins. The `context` in `openspec/config.yaml` says so for every agent.

**Historical input:** `specs/litfoundry_codex_spec_v1_3.md`, which is kept for background and the section numbers cited below.

**OpenSpec root:** `openspec/`. Project-wide constraints are in `openspec/config.yaml`.

**Structure:**
- **Changes per milestone.** v1.3 §20 milestones M1–M7 are each split into one or more changes (`m1-*` … `m7-*`). SHOULD items from §0.2 are separate `post-v1-*` changes.
- **Main specs.** `openspec/specs/` stays empty until changes are implemented and archived.
- **Capability ownership.** Each capability is owned by exactly one change, so changes can be archived in dependency order without partial main specs.

## 1. Changes in implementation order

| # | Change | Milestone | Depends on | Capabilities (new) |
|---|---|---|---|---|
| 1 | `m1-platform-foundation` | M1 | none | `platform/product-identity`, `platform/data-root`, `platform/secret-storage`, `platform/server-deployment`, `platform/system-status`, `platform/operational-logging` |
| 2 | `m1-web-foundation` | M1 | 1 | `platform/api-conventions`, `platform/web-security`, `platform/web-shell` |
| 3 | `m1-local-identity` | M1 | 1, 2 | `identity/admin-bootstrap`, `identity/local-accounts`, `identity/sessions`, `identity/user-administration`, `platform/audit-log` |
| 4 | `m2-project-workspaces` | M2 | 1–3 | `projects/project-lifecycle`, `projects/project-storage`, `platform/schema-migrations` |
| 5 | `m2-project-access-control` | M2 | 4 | `projects/access-control`, `projects/sharing` |
| 6 | `m2-background-jobs` | M2 | 4, 5 | `platform/background-jobs`, `platform/write-coordination` |
| 7 | `m2-active-directory` | M2 | 1, 3 | `identity/directory-connection`, `identity/directory-sign-in`, `identity/directory-provisioning` |
| 8 | `m3-search-strategy` | M3 | 4, 5 | `search/search-strategy`, `search/query-compilation` |
| 9 | `m3-source-credentials` | M3 | 1, 3, 6 | `search/source-credentials`, `search/api-budgets` |
| 10 | `m3-search-runs` | M3 | 6, 8, 9 | `search/search-runs` |
| 11 | `m3-openalex-source` | M3 | 9, 10 | `search/openalex-source` |
| 12 | `m3-wos-starter-source` | M3 | 9–11 | `search/wos-starter-source` |
| 13 | `m3-source-file-imports` | M3 | 10 | `search/source-file-imports` |
| 14 | `m4-canonical-records` | M4 | 10, 13 | `records/canonical-records`, `records/keyword-normalisation` |
| 15 | `m4-deduplication` | M4 | 14 | `records/deduplication` |
| 16 | `m5-screening` | M5 | 15 | `review/review-protocols`, `review/screening` |
| 17 | `m5-full-text-eligibility` | M5 | 16 | `review/full-text-eligibility`, `review/attachments` |
| 18 | `m5-corpus-and-prisma` | M5 (part of M4) | 16, 17 | `review/corpus-snapshots`, `review/prisma-reporting` |
| 19 | `m6-bibliometric-analyses` | M6 | 14, 18 | `analysis/bibliometric-analyses`, `analysis/analysis-artifacts` |
| 20 | `m6-reports-and-visualisations` | M6 | 18, 19 | `analysis/interactive-visualisations`, `analysis/research-reports` |
| 21 | `m7-project-export-import` | M7 | 4, 6, 20 | `data/project-export`, `data/project-import` |
| 22 | `m7-full-backup-and-restore` | M7 | 4, 6, 21 | `data/full-backup`, `data/full-restore` |
| 23 | `m7-windows-distribution` | M7 | 1, 6, 22 | `platform/windows-distribution`, `platform/licence-compliance` |
| 24 | `m7-hardening` | M7 | all v1 | `platform/capacity-quotas`, `platform/performance-baseline`, `platform/privacy-documentation` |

Changes 7 (AD), 11–13 (sources) and 16–17 (review) can be worked on in parallel with their siblings once their dependencies are archived.

### Post-v1 (SHOULD, v1.3 §0.2)

| Change | Artifacts | Capabilities |
|---|---|---|
| `post-v1-scheduled-backups` | proposal, specs, design, tasks | `data/backup-scheduling`, `data/backup-retention`, `data/backup-administration` |
| `post-v1-linux-macos-packages` | proposal, specs | `platform/linux-distribution`, `platform/macos-distribution` |
| `post-v1-scopus-api-source` | proposal, specs | `search/scopus-api-source` |
| `post-v1-wos-expanded-source` | proposal, specs | `search/wos-expanded-source` |
| `post-v1-asreview-interop` | proposal, specs | `review/asreview-interop` |
| `post-v1-citation-networks` | proposal, specs | `analysis/citation-networks` (analyses 6–7) |
| `post-v1-research-maturity` | proposal, specs | `analysis/research-maturity` (analysis 10) |

### MAY items: non-goals, no change created

- Analysis 8 (topic clusters and thematic evolution). It needs its own specification first.
- TOTP for `admin`.
- Personal-data export and pseudonymisation tooling.
- Multiple AD domains, and Windows SSO/Kerberos.
- PyBibX and BibFusion connectors.
- Email notifications.

## 2. v1.3 sections → changes

| v1.3 section | Changes |
|---|---|
| §0 Instructions, §0.1 Naming | `openspec/config.yaml`, `m1-platform-foundation`, export and backup naming in `m7-project-export-import` and `m7-full-backup-and-restore` |
| §0.2 Release scope | all `m*` changes (MUST), all `post-v1-*` changes (SHOULD), the MAY list above |
| §1 Scope, decisions, roles, rights | `m1-local-identity`, `m2-project-access-control`, `m2-project-workspaces`, `m1-platform-foundation` (About screen) |
| §2 Technology and licensing | `openspec/config.yaml`; the stack choices sit in each change's design.md; `m7-windows-distribution` (licence compliance) |
| §3 Deployment topology | `m1-platform-foundation` |
| §4, §4.1, §4.2 Data layout and schemas | the change that owns each table (named in its design.md "Migration Plan") |
| §4.3 Project creation, routing and migration | `m2-project-workspaces` |
| §5.1–5.2 Sign-in and bootstrap | `m1-local-identity`, `m2-active-directory` |
| §5.3 Active Directory | `m2-active-directory` |
| §5.4–5.5 Sessions and admin UX | `m1-local-identity`, `m2-active-directory` |
| §5.6 Credential precedence | `m3-source-credentials` |
| §6 Sharing | `m2-project-access-control` |
| §7.1 Strategy editor, §7.2 Compilers | `m3-search-strategy` |
| §8 Source adapters and imports | `m3-search-runs`, `m3-openalex-source`, `m3-wos-starter-source`, `m3-source-file-imports`, `m3-source-credentials`; post-v1 Scopus and WoS Expanded |
| §9 Background jobs | `m2-background-jobs` |
| §10 Normalisation and deduplication | `m4-canonical-records`, `m4-deduplication` |
| §11 PRISMA screening | `m5-screening`, `m5-full-text-eligibility`, `m5-corpus-and-prisma`, `post-v1-asreview-interop` |
| §12 Bibliometrics and reports | `m6-bibliometric-analyses`, `m6-reports-and-visualisations`; post-v1 analyses 6, 7 and 10 |
| §13 Frontend information architecture | the screens are in the owning change of each feature; the shell is in `m1-web-foundation` |
| §14 REST API contract | conventions in `m1-web-foundation`; each route is in its feature's change |
| §15 Export, import and archival | `m7-project-export-import` |
| §16 Full backups (v1 scope: CLI) | `m7-full-backup-and-restore` (§16.3, §16.5, CLI tests from §16.6) |
| §16.1, §16.2, §16.4, admin parts of §16.5 and §16.6 | `post-v1-scheduled-backups` |
| §17 Operational and security controls | `m1-platform-foundation`, `m1-web-foundation`, `m1-local-identity`, `m7-hardening` |
| §18, §18.1 Packaging and CLI | `m7-windows-distribution`; each CLI command is in its owning change |
| §19 Testing and acceptance | each task cites its §19 group; release acceptance and the definition of done are in `m7-hardening` |
| §20 Delivery plan | the change order above |
| §21 Reference links | used in the design.md files |

**Coverage check** (20 October 2026). Every item below appears in at least one change:
- all 70 endpoint paths in the §14 table (including the SHOULD `/admin/backups/*` and `/screening/asreview` routes);
- all 25 standard and adapter error codes;
- every §18.1 CLI command;
- §19 test groups 1–14, each referenced from tasks.

`openspec validate --all --strict` passes.

## 3. Decisions made while converting (review these)

These refine or depart from v1.3. Each is also recorded in the owning change's design.md, for `docs/decisions.md` when implemented.

**Departures from v1.3:**
1. **Disabling AD revokes only AD sessions.** v1.3 §5.3 rule 8 uses `auth_settings.revision`, which would also sign out every local user, including `admin`. Instead, AD tokens carry a directory-revision claim (`m2-active-directory`).
2. **Corpus versioning moved from M4 to M5.** Corpus membership depends on screening resolutions (`m5-corpus-and-prisma`).

**Ambiguity resolved:**

3. **The admin restore GUI is post-v1.** v1.3 §16.5 mentions it, but §0.2 makes v1 backups CLI-only, so §0.2 decides (`m7-full-backup-and-restore`, `post-v1-scheduled-backups`).

**Additions to the v1.3 API:**

4. **New error codes:** `NOT_FOUND`, `PAYLOAD_TOO_LARGE`, `QUOTA_EXCEEDED`, `INTERNAL_ERROR`, `SETUP_REQUIRED`, `AUTH_THROTTLED`, `PROJECT_UNAVAILABLE` and `SOURCE_UNAVAILABLE`, plus the details `PASSWORD_CHANGE_REQUIRED` and `PROJECT_ARCHIVED`. The v1.3 §14 list says "include", so it is not exhaustive.
5. **New endpoints:** `GET /admin/logs` (`m1-platform-foundation`), and `POST /admin/projects/{project_id}/quarantine` and `/release` (`m2-project-workspaces`). v1.3 §0 requires every admin feature to be reachable through REST.

**New behaviour, beyond the v1.3 text:**

6. **Refused data roots.** `init` and `serve` refuse a data root on UNC paths or detected network filesystems (`m1-platform-foundation`).
7. **API budgets** (`m3-source-credentials`):
   - per-user caps on shared keys, on top of the per-key budgets;
   - a search whose estimate exceeds the remaining budget needs explicit confirmation;
   - `api_usage` is added to the tables exempt from the write barrier.
8. **Automatic duplicate merges.** Exact-identifier duplicates are merged automatically by default, reversibly and as a project setting (`m4-deduplication`).
9. **Screening rules** (`m5-screening`):
   - blinded dual screening, enforced by the server;
   - exclusion reasons are always required at full text, and at title/abstract only when the protocol says so (off by default).
10. **Hidden private projects.** Requests for projects the caller cannot discover return 404 rather than 403 (`m2-project-access-control`).
11. **Admin access audit granularity.** Every opening of a project the admin doesn't own (a request for the project itself) and every admin change is audited. Requests inside an open project are not logged one by one (`m2-project-access-control`).
12. **Restricted keyword rules.** Rule types are limited to `exact`, `wildcard` (trailing `*`) and `stopword`, with no regular expressions (`m4-canonical-records`).
13. **Editing and ownership rules.**
    - Editors can edit project details.
    - After an ownership transfer, the previous owner's access follows the sharing rules (`m2-project-workspaces`).
14. **Quota defaults** in `m7-hardening`. Concurrency limits queue jobs; only the other quotas refuse with `QUOTA_EXCEEDED`. The admin is exempt from the projects-per-user quota.

    | Quota | Default |
    |---|---|
    | Projects per user | 50 |
    | Storage per project | 20 GB |
    | Upload size | 200 MB |
    | Archive size | 5 GB |
    | Queued jobs per user (refuses) | 20 |
    | Concurrent jobs per user (queues) | 3 |
    | Workers (queues) | 2 |

15. **Restore safety** (`m7-full-backup-and-restore`):
    - restore refuses to run while the service is up;
    - it always takes a safety backup and stops if it can't;
    - a dry run changes no live data and only appends to `logs/restore-tests.jsonl`.
16. **Frozen corpus snapshot.** Freezing a corpus also snapshots every member's metadata and every PRISMA count input, with a snapshot hash. PRISMA counts and analyses read only the snapshot, and an analysis input hash covers the snapshot hash. Keyword dictionary revisions are kept (`m5-corpus-and-prisma`, `m6-bibliometric-analyses`, `m4-canonical-records`).
17. **Licensed exports.** Exporting licensed raw records needs an explicit rights acknowledgement, otherwise `EXPORT_RESTRICTED` (`m7-project-export-import`).
18. **Export coordination.** An export holds an `export:<project_uuid>` lease, with no write scope, which pauses housekeeping deletions for that project. Its file inventory comes from the database snapshot's references, and files are always placed before the rows that reference them (`m7-project-export-import`, `m2-project-workspaces`).
19. **Backup series per destination.** v1 CLI backups get a series ID per destination, written to the run record and manifest. Scheduled backups always start a new series, so retention never prunes CLI archives. `--stage-locally` restores the v1.3 local-staging fallback (`m7-full-backup-and-restore`, `post-v1-scheduled-backups`).
20. **Missed-backup grace.** `missed_run_grace_minutes` is an admin setting (default 360). One catch-up runs only if the latest missed occurrence is within the grace; older ones are logged as skipped (`post-v1-scheduled-backups`).
21. **Explicit account conversion.** Account-type conversion and SID rebinding use explicit `conversion` and `rebind` objects in `PATCH /admin/users/{user_id}`. A direct account-type change is rejected (`m1-local-identity`, `m2-active-directory`).
22. **Path containment exception.** Full-backup destinations and restore staging are the only file paths allowed outside the data root (`m1-platform-foundation`).
23. **Cross-origin allowlist.** The unsafe-method origin check also accepts the explicit cross-origin allowlist (`m1-web-foundation`).

**Codex review (21 October 2026).** Items 11 and 14–23 resolve the 12 conflicts and gaps the review found. Its other findings were already recorded here.

## 4. Working with these changes

- **List:** `openspec list`.
- **Inspect:** `openspec show <change>`.
- **Check:** `openspec validate --all --strict`.
- **Implement:** `/opsx:apply <change>`, working through the order above.
- **Archive:** `/opsx:archive <change>` once tasks are complete, which creates the main specs under `openspec/specs/`.

**Archive at milestone granularity.** Archiving a change writes its requirements into the main specs as implemented behaviour. A few requirements are finished by a later change's tasks within the same milestone, so archive all changes of a milestone together once that milestone's tasks are done. The cross-change completions are:
- `m1-platform-foundation`: its GUI screens (branding, About, Admin → System, log view) and admin-only checks are completed in `m1-local-identity` groups 5–6.
- `m2-project-workspaces`:
  - listing shared and public projects is completed in `m2-project-access-control` task 1.4;
  - job cancellation on delete is completed in `m2-background-jobs` task 2.3.
- `m3-search-strategy`: preview test counts are completed by `m3-openalex-source` task 1.7 and `m3-wos-starter-source` task 1.6.
- `m3-source-credentials`: recording the credential scope on source runs is completed with `m3-search-runs`.
