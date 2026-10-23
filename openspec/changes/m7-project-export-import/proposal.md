# Proposal: M7 project export and import

## Why

Owners need to move a complete project between installations, or archive it. The export must carry the raw data, decisions, artifacts and provenance, and must never carry credentials or other users' data. An imported ZIP is untrusted input and must be validated thoroughly before it touches the installation (v1.3 §15).

## What Changes

- **Export (`/exports`):** the owner or admin exports a project ZIP as a background job.
  - **Snapshot:** a consistent SQLite snapshot through the backup API, with a frozen artifact inventory, SHA-256 checksums, provenance and checksum metadata, and a licence/reuse notice.
  - **Name and manifest:** the file is named `litfoundry_project_<project_uuid>_<YYYYMMDD_HHMMSSZ>.zip`, and the manifest carries product branding and the format and schema versions.
  - **Exclusions:** credentials, catalogue data, tokens, secrets, logs, caches, temp files, other projects and absolute paths.
- **Licensed content:** exports containing licensed Scopus or WoS raw records need a rights acknowledgement (`EXPORT_RESTRICTED` otherwise), and a metadata-only export option is offered.
- **Download:** authenticated download, with the owner or admin permission rechecked. Exports expire after 7 days by default, and housekeeping removes them.
- **Import (`/project-imports`):** validated as untrusted input:
  - size, entry count, entry types, path traversal, symlinks, compression bombs, manifest identifier and version, and checksums;
  - quota-limited staging;
  - older schemas are migrated and newer schemas rejected.
- **Imported project:** gets a new project UUID, is owned by the importer and is private.
  - ACLs and job leases are cleared, and no credentials are imported.
  - Reviewer IDs are kept, and unknown people are marked `imported`.
  - The original IDs are kept in imported-from fields.
  - Registration is atomic.
- **GUI:** the export screen with progress, history and download, and an import action on Home.

## Capabilities

### New Capabilities

- `data/project-export`: project ZIP export, its contents and exclusions, naming and manifest, licensed-content rules, download and expiry.
- `data/project-import`: safe validation and import of project ZIPs as new private projects, with preserved provenance.

### Modified Capabilities

None.

## Impact

- **v1.3 sections implemented:**
  - §0.1: archive names and manifests;
  - §4: `exports/` expiry;
  - §13: Export;
  - §14: `/exports`, `/exports/{export_id}/download`, `/project-imports` and `EXPORT_RESTRICTED`;
  - §15;
  - §19: group 11 (project round trip);
  - §20: M7, including the branded export filenames.
- **Depends on:** `m6-reports-and-visualisations` (all project content exists), `m2-background-jobs` and `platform/schema-migrations` (`m2-project-workspaces`).
- **Code:** `src/litfoundry/export/`, the API routes and the frontend export and import screens.
