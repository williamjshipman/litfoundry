# Spec Delta: platform/windows-distribution

## Purpose

Delivers LitFoundry to Windows users as a signed, self-contained package and service that needs no Python installation. Linux and macOS remain runnable from a virtual environment.

## ADDED Requirements

### Requirement: Windows package
The release build SHALL produce a one-folder package for Windows x86_64. It SHALL be branded LitFoundry, with the executable `litfoundry`, and contain the server, worker, static UI assets, migration scripts and licence inventory. The build SHALL run on Windows; cross-compilation SHALL NOT be assumed.

#### Scenario: Package contents
- **WHEN** the Windows release build completes
- **THEN** the package contains `litfoundry.exe`, the UI assets, migrations and the licence inventory

### Requirement: Data outside the install folder
The packaged application SHALL keep all data in the configured data root, by default `%PROGRAMDATA%\LitFoundry` in service mode or the user's application data folder otherwise. It SHALL never store a SQLite database inside the install folder or the package extraction folder.

#### Scenario: Install folder read-only
- **WHEN** the install folder is read-only for the service identity
- **THEN** LitFoundry runs normally

### Requirement: Installer
The Windows installer SHALL:
- ask whether to set up server mode or workstation mode;
- create and protect the data root;
- run initialisation and display the bootstrap token;
- optionally install the Windows Service.

Client PCs SHALL need only a browser.

#### Scenario: Server-mode install
- **WHEN** an administrator installs in server mode with the service option
- **THEN** the data root exists with restrictive permissions, the service is installed, and the bootstrap token is shown once

### Requirement: Upgrade keeps data
Upgrading SHALL replace program files only and keep the data root. Before the service starts again, the operator SHALL be told to run the migration, and the server's schema version gate SHALL enforce it.

#### Scenario: Upgrade
- **WHEN** a newer version is installed over an older one
- **THEN** the data root is unchanged and the service does not start until `litfoundry migrate` has run

### Requirement: Windows Service
`litfoundry service install` SHALL register one Windows Service with ID `litfoundry`, which runs the supervisor for the server and worker processes, under a configurable service account. `litfoundry service uninstall` SHALL remove the service without touching the data root.

#### Scenario: Service lifecycle
- **WHEN** the service is installed, started, stopped and uninstalled
- **THEN** the server and workers start and stop with it, and the data root remains after uninstall

### Requirement: Signing
When a code-signing certificate is configured, the release build SHALL sign the executables and the installer. Unsigned builds SHALL be labelled as unsigned in the release notes.

#### Scenario: Signed release
- **WHEN** the release pipeline runs with a certificate configured
- **THEN** the executables and installer carry valid signatures

### Requirement: Clean-machine verification
Each Windows release SHALL pass a smoke test on a clean Windows host that checks:
- installation and first start;
- migrations;
- SQLite;
- plotting and fonts;
- the browser UI with no internet access;
- bootstrap and sign-in.

#### Scenario: Offline clean host
- **WHEN** the package is installed on a clean Windows host without internet
- **THEN** the smoke test passes, including loading the UI

### Requirement: Venv operation on Linux and macOS
LitFoundry SHALL run on Linux and macOS from a Python virtual environment, following documented steps. CI SHALL run the full test suite and a venv smoke test on both.

#### Scenario: Linux venv
- **WHEN** the documented venv steps are followed on Linux
- **THEN** `litfoundry init`, `litfoundry supervise` and the UI work

### Requirement: Deployment documentation
The release documentation SHALL cover:
- HTTPS proxy setup, with Caddy as a separately installed prerequisite;
- the firewall;
- AD controller and CA trust prerequisites;
- the service account's access to the data root and to UNC backup destinations;
- the requirement that backup destinations be readable only by the service identity and administrators.

#### Scenario: Backup permissions documented
- **WHEN** an administrator reads the Windows deployment guide
- **THEN** it explains how to grant the service account write access to a UNC backup share and restrict readers
