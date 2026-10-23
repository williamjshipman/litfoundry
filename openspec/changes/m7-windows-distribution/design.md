# Design: M7 Windows distribution and licence compliance

## Context

All runtime features exist. `litfoundry supervise` (M2) is the single process entry point a service needs. Data root initialisation and ACLs are implemented (M1).

## Goals / Non-Goals

**Goals:**
- A reproducible Windows build from CI, with a gate that blocks licence violations.
- Service management that never touches user data.

**Non-Goals:**
- Linux and macOS packages and services (`post-v1-linux-macos-packages`).
- Bundling Caddy (an optional prerequisite, v1.3 §18).
- Auto-update.

## Decisions

### PyInstaller
- **Build:** onedir mode with a spec file in `packaging/pyinstaller/litfoundry.spec`.
- **Data files:** `frontend/` (built CSS and vendor files), `migrations/` and `LICENSES/`.
- **Runtime paths:** at runtime, assets are located through `sys._MEIPASS`-aware path helpers. Data paths always come from configuration and never from the bundle location.
- **Licence note:** PyInstaller's bootloader licence exception permits distributing the result (v1.3 §21).

### Installer
- **Tool:** Inno Setup (free, permissive licence), built in CI on `windows-latest`.
- **Install steps:**
  1. choose server or workstation mode;
  2. choose the service account;
  3. install files to `Program Files\LitFoundry`;
  4. run `litfoundry init` (data root ACL);
  5. show the bootstrap token from `init` output;
  6. run `litfoundry service install` if selected.
- **Upgrade:** program files are replaced. The installer runs `litfoundry status` and shows the "run `litfoundry migrate`" instruction when the schema gate reports pending migrations.

### Windows Service
- **Wrapper:** `pywin32`'s `win32serviceutil` (PSF licence, compatible), in `litfoundry.service.windows`.
- **Service:** `litfoundry`, whose `SvcDoRun` starts the `supervise` loop, while `SvcStop` signals a graceful stop.
- **Account:** configurable, defaulting to a virtual service account (`NT SERVICE\litfoundry`), which the data-root ACL grants.

### Licence gate
- **Collection:** `scripts/licence_check.py` reads installed distribution metadata (`importlib.metadata`) and the vendor lock.
- **Classification:** licences are classified against an allowlist (MIT, BSD, Apache-2.0, LGPL-3.0, GPL-3.0, PSF, MPL-2.0 file-level) and a denylist (GPL-2.0-only, non-commercial).
- **Unknown licences:** they fail the gate unless overridden in a reviewed `licence-overrides.toml`.
- **SBOM:** CycloneDX JSON, produced by `scripts/sbom.py` with `cyclonedx-bom` (Apache-2.0, build-time only).

### Signing
`signtool` runs in the release workflow when the `SIGNING_CERT` secret is present.

## Risks / Trade-offs

- [PyInstaller misses hidden imports, for example from scipy or Biblium] → The clean-host smoke test exercises each analysis type and PRISMA rendering.
- [Transitive licences of Biblium and PyBibX] → The gate checks the full installed set. PyBibX is excluded by default.

## Migration Plan

Not applicable: this change adds packaging only.
