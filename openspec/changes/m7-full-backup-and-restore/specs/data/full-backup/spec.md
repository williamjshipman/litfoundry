# Spec Delta: data/full-backup

## Purpose

Creates consistent, verified, full-installation backup archives for disaster recovery. Each archive covers the catalogue, every project and the stored secrets, and can be restored on another machine.

## ADDED Requirements

### Requirement: Create a backup from the host
`litfoundry backups create --destination PATH` SHALL create a full backup in the given directory. The destination SHALL be required, and SHALL be an absolute path outside the data root that is not equal to or beneath any staging, temp or export path. UNC paths and mounted network directories SHALL be accepted.

#### Scenario: Destination inside data root
- **WHEN** an operator passes a destination inside the data root
- **THEN** the command fails before any work and no archive is written

#### Scenario: Missing destination
- **WHEN** an operator runs `litfoundry backups create` without `--destination`
- **THEN** the command fails and names the required option

### Requirement: Destination check
Before snapshotting, the command SHALL check that the destination exists, is writable (by writing and deleting a uniquely named probe file) and has enough free space for the estimated archive. It SHALL never read or list unrelated files there.

#### Scenario: Unwritable destination
- **WHEN** the destination is not writable by the service identity
- **THEN** the run fails with `BACKUP_DESTINATION_UNAVAILABLE` and no snapshot is taken

### Requirement: Exclusive backup
Only one full backup SHALL run at a time, under an exclusive `full-backup` lease. A backup SHALL NOT start during a schema migration or a restore. Housekeeping deletions (trash purge and export expiry) SHALL NOT run while the lease is held.

#### Scenario: Concurrent backups
- **WHEN** a second backup starts while one is running
- **THEN** the second exits with an error naming the running backup

### Requirement: Contents
A full backup SHALL include:
- the catalogue;
- every included project's database and persistent files, regardless of sharing;
- `secret_material/`;
- non-secret administrative configuration;
- logs, unless excluded with an option.

It SHALL exclude previous backups, staging, temp files, project export ZIPs and TLS or reverse-proxy CA private keys.

#### Scenario: Private and archived projects included
- **WHEN** a backup runs on an installation with private, archived and disabled-user projects
- **THEN** all of them are in the archive

### Requirement: Project states
`ready` and `archived` projects SHALL be included. `quarantined` projects SHALL be included as raw file copies, flagged in the manifest. `provisioning` and trashed projects SHALL be excluded. A project in `error` SHALL fail the backup with an administrator-visible error naming the project.

#### Scenario: Quarantined project
- **WHEN** one project is quarantined
- **THEN** the backup completes and the manifest flags that project as quarantined

#### Scenario: Damaged project not quarantined
- **WHEN** a project is in state `error`
- **THEN** the backup fails and names the project

### Requirement: Consistent snapshot under the write barrier
The backup SHALL raise the global write barrier and wait for it to freeze. It SHALL then copy the catalogue and every included project database with the SQLite online backup API, record each project's file inventory, and release the barrier. No hashing or file copying SHALL happen while the barrier is held, and live database files SHALL never be copied directly.

#### Scenario: Backup during activity
- **WHEN** a backup runs while a user edits a project, an attachment is uploaded and a search job adds records
- **THEN** the snapshots pass integrity checks, the search job pauses and resumes, and token refresh and job heartbeats continue

### Requirement: Snapshot verification and file copy
After releasing the barrier, the backup SHALL run integrity and foreign-key checks on every snapshot, then copy and hash every inventoried project file. A missing or unreadable inventoried file SHALL fail the run.

#### Scenario: Missing file
- **WHEN** an inventoried attachment cannot be read
- **THEN** the backup fails and records a redacted error

### Requirement: Manifest
The archive's `manifest.json` SHALL contain:
- `product="litfoundry"` and `product_name="LitFoundry"`;
- format version, run ID, series ID, source hostname and app version;
- snapshot start and finish times (UTC);
- catalogue and project schema versions;
- every project's UUID, relative path and state;
- inventory sizes and a SHA-256 for every file;
- a statement that the archive contains secrets.

#### Scenario: Secrets statement
- **WHEN** an operator reads a backup's manifest
- **THEN** it states that the archive contains secrets and lists every file's checksum

### Requirement: Backup metadata files
The archive SHALL contain `backup_metadata/checksums.json`, `backup_metadata/configuration.json` holding only non-secret configuration, and a restore README. Archive entries SHALL use relative, safe paths only.

#### Scenario: Metadata present
- **WHEN** an archive is listed
- **THEN** the checksums file, the configuration file and the restore README are present, and no entry path is absolute

