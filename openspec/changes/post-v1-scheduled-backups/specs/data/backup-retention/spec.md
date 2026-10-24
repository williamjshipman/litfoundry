# Spec Delta: data/backup-retention

## Purpose

Keeps a bounded number of verified full backups per destination series. Pruning never removes a good restore point prematurely, and never touches files LitFoundry does not manage.

## ADDED Requirements

### Requirement: Rotation only after success
Older backups SHALL be pruned only after a new backup has been created, verified and committed as `completed`. A failed backup SHALL trigger no pruning.

#### Scenario: Failed run
- **WHEN** a scheduled backup fails
- **THEN** every existing archive is kept

### Requirement: Keep the newest verified archives
Retention SHALL keep the most recent `retain_count` verified successful archives of the current series, ordered by UTC run timestamp, not by filename.

#### Scenario: Retain three
- **WHEN** `retain_count` is 3 and a fourth backup succeeds
- **THEN** the oldest of the four archives is deleted and three remain

### Requirement: Only managed archives are deleted
An archive SHALL be deleted only if all of these hold:
- it matches a recorded run;
- its manifest run ID matches that run;
- its manifest series ID is the current series.

Unrelated `.zip` files, files in subdirectories, and archives from earlier destinations SHALL never be deleted automatically.

#### Scenario: Unrelated zip
- **WHEN** the destination contains a ZIP file LitFoundry did not create
- **THEN** pruning leaves it untouched

#### Scenario: Old destination
- **WHEN** the destination changed last month
- **THEN** archives in the old destination are never pruned automatically

### Requirement: Failed runs do not count
Failed or partial archives SHALL NOT count towards retention. Orphaned `.partial` files SHALL be cleaned up separately, under their own age threshold, once no run owns them.

#### Scenario: Partial file
- **WHEN** a crashed run left a `.partial` file
- **THEN** it does not count towards retention and is removed after its age threshold

### Requirement: Lowered retention preview
When the administrator lowers `retain_count`, the system SHALL preview the archives that would be deleted. It SHALL defer deletion until the next successful run, or until a confirmed Prune now.

#### Scenario: Lower from 7 to 3
- **WHEN** the administrator lowers retention from 7 to 3
- **THEN** the four affected archives are listed and none is deleted yet

### Requirement: Guarded prune
`POST /api/v1/admin/backups/prune` SHALL preview deletions when `dry_run=true`, and apply them otherwise. Before deleting, it SHALL verify that good archives remain. It SHALL refuse to delete the only valid restore point unless the administrator explicitly confirms a recovery-impact warning.

#### Scenario: Only restore point
- **WHEN** pruning would delete the only valid archive
- **THEN** it is refused unless the recovery-impact confirmation is given

### Requirement: Retention changes audited
Every change to retention settings and every applied prune SHALL record an audit event.

#### Scenario: Audit prune
- **WHEN** the administrator applies Prune now
- **THEN** an audit event lists the deleted archives

### Requirement: Re-registration after restore
After a restore, the next backup run SHALL rescan the destination and re-register managed archives by their manifest run ID and series ID. Archives created after the restored point in time SHALL therefore stay under retention.

#### Scenario: Archives newer than restore point
- **WHEN** an installation is restored from an older backup and the next backup runs
- **THEN** archives created after the restored snapshot are re-registered and pruned correctly
