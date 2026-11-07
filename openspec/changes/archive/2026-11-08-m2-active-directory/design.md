# Design: M2 Active Directory sign-in

## Context

`m1-local-identity` provides the `IdentityProvider` abstraction, sessions, throttling and audit, and `m1-platform-foundation` provides encrypted secret storage. This change adds `ActiveDirectoryProvider` and its administration.

## Goals / Non-Goals

**Goals:**
- Never bind as a user who cannot use LitFoundry. This avoids adding to the domain's bad-password counts and prevents lockout denial-of-service.
- The same behaviour on Windows, Linux and macOS servers (ldap3 is pure Python).

**Non-Goals:**
- More than one domain.
- Kerberos or browser SSO.
- Group-based roles.
- Just-in-time provisioning.

## Decisions

### Library
- **Version:** `ldap3` pinned at 2.9.1, the latest stable release. 2.10.x is still at release candidate (v1.3 A.3).
- **Testing:** the AD suite runs on every supported Python version in CI.
- **Encapsulation:** the library is wrapped behind `DirectoryClient`, so it can be replaced if ldap3 stalls.

### Connection
- **Pool:** `ServerPool` of the configured domain controllers, in `FIRST` strategy with active checks.
- **Server objects:** created with `get_info=NONE`, `connect_timeout` and `use_ssl` for LDAPS. StartTLS calls `start_tls()` before any bind.
- **TLS:** `Tls(validate=CERT_REQUIRED, ca_certs_file=<bundle>, version=TLSv1.2+)`, with hostname checking on.
- **Referrals:** `auto_referrals=False`.
- **Read timeout:** `receive_timeout` on every `Connection`.

### Sign-in sequence
1. Throttle check (IP and identifier).
2. Parse the identifier form and reject `admin`.
3. Bind as the service account.
4. Search with `escape_filter_chars` values and the attribute allowlist. Exactly one result is required.
5. Look up the SID binding. Check the LitFoundry user is active, and that `userAccountControl` and `msDS-User-Account-Control-Computed` show the account is not disabled or locked.
6. Only then open a new connection and do a simple bind as the user's DN with the password. Reject empty passwords before this step.
7. Unbind in `finally`.

Every failure branch returns the same response after a padded minimum duration (timing equalisation).

### Revalidation
- **Scheduling:** a periodic job type, `ad_revalidation`, re-enqueues itself at the configured interval, using the M2 job framework.
- **Check:** for each active AD-bound user, the job looks up the SID through the service account.
- **Revocation:** on disable, lock, missing account or SID change, it increments `users.session_version`.
- **Reachability state:** the job records `last_directory_success_at`.
- **Grace enforcement:** the session check refuses AD mutations once `now - last_directory_success_at > grace`.

### Disable
Disabling AD increments `auth_settings.revision`. Under the M1 revalidation rule, this revokes all sessions, including local ones. A narrower alternative is a dedicated `directory_revision` claim that only AD sessions carry, which revokes AD sessions only.
- **Decision:** add `dr` (directory revision) to AD tokens and increment it on disable, so local sessions survive.
- **Departure from v1.3:** v1.3 §5.3 rule 8 names `auth_settings.revision` for this. The intended effect is the same, and the departure is recorded in `docs/decisions.md`.

### Testing
- **Unit tests:** ldap3 `MOCK_SYNC` with a fixture directory (users, disabled flags, duplicate names, special characters).
- **Integration tests:** a Samba AD DC container on Linux CI with LDAPS. They cover bad certificates, an expired service account, a domain outage (container stopped) and lockout-threshold behaviour.

## Risks / Trade-offs

- [ldap3 maintenance is slow] → Pin it, run the tests on every Python version, and keep `DirectoryClient` as a thin seam.
- [Samba AD behaves differently from Windows AD for the computed UAC attribute] → Read both attributes and test the lockout path against the mock as well.
- [Timing padding slows failed sign-ins] → Acceptable, and bounded at about 1 s.

## Migration Plan

Catalogue revision adding `directory_config` and `directory_identity_bindings` (unique SID, unique `user_id`).
