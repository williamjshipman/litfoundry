# Proposal: M2 Active Directory sign-in

## Why

Many organisations want staff to use their directory credentials. Active Directory sign-in is MUST for v1 (v1.3 §0.2), but it is optional for each installation. Supporting it means one domain and a required read-only service account; only pre-provisioned users can sign in; and the built-in `admin` stays local (v1.3 decision 2). The design must not let LitFoundry lock out domain accounts or fail open when the domain is unreachable.

## What Changes

- **Connection management:**
  - a single-domain AD configuration with a required service account and TLS (LDAPS or StartTLS) with certificate validation;
  - a connection test that must pass before AD can be enabled;
  - disabling or removing AD revokes all AD sessions.
- **AD sign-in:**
  - a method selector on the sign-in page;
  - `DOMAIN\name`, UPN and bare `sAMAccountName` identifiers;
  - the service account looks the user up first, and provisioning and account state are checked **before** any user bind;
  - a generic failure response;
  - throttling kept below the domain lockout threshold;
  - `admin` rejected for this provider.
- **Revalidation:** active AD users are rechecked periodically, sessions are revoked on disable, lockout, deletion or SID change, and a grace period bounds how long LitFoundry tolerates an unreachable domain.
- **Provisioning:** the admin resolves an AD account and binds its SID to a new LitFoundry user. Rebinding and local↔AD conversion are explicit, audited actions.
- **Diagnostics:** admin-only diagnostic events for domain, certificate and service-account failures.

## Capabilities

### New Capabilities

- `identity/directory-connection`: the AD configuration, service account, TLS policy, connection test, enable/disable, revalidation and diagnostics.
- `identity/directory-sign-in`: the AD sign-in flow, identifier forms, lookup-first and provisioning-first checks, password bind and throttling.
- `identity/directory-provisioning`: resolving AD accounts, SID binding, rebinding and account-type conversion.

### Modified Capabilities

None. The AD method selector appears through `/auth/methods`, which `identity/sessions` already specifies.

## Impact

- **v1.3 sections implemented:**
  - §4.1: the `directory_config` and `directory_identity_bindings` tables;
  - §5.1: the AD parts;
  - §5.3;
  - §5.5: the AD parts;
  - §13: the AD selector and the Admin AD screens;
  - §14: the `/admin/ad-directory` routes;
  - §14: the AD-bound users in `/admin/users`;
  - §14: `AUTH_PROVIDER_DISABLED`, `DIRECTORY_UNAVAILABLE` and `AD_IDENTITY_AMBIGUOUS`;
  - §19: group 2 (AD) and group 12 (AD end to end);
  - §20: M2.
- **Depends on:** `m1-local-identity` and `m1-platform-foundation` (secret storage). It is independent of the other M2 changes.
- **Code:** `src/litfoundry/auth/active_directory.py`, the catalogue revision, the API routes and the Admin → Authentication and AD user screens. Test fixtures cover ldap3 MOCK strategies and a Samba AD DC container for Linux CI.
- **Dependencies introduced:** `ldap3` 2.9.1 (LGPL-3.0, GPLv3-compatible), pinned.
- **Non-goals (MAY):** multiple domains, Windows SSO/Kerberos, and roles from AD groups.
