# Spec Delta: data/full-restore

## Purpose

Restores a whole LitFoundry installation from a full backup, offline and verified first. The existing installation is preserved if anything goes wrong, and the restore works on the same machine or a new one.

## ADDED Requirements

### Requirement: Offline restore only
A full restore SHALL run only through `litfoundry restore` on the host. No web endpoint SHALL replace live databases or files. The command SHALL refuse to proceed while server or worker processes are running against the data root.

#### Scenario: Service still running
- **WHEN** an operator runs a restore while the service is running
- **THEN** the command refuses and tells the operator to stop the service

### Requirement: Dry run
`litfoundry restore --archive PATH --dry-run` SHALL perform every verification and staging step and report the result, without changing any live database, project file, secret or configuration. Its only write SHALL be to append a restore-test record (date, archive, result) to the restore-test log at `<data_root>/logs/restore-tests.jsonl`.

#### Scenario: Dry run leaves data untouched
- **WHEN** a dry run completes
- **THEN** every live database, project file, secret and configuration file is unchanged, the restore-test log has one new record and the report lists every check

### Requirement: Confirmed restore
`litfoundry restore --archive PATH --confirm` SHALL show an application-outage warning and require interactive confirmation before replacing data.

#### Scenario: Confirmation declined
- **WHEN** the operator declines the confirmation prompt
- **THEN** nothing is changed

### Requirement: Verification before replacement
Before any replacement, the restore SHALL verify:
- archive integrity and every manifest checksum;
- expected schema versions;
- path safety and decompression quotas;
- SQLite integrity and foreign keys;
- catalogue-to-project consistency.

These checks SHALL run on data staged outside the live data root.

#### Scenario: Catalogue references missing project
- **WHEN** the catalogue in an archive references a project folder the archive lacks
- **THEN** the restore stops and the live installation is unchanged

### Requirement: Schema handling
Archives with older schemas SHALL be migrated in staging with the migration coordinator. Archives newer than the installation SHALL be rejected.

#### Scenario: Older archive
- **WHEN** an archive from the previous release is restored
- **THEN** its databases are migrated in staging before replacement

### Requirement: Safety backup and rollback
Before replacing data, the restore SHALL always take a safety backup of the existing data root, and SHALL stop without changes if it cannot. It SHALL replace data atomically where the filesystem allows, or otherwise use a rollback-capable staged replacement. If any step fails, it SHALL return the original installation to its prior state.

#### Scenario: Interrupted restore
- **WHEN** the restore fails after starting the replacement
- **THEN** the original installation is restored and starts normally

### Requirement: Post-restore resets
After replacement, the restore SHALL:
- restore `secret_material/`;
- rotate the session signing key, so every user signs in again;
- clear job leases and hold restored queued jobs for administrator review;
- mark restored running backup runs as `failed`;
- reset operational state such as throttles and active writers.

#### Scenario: Users sign in again
- **WHEN** a restore completes
- **THEN** every session from before the restore is rejected, and stored API credentials still work

### Requirement: Smoke checks before writes
After a restore, the system SHALL run post-restore smoke checks (catalogue opens, projects open, secrets decrypt) before accepting new writes, and SHALL report the outcome.

#### Scenario: Smoke check failure
- **WHEN** a restored secret cannot be decrypted
- **THEN** the restore reports failure and rolls back

### Requirement: Cross-machine restore
A full backup SHALL restore on a different machine, including a different supported operating system, preserving:
- sign-in methods and users;
- ACLs;
- project databases, search data and reports;
- stored credentials.

Host-specific settings such as hostname, proxy and CA paths SHALL be reported for reconfiguration.

#### Scenario: Restore on new host
- **WHEN** a backup made on Windows is restored on a Linux test host
- **THEN** users, ACLs, projects and reports are present, and credentials decrypt

### Requirement: Restore documentation and test reminder
The documentation SHALL describe restoring to the same machine and to a new machine on Windows, Linux and macOS, including the dependency on API entitlements, CA trust and AD connectivity in the new environment. The admin system screen and `litfoundry status` SHALL show the date of the last restore test and a reminder once it is more than 90 days old.

#### Scenario: Restore test overdue
- **WHEN** the last recorded restore test is 100 days old
- **THEN** the admin system screen shows a restore-test reminder
