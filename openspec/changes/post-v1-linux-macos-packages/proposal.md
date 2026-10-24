# Proposal: Linux and macOS packages and services (post-v1)

**Priority:** SHOULD, planned for the release after v1 (v1.3 §0.2). Design and tasks will be written when this change is scheduled.

## Why

v1 ships a packaged installer only for Windows. Linux and macOS run from a Python virtual environment, with CI running the full test suite on all three (v1.3 decision 7, §18). Packaged distributions with native services remove the need for Python on those hosts.

## What Changes

- **Linux x86_64:** a PyInstaller onedir package with a systemd service `litfoundry` running the supervisor, a dedicated service user, and the data root `/var/lib/litfoundry` with mode `0700`.
- **macOS arm64 and x86_64:** packages with a launchd daemon `litfoundry` and the data root `/Library/Application Support/LitFoundry`, with signing and notarisation when credentials are configured.
- **Service commands:** `litfoundry service install|uninstall` support systemd and launchd.
- **Testing:** clean-host smoke tests for each platform.
- **Documentation:** availability of mounted backup volumes after a reboot, and their credentials.

## Capabilities

### New Capabilities

- `platform/linux-distribution`: the Linux package, systemd service, service user and data-root defaults.
- `platform/macos-distribution`: the macOS packages, launchd service, signing and notarisation, and data-root defaults.

### Modified Capabilities

None.

## Impact

- **v1.3 sections implemented:**
  - §0.2: Linux and macOS packages;
  - §2: the Packaging row;
  - §18: Linux and macOS;
  - §18.1: `service` for systemd and launchd;
  - §19: group 13 (installer smoke tests on Linux and macOS).
- **Depends on:** `m7-windows-distribution`, which provides the shared PyInstaller spec and licence gate.
- **Code:** `packaging/linux/`, `packaging/macos/` and release workflow jobs per OS.
