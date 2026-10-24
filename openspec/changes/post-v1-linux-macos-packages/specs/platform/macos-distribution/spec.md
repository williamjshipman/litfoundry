# Spec Delta: platform/macos-distribution

## Purpose

Delivers LitFoundry on macOS (arm64 and x86_64) as signed packages with a launchd service, so macOS hosts do not need a Python environment.

## ADDED Requirements

### Requirement: macOS packages
The release build SHALL produce one-folder packages for macOS arm64 and x86_64, built on macOS. Each SHALL be branded LitFoundry, with the executable `litfoundry`.

#### Scenario: Both architectures
- **WHEN** the macOS release build completes
- **THEN** packages exist for arm64 and x86_64

### Requirement: launchd service
`litfoundry service install` on macOS SHALL install a launchd daemon `litfoundry` that runs the supervisor. `uninstall` SHALL remove it without touching the data root.

#### Scenario: Daemon lifecycle
- **WHEN** the daemon is installed, loaded and unloaded
- **THEN** LitFoundry starts and stops with it

### Requirement: macOS data root
The package SHALL default to the data root `/Library/Application Support/LitFoundry` in system-wide mode, or the user's Application Support folder otherwise, with restrictive permissions.

#### Scenario: System-wide default
- **WHEN** initialisation runs in system-wide mode
- **THEN** the data root is `/Library/Application Support/LitFoundry` with mode `0700`

### Requirement: Signing and notarisation
When signing credentials are configured, the release build SHALL sign and notarise the macOS packages. Unsigned builds SHALL be labelled as unsigned.

#### Scenario: Notarised release
- **WHEN** the release pipeline runs with credentials configured
- **THEN** the packages pass Gatekeeper assessment

### Requirement: macOS clean-host smoke test
Each macOS release SHALL pass the clean-host smoke test, covering install, init, bootstrap, sign-in, a project, the PRISMA SVG, one analysis, and the UI with no internet.

#### Scenario: Offline macOS host
- **WHEN** the package is installed on a clean macOS host without internet
- **THEN** the smoke test passes
