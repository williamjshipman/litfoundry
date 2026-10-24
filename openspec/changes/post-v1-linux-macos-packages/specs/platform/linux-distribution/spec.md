# Spec Delta: platform/linux-distribution

## Purpose

Delivers LitFoundry on Linux x86_64 as a self-contained package with a systemd service, so Linux hosts do not need a Python environment.

## ADDED Requirements

### Requirement: Linux package
The release build SHALL produce a one-folder package for Linux x86_64, built on Linux. It SHALL be branded LitFoundry, with the executable `litfoundry`, and contain the server, worker, UI assets, migrations and licence inventory.

#### Scenario: Linux package contents
- **WHEN** the Linux release build completes
- **THEN** the package runs `litfoundry --version` on a clean host

### Requirement: systemd service
`litfoundry service install` on Linux SHALL install a systemd unit `litfoundry` that runs the supervisor as a dedicated service user. `uninstall` SHALL remove the unit without touching the data root.

#### Scenario: Service starts at boot
- **WHEN** the unit is installed and the host reboots
- **THEN** LitFoundry starts automatically under the service user

### Requirement: Linux data root
The package SHALL default to the data root `/var/lib/litfoundry`, owned by the service user with mode `0700`, and SHALL keep no database inside the package folder.

#### Scenario: Permissions
- **WHEN** initialisation runs during installation
- **THEN** `/var/lib/litfoundry` is owned by the service user with mode `0700`

### Requirement: Linux clean-host smoke test
Each Linux release SHALL pass the clean-host smoke test, covering install, init, bootstrap, sign-in, a project, the PRISMA SVG, one analysis, and the UI with no internet.

#### Scenario: Offline Linux host
- **WHEN** the package is installed on a clean Linux host without internet
- **THEN** the smoke test passes