### Requirement: Unencrypted archives with secrets
Backups SHALL be unencrypted and SHALL include the master key, the encrypted stored secrets and the session signing key, so restore needs no extra steps. The CLI and documentation SHALL warn that the destination must be readable only by the service identity and administrators. Secrets SHALL appear only in the secret-store files, never in logs, configuration metadata or the manifest.

#### Scenario: Secret scan of archive metadata
- **WHEN** test secrets are configured and a backup is created
- **THEN** the secrets appear in no log, manifest or configuration file in the archive

### Requirement: Archive naming
Archives SHALL be named `litfoundry_full_<YYYYMMDD_HHMMSSZ>_<run_uuid_short>.zip`, using the UTC snapshot time, which SHALL match the manifest. Filenames SHALL never contain `:`.

#### Scenario: Name matches manifest
- **WHEN** a backup completes
- **THEN** the timestamp in its filename equals the manifest's UTC snapshot time

### Requirement: Destination series
Each distinct normalised destination path SHALL have a backup series ID. It is created on first use and reused for later backups to the same destination. The series ID SHALL be recorded in the run record and the manifest.

#### Scenario: Same destination twice
- **WHEN** two CLI backups are written to the same destination
- **THEN** both runs and both manifests carry the same series ID

#### Scenario: New destination
- **WHEN** a backup is written to a destination not used before
- **THEN** it gets a new series ID

### Requirement: Local staging fallback
When the destination cannot reliably hold a `.partial` file (for example, on some network shares), the operator SHALL be able to request local staging with `--stage-locally`. The archive is then built and verified under `backup_staging/`, copied to the destination as `.partial`, checked again against its SHA-256, and only then renamed.

#### Scenario: Staged locally
- **WHEN** an operator runs `litfoundry backups create --destination PATH --stage-locally`
- **THEN** the archive is verified locally, copied, re-verified at the destination and renamed to `.zip`

### Requirement: Package and verify before completion
Unless local staging is requested, the archive SHALL be written as a `.partial` file in the destination. It SHALL then be closed, reopened, CRC-checked for every entry and compared against the manifest checksums before it is renamed to `.zip`. The run SHALL be marked `completed` only after the final file is verified to exist and be readable, with its SHA-256 and size recorded.

#### Scenario: Corruption detected
- **WHEN** an entry fails its CRC check after writing
- **THEN** the run is `failed`, no `.zip` is produced and earlier backups are untouched

### Requirement: Failure handling
On any failure, the run SHALL be marked `failed` with a redacted error code, staging SHALL be cleaned up and the administrator SHALL see an alert in the application. No earlier backup SHALL be deleted or modified. Failures include an unavailable destination, a full disk, a barrier drain timeout, a check failure and a corrupt archive.

#### Scenario: Disk full
- **WHEN** the destination fills during packaging
- **THEN** the run is `failed` with `BACKUP_DESTINATION_UNAVAILABLE`, the `.partial` file is removed and earlier archives remain

### Requirement: Backup run records
Each run SHALL be recorded in the catalogue's backup run history with:
- status, initiator (`cli`) and series ID;
- start and completion times;
- destination file;
- SHA-256 and size;
- error code and validation results.

A copy of the record SHALL be included in the manifest.

#### Scenario: Run recorded
- **WHEN** a CLI backup completes
- **THEN** a run record with initiator `cli`, checksum and size exists

### Requirement: Verify and list commands
- `litfoundry backups verify ARCHIVE` SHALL check archive integrity, manifest checksums and SQLite integrity in temporary staging, without changing live data.
- `litfoundry backups list` SHALL show recorded runs with status, file, size and checksum.

#### Scenario: Verify corrupted archive
- **WHEN** an operator verifies an archive whose manifest was altered
- **THEN** verification fails and live data is unchanged

### Requirement: Licensed content warning
When an archive includes records from licensed sources, the command SHALL warn that a disaster-recovery backup is not permission to redistribute them.

#### Scenario: Warning shown
- **WHEN** a backup includes Scopus imports
- **THEN** the command output includes the redistribution warning

### Requirement: Backup status
`litfoundry status`, the readiness endpoint and the admin system screen SHALL show the last backup's result, time, file and size, and any active backup alert.

#### Scenario: Failed last backup
- **WHEN** the last backup failed
- **THEN** the admin system screen shows the failure and its error code

### Requirement: Stale partial file cleanup
A separate housekeeping step SHALL remove orphaned `.partial` files older than a threshold, once it has confirmed that no running backup owns them.

#### Scenario: Orphan partial file
- **WHEN** a crashed run left a `.partial` file and no backup is running
- **THEN** housekeeping removes it after the threshold
