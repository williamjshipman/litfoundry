# Spec Delta: data/project-export

## Purpose

Lets a project's owner or the administrator export a complete, portable project archive. The archive contains everything needed to continue the project elsewhere and nothing that belongs to the installation or other users.

## ADDED Requirements

### Requirement: Request an export
`POST /api/v1/projects/{project_id}/exports` SHALL let only the owner or the administrator start a project export, responding 202 with a job. `GET` SHALL list export history: timestamp, requester, format version, schema version, size, status and expiry.

#### Scenario: Editor refused
- **WHEN** an editor requests an export
- **THEN** the response is 403

### Requirement: Consistent snapshot
The export SHALL copy the project database through the SQLite online backup API after coordinating with writers, and SHALL freeze the artifact inventory at that moment. It SHALL never copy a live database file directly, and it SHALL not change the live project.

#### Scenario: Export during edits
- **WHEN** an export runs while an editor saves screening decisions
- **THEN** the exported database passes an integrity check and the live project is unchanged by the export

### Requirement: Inventoried files protected during export
The export's file inventory SHALL include every project file referenced by the database snapshot. Interactive edits SHALL continue during an export. While a project's export runs, housekeeping SHALL NOT delete any of that project's files, so every inventoried file can still be copied.

#### Scenario: Attachment deleted during export
- **WHEN** an editor deletes an attachment after the export's snapshot was taken but before its files are copied
- **THEN** the attachment file is still exported, and housekeeping removes it only after the export finishes

### Requirement: Archive contents
The archive SHALL contain:
- `manifest.json` and `project.sqlite`;
- `sources/`, `imports/`, `attachments/`, `reports/` and `figures/`;
- `metadata/provenance.json` and `metadata/checksums.json`, with a SHA-256 for every file;
- a licence/reuse notice.

#### Scenario: Checksums complete
- **WHEN** an export completes
- **THEN** every file in the archive has a matching entry in `metadata/checksums.json`

### Requirement: Archive exclusions
The archive SHALL NOT contain:
- source credentials, catalogue account data, tokens or secrets;
- runtime logs, caches or temp files;
- any other project's data;
- absolute host paths.

#### Scenario: No secrets
- **WHEN** an export of a project whose users have personal API keys is scanned
- **THEN** no key, token, password hash or absolute path is found

### Requirement: Archive naming and manifest
The archive SHALL be named `litfoundry_project_<project_uuid>_<YYYYMMDD_HHMMSSZ>.zip`, using UTC. Its manifest SHALL include:
- `"product": "litfoundry"` and `"product_name": "LitFoundry"`;
- the export format version;
- the project schema version;
- the export timestamp;
- the project UUID.

#### Scenario: Branded name
- **WHEN** an export is downloaded
- **THEN** its filename follows the pattern, and the manifest carries the product fields

### Requirement: Licensed content
When the project contains raw records from licensed sources (Scopus or WoS files or APIs), exporting them SHALL require an explicit rights acknowledgement. Without the acknowledgement, the export SHALL fail with `EXPORT_RESTRICTED`. A metadata-only export option SHALL exclude licensed raw payloads.

#### Scenario: Metadata-only export
- **WHEN** the owner chooses a metadata-only export
- **THEN** licensed raw payloads are excluded and the manifest records the export as metadata-only

### Requirement: Authorised download
`GET /api/v1/projects/{project_id}/exports/{export_id}/download` SHALL recheck owner or administrator permission on every request. There SHALL be no permanent unauthenticated download URL.

#### Scenario: Ownership transferred
- **WHEN** a former owner uses an old download link after the project was transferred
- **THEN** the download is refused

### Requirement: Export expiry
Export files SHALL expire after a configurable period, 7 days by default. Housekeeping SHALL then delete them. Export files SHALL be excluded from full-system backups.

#### Scenario: Expired export
- **WHEN** an export is older than the expiry period
- **THEN** it is deleted and its history entry shows it as expired

### Requirement: Export screen
The GUI SHALL provide export with job progress, the rights acknowledgement, the metadata-only option, export history and authenticated download.

#### Scenario: Export from GUI
- **WHEN** the owner starts an export and waits
- **THEN** progress is shown and the download becomes available on completion
