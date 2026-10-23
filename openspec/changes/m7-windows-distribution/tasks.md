# Tasks: M7 Windows distribution and licence compliance

## 1. Licence compliance

- [ ] 1.1 Implement `scripts/licence_check.py` (allowlist, denylist, reviewed overrides, vendor files) and the CycloneDX SBOM generation. Verify that a seeded GPL-2.0-only dependency fails the gate, and that the default build bundles no optional machine-learning stack.
- [ ] 1.2 Assemble `LICENSES/` (GPLv3, component licences, notices) and the corresponding-source offer. Verify with a package-content test.
- [ ] 1.3 Enforce the lockfile check in the release workflow. Verify that the build fails on an unpinned dependency.

## 2. Windows package and service

- [ ] 2.1 Create the PyInstaller spec (onedir, frontend assets, migrations, licences, bundle-aware asset paths, data paths only from configuration). Verify that the package runs `litfoundry --version` and `litfoundry status` on a CI Windows runner.
- [ ] 2.2 Implement `litfoundry service install|uninstall` with pywin32 (service `litfoundry` running `supervise`, configurable account, uninstall keeps data). Verify with a service lifecycle test on the Windows runner.
- [ ] 2.3 Build the Inno Setup installer (mode choice, data-root creation and ACL through `init`, token display, optional service, upgrade with migrate instruction). Verify with a scripted silent install, upgrade and uninstall test.
- [ ] 2.4 Add signing in the release workflow when a certificate is configured, and unsigned labelling otherwise. Verify with a workflow dry run.
- [ ] 2.5 Add the clean-host smoke test (fresh Windows VM or runner, no internet: install, init, bootstrap, sign-in, project, PRISMA SVG, one analysis, UI load). Verify that it passes for the release build (§19 group 13).

## 3. Venv platforms and docs

- [ ] 3.1 Add venv smoke tests on Linux and macOS CI (init, supervise, UI load offline). Verify that they pass (§19 group 13).
- [ ] 3.2 Write `docs/deployment-windows.md`, `docs/deployment-linux.md` and `docs/deployment-macos.md` (venv, proxy, firewall, CA trust, AD prerequisites, service-account access to UNC backups, backup destination permissions). Verify with a docs review checklist covering each item.
