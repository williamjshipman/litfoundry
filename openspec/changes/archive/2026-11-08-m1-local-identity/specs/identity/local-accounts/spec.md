# Spec Delta: identity/local-accounts

## Purpose

Local LitFoundry accounts, which are always available and are the only way `admin` signs in. Each account has a username and a LitFoundry-managed password, with throttling that cannot lock out the administrator.

## ADDED Requirements

### Requirement: Username rules
Local usernames SHALL be stored lowercased, SHALL match `^[a-z0-9][a-z0-9._-]{1,63}$` and SHALL be unique. Matching at sign-in SHALL be case-insensitive.

#### Scenario: Case-insensitive sign-in
- **WHEN** the account `jsmith` signs in as `JSmith` with the correct password
- **THEN** sign-in succeeds

#### Scenario: Invalid username
- **WHEN** the administrator tries to create a local account named `j@smith` or `corp\jsmith`
- **THEN** creation fails with `VALIDATION_ERROR`

### Requirement: Local sign-in
`POST /api/v1/auth/login` with `provider` `local` SHALL authenticate a local account by username and password and start a session. When `provider` is omitted, it SHALL default to `local`.

#### Scenario: Successful local sign-in
- **WHEN** an active local user posts the correct username and password
- **THEN** the session cookies are set and `/api/v1/auth/me` returns the user

#### Scenario: Provider omitted
- **WHEN** a sign-in request has no `provider`
- **THEN** it is processed as a local sign-in

### Requirement: Generic sign-in failure
A wrong password, an unknown username and a disabled account SHALL all produce the same generic `UNAUTHENTICATED` response, with similar timing.

#### Scenario: Unknown versus wrong password
- **WHEN** one request uses an unknown username and another uses a known username with a wrong password
- **THEN** both responses are identical apart from `request_id`

### Requirement: Password storage
Local passwords SHALL be stored only as salted, memory-hard hashes and SHALL never be returned or logged.

#### Scenario: Hash at rest
- **WHEN** a local account's password is set
- **THEN** the catalogue holds only a hash, and no API response contains the hash

### Requirement: Password policy
Passwords set through bootstrap, account creation, reset or change SHALL satisfy the administrator-configured password policy. The policy includes minimum length and SHALL be configurable through `GET`/`PUT /api/v1/admin/auth-settings`.

#### Scenario: Too short
- **WHEN** a user sets a password shorter than the policy minimum
- **THEN** the change fails with `VALIDATION_ERROR`

### Requirement: Forced password change
An account flagged for password change SHALL be able only to change its password, read `/auth/me` and sign out, until the password is changed.

#### Scenario: First sign-in
- **WHEN** a user signs in with an administrator-set initial password
- **THEN** every other API call is refused with `FORBIDDEN` and code detail `PASSWORD_CHANGE_REQUIRED` until the password is changed

### Requirement: Change own password
`PUT /api/v1/auth/password` SHALL let a local account change its password by supplying the current password. On success it SHALL revoke the account's other sessions. Accounts that are not local SHALL receive `FORBIDDEN`.

#### Scenario: Other sessions revoked
- **WHEN** a user signed in on two browsers changes the password in one
- **THEN** the other browser's next request is rejected as unauthenticated

### Requirement: Sign-in throttling
Failed sign-ins SHALL be throttled per source IP and per provider and normalised identifier, with exponential backoff. A throttled request SHALL receive 429 `AUTH_THROTTLED` with `Retry-After`, without the password being checked. Throttle settings SHALL be configurable through `/api/v1/admin/auth-settings`.

#### Scenario: Repeated failures
- **WHEN** an identifier exceeds the configured failure limit
- **THEN** further attempts receive 429 `AUTH_THROTTLED` until the backoff expires

### Requirement: Administrator never locked out
Failed sign-ins to `admin` SHALL be throttled only per source IP and SHALL never lock or throttle the account as a whole.

#### Scenario: Attack from another address
- **WHEN** one IP address triggers throttling with failed `admin` sign-ins
- **THEN** the correct `admin` password still succeeds from a different IP address

### Requirement: Contact email is informational
A local account's optional contact email and display name SHALL be informational only. Neither SHALL be accepted as a sign-in identifier, and no email verification or mail transport SHALL be required.

#### Scenario: Email as identifier
- **WHEN** a user tries to sign in with their contact email address
- **THEN** sign-in fails as for an unknown username
