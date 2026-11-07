# Proposal: M1 local identity

## Why

LitFoundry is multi-user and must never ship a default password. The built-in `admin` must be created safely on first run and must always be able to sign in, even when Active Directory (added in M2) is down or disabled. Local username/password accounts are the baseline sign-in method that every installation has (v1.3 decisions 2–3).

## What Changes

- **First-run setup:**
  - Lock the application until setup is complete.
  - Use a single-use, short-lived bootstrap token, delivered on the host console and in a protected file. `litfoundry bootstrap-token` reissues it.
  - Create the fixed local `admin` account.
  - Add host-only `litfoundry admin reset-password`.
- **Local accounts:**
  - usernames with fixed character rules;
  - Argon2id passwords;
  - an admin-configurable password policy;
  - forced password change at first sign-in;
  - changing your own password;
  - throttling per IP and per identifier, which never locks `admin`.
- **Sessions:**
  - cookies with access and refresh tokens and double-submit CSRF;
  - refresh-token rotation with reuse detection;
  - logout;
  - every request revalidated against account state, `session_version` and `auth_settings.revision`;
  - `/auth/methods` and `/auth/me`.
- **User administration (local accounts):** list, create, update, enable/disable, reset password and revoke sessions.
- **System audit log:** `audit_events`, with an admin feed at `/admin/audit-events`.

## Capabilities

### New Capabilities

- `identity/admin-bootstrap`: the first-run setup gate, bootstrap token, fixed `admin` account and host-only recovery.
- `identity/local-accounts`: local usernames, password sign-in, password policy, forced and self-service password change, and throttling.
- `identity/sessions`: session cookies, CSRF, refresh rotation, logout, per-request revalidation and sign-in method discovery.
- `identity/user-administration`: admin-only management of accounts and their sessions.
- `platform/audit-log`: the system audit trail and the admin audit feed.

### Modified Capabilities

None.

## Impact

- **v1.3 sections implemented:**
  - §1: decision 4 and the Roles section;
  - §4.1: the `users`, `auth_settings`, `login_throttle`, `refresh_tokens` and `audit_events` tables;
  - §5.1: the local parts;
  - §5.2;
  - §5.4;
  - §5.5: the local parts;
  - §13: Setup/Login and Admin users;
  - §14: the setup, auth, admin user, auth-settings and audit-event routes;
  - §17: the authentication bullets;
  - §18.1: `bootstrap-token` and `admin reset-password`;
  - §19: groups 1 and 2 (local part);
  - §20: M1.
- **Depends on:** `m1-platform-foundation` and `m1-web-foundation`.
- **Code:** `src/litfoundry/auth/`, `src/litfoundry/catalog/` models and migration revision, `src/litfoundry/api/auth.py` and `admin_users.py`, frontend setup, sign-in and Admin → Users screens.
- **Dependencies introduced:** Flask-JWT-Extended and argon2-cffi (both MIT).
- **Out of scope:**
  - Active Directory, including the method selector on the sign-in form and the AD-specific user administration (`m2-active-directory`);
  - project ownership transfer (`m2-project-workspaces`);
  - `/users/lookup` (`m2-project-access-control`).
