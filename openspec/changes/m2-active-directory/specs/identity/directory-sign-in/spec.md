# Spec Delta: identity/directory-sign-in

## Purpose

Lets pre-provisioned Active Directory users sign in with their directory credentials. The rules ensure LitFoundry never adds bad-password counts to accounts that cannot use it and never trusts caller-supplied identity data.

## ADDED Requirements

### Requirement: AD provider availability
`POST /api/v1/auth/login` with `provider` `active_directory` SHALL be processed only while AD is configured, tested and enabled. Otherwise it SHALL fail with `AUTH_PROVIDER_DISABLED`. While AD is enabled, the sign-in page SHALL show a `LitFoundry account` / `Active Directory` method selector.

#### Scenario: AD disabled
- **WHEN** a client signs in with provider `active_directory` while AD is disabled
- **THEN** the response is `AUTH_PROVIDER_DISABLED`

#### Scenario: Selector shown
- **WHEN** AD is enabled and a browser opens the sign-in page
- **THEN** the method selector is shown

### Requirement: Accepted identifier forms
AD sign-in SHALL accept these identifier forms, matched case-insensitively:
- `DOMAIN\name`, only for the configured NetBIOS name;
- UPNs, only in the configured suffixes;
- bare `sAMAccountName`.

Other forms SHALL fail generically.

#### Scenario: Wrong NetBIOS domain
- **WHEN** a user signs in as `OTHERDOM\jsmith`
- **THEN** sign-in fails with the generic error

### Requirement: Administrator excluded
The `active_directory` provider SHALL reject the identifier `admin` in every form.

#### Scenario: Admin through AD
- **WHEN** a client signs in with provider `active_directory` and identifier `admin`
- **THEN** sign-in fails without contacting the directory

### Requirement: Look up before binding
The system SHALL use the service account to resolve the identifier to exactly one user object. The search SHALL escape filter values and request only an allowlist of attributes. Ambiguous or missing matches SHALL fail generically.

#### Scenario: LDAP injection attempt
- **WHEN** the identifier is `jsmith*)(objectClass=*`
- **THEN** the search treats it as a literal value and sign-in fails generically

### Requirement: Provisioning checked before password
If the resolved SID has no active LitFoundry binding, or the AD account is disabled or locked, sign-in SHALL fail without binding as the user. The response SHALL be identical, with similar timing, to a wrong-password failure.

#### Scenario: Unprovisioned AD user
- **WHEN** an AD user without a LitFoundry binding signs in with the correct AD password
- **THEN** sign-in fails generically and no bind as that user is attempted

#### Scenario: Disabled AD account
- **WHEN** a provisioned user whose AD account is disabled signs in
- **THEN** sign-in fails generically without a user bind

### Requirement: Password verification by bind
For a provisioned, enabled account, the system SHALL verify the password by binding as the resolved user over the validated TLS connection. Empty passwords SHALL be rejected, and anonymous or unauthenticated binds SHALL never count as success. The password SHALL NOT be stored, logged or reused after the request, and connections SHALL be closed on every path.

#### Scenario: Empty password
- **WHEN** a provisioned AD user submits an empty password
- **THEN** sign-in fails without any bind

#### Scenario: Successful AD sign-in
- **WHEN** a provisioned, enabled AD user submits the correct password
- **THEN** a session starts with provider `active_directory`

### Requirement: AD throttling below lockout threshold
AD sign-in SHALL be throttled per source IP and per identifier. The per-identifier limit SHALL be configurable, with a default of 3 failures per identifier per 15 minutes, so it stays below the domain's lockout threshold.

#### Scenario: Fourth attempt throttled
- **WHEN** an identifier has 3 failed AD sign-ins within 15 minutes under default settings
- **THEN** the next attempt receives 429 `AUTH_THROTTLED` without contacting the directory

### Requirement: Directory unavailable
When no configured domain controller can be reached, AD sign-in SHALL fail with 503 `DIRECTORY_UNAVAILABLE` and SHALL reveal nothing about the account. Local sign-in, including `admin`, SHALL keep working.

#### Scenario: Domain down
- **WHEN** all domain controllers are unreachable
- **THEN** AD sign-in returns `DIRECTORY_UNAVAILABLE` and `admin` can still sign in locally

### Requirement: Separate local and directory accounts
A local account and an AD account with the same name SHALL be separate accounts, distinguished by the explicit provider. There SHALL be no automatic linking, merging or privilege inheritance between them. AD groups SHALL grant no LitFoundry roles.

#### Scenario: Same name, two accounts
- **WHEN** local `jsmith` and AD `jsmith` both exist
- **THEN** signing in with each provider yields different user UUIDs

### Requirement: No LitFoundry password for AD users
AD-bound accounts SHALL have no LitFoundry password. Local password change and reset SHALL be refused for them.

#### Scenario: AD user changes password
- **WHEN** an AD user calls `PUT /api/v1/auth/password`
- **THEN** the response is 403
