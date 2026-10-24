# Proposal: M7 hardening and release acceptance

## Why

Before release, LitFoundry must stay usable under realistic load, resist resource exhaustion by any one user, and tell users and administrators plainly what data it holds and who can see it. These requirements come from v1.3 decision 9, §17 and §19. The release also needs an end-to-end check against the v1.3 definition of done.

## What Changes

- **Capacity quotas:** configurable limits with documented safe defaults:
  - projects per user;
  - storage per project;
  - upload and archive sizes;
  - queued jobs per user;
  - concurrent jobs per user and worker count, which queue jobs rather than refuse them.

  Exceeding a quota returns `QUOTA_EXCEEDED`.
- **Performance baseline:**
  - server pagination for 50,000-record projects;
  - a typical project dashboard within 2 seconds on a modern LAN machine;
  - no bibliographic call on request threads;
  - a load-test gate with simultaneous viewers and editors on at least 10,000 source records.
- **Trust and privacy documentation:**
  - security notes stating the administrator trust model and the limits of project isolation;
  - documentation of the personal data stored (account names, contact emails, reviewer decisions, audit trails);
  - the manual process for personal-data requests.
- **Release acceptance:**
  - the full end-to-end GUI scenario from v1.3 §19 group 12;
  - crash and reboot resilience checks;
  - verification of the §19 definition of done on a clean Windows host.

## Capabilities

### New Capabilities

- `platform/capacity-quotas`: configurable resource quotas with safe defaults and consistent errors.
- `platform/performance-baseline`: response-time and scale targets, with a load-test gate.
- `platform/privacy-documentation`: trust-model, security and personal-data documentation for users and administrators.

### Modified Capabilities

None.

## Impact

- **v1.3 sections implemented:**
  - §1: decision 9 (documentation);
  - §17: capacity budgets, process termination, security notes and personal data;
  - §19: performance targets, group 12 (complete flow) and the definition of done;
  - §0.2: personal data is document-only;
  - §20: M7 (security and performance hardening).
- **Depends on:** all other v1 changes. This is the final v1 change.
- **Code:** `src/litfoundry/config.py` (quota settings), quota checks at the creation points, `tests/load/`, `tests/e2e/test_release_flow.py`, `docs/security.md` and `docs/privacy.md`.
- **Out of scope (MAY):** personal-data export and pseudonymisation tooling, and TOTP for `admin`.
