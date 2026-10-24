# Proposal: M7 Windows distribution and licence compliance

## Why

End users should not need Python. v1 ships one packaged platform, Windows x86_64, with a Windows Service that runs LitFoundry as a LAN server or workstation (v1.3 decisions 7–8 and §18). Linux and macOS run from a virtual environment until their packages ship (SHOULD). LitFoundry is GPL-3.0, so every bundled component must be GPLv3-compatible, and binaries must ship notices and offer the corresponding source (v1.3 §2).

## What Changes

- **Package:** a PyInstaller onedir build for Windows x86_64, branded LitFoundry, with launcher `litfoundry`. It contains the server, worker, static UI assets, migration scripts and licence inventory. No SQLite database is kept in the install or extraction folders.
- **Installer:**
  - asks for server or workstation mode;
  - creates and protects the data root (`%PROGRAMDATA%\LitFoundry`);
  - runs `litfoundry init` and shows the bootstrap token;
  - optionally installs the service;
  - on upgrade, keeps the data root and requires a migration.
- **Windows Service:** `litfoundry`, running `litfoundry supervise`, managed with `litfoundry service install|uninstall`.
- **Signing:** executables and the installer are signed when a certificate is configured.
- **Clean-machine smoke test:** fonts, plotting, migrations, SQLite and browser assets, offline. Linux and macOS venv smoke tests.
- **Deployment documentation:**
  - HTTPS proxy, with Caddy as a separately installed prerequisite;
  - firewall;
  - AD controller and CA trust prerequisites;
  - the service account's filesystem and UNC backup access;
  - backup destination permissions.
- **Licence compliance:**
  - a lockfile;
  - a licence inventory and an SBOM per build;
  - an automated licence gate that rejects incompatible licences;
  - licence texts and notices bundled, and a corresponding-source offer;
  - optional heavy ML stacks excluded.

## Capabilities

### New Capabilities

- `platform/windows-distribution`: the Windows package, installer, service, signing, upgrade behaviour, smoke tests and deployment documentation, plus venv operation on Linux and macOS.
- `platform/licence-compliance`: the lockfile, licence inventory, SBOM, licence gate, bundled notices and source offer.

### Modified Capabilities

None.

## Impact

- **v1.3 sections implemented:**
  - §0.1: the service ID;
  - §1: decisions 7–8;
  - §2: licensing and the Packaging row;
  - §18;
  - §18.1: `service install|uninstall` and `supervise` as the service entry point;
  - §19: group 13;
  - §20: M7 (Windows packaging and service).
- **Depends on:** `m2-background-jobs` (`supervise`), `m1-platform-foundation` (`init`, data root ACL) and `m7-full-backup-and-restore` (documentation cross-references).
- **Code:** `packaging/pyinstaller/`, `packaging/windows/` (installer script, service wrapper), `LICENSES/`, `scripts/licence_check.py`, `scripts/sbom.py` and a CI release workflow.
- **Out of scope:** Linux and macOS packages with systemd and launchd services (`post-v1-linux-macos-packages`).
