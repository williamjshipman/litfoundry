# Spec Delta: identity/directory-provisioning

## Purpose

Lets the administrator pre-provision Active Directory users by binding their immutable SID to a LitFoundry account, and manage those bindings explicitly and auditably.

## ADDED Requirements

### Requirement: Resolve an AD account
`POST /api/v1/admin/ad-directory/resolve-user` SHALL let the administrator look up an AD account through the service account. It SHALL return the account's display name, `sAMAccountName`, UPN, SID and enabled state. If more than one object matches, it SHALL fail with `AD_IDENTITY_AMBIGUOUS`.

#### Scenario: Resolve user
- **WHEN** the administrator resolves `jsmith`
- **THEN** the response shows the matching account's name, UPN and SID for confirmation

#### Scenario: Ambiguous match
- **WHEN** the search term matches two directory objects
- **THEN** the response is `AD_IDENTITY_AMBIGUOUS`

### Requirement: Create an AD-bound user
`POST /api/v1/admin/users` with account type `active_directory` and a resolved SID SHALL create a LitFoundry user and its SID binding, with no LitFoundry password. The binding SHALL store the SID, the GUID and the normalised account name and UPN.

#### Scenario: Provision AD user
- **WHEN** the administrator confirms a resolved AD account
- **THEN** a LitFoundry user bound to that SID exists and can sign in through AD

### Requirement: SID is the binding key
Each SID SHALL be bound to at most one LitFoundry user. Bindings SHALL be matched by SID, never by account name or email address.

#### Scenario: Duplicate SID
- **WHEN** the administrator tries to provision a SID that is already bound
- **THEN** the request fails with `CONFLICT`

#### Scenario: Renamed AD account
- **WHEN** an AD account's `sAMAccountName` changes but its SID does not
- **THEN** the user keeps signing in to the same LitFoundry account

### Requirement: Explicit rebinding
Rebinding a LitFoundry user to a different SID SHALL be an explicit administrator action: a `rebind` object in the body of `PATCH /api/v1/admin/users/{user_id}`. It SHALL check for collisions and record an audit event.

#### Scenario: Rebind
- **WHEN** the administrator rebinds a user to a new SID that no other user holds
- **THEN** the binding changes and an audit event records old and new SIDs

### Requirement: Account type conversion
Converting an account between local and AD SHALL be an explicit, audited administrator action: a `conversion` object in the body of `PATCH /api/v1/admin/users/{user_id}`. The two conversions are:
- **Local to AD:** binds a resolved SID and removes the password.
- **AD to local:** removes the binding, sets a username and a temporary password, and requires a password change.

Ownership and ACL entries SHALL be unaffected, and the account's sessions SHALL be revoked.

#### Scenario: Convert to local
- **WHEN** the administrator converts an AD user to a local account
- **THEN** the user keeps their projects and must sign in locally with the temporary password

#### Scenario: Direct type change still rejected
- **WHEN** a PATCH sets the account type directly instead of using a `conversion` object
- **THEN** the request fails with `VALIDATION_ERROR` and the account is unchanged

### Requirement: AD provisioning screen
Admin → Users → New → Active Directory SHALL search the directory through the service account, show the matching account (name, UPN, SID) for confirmation and then create the bound user.

#### Scenario: Provision from GUI
- **WHEN** the administrator searches, confirms and saves an AD user
- **THEN** the user appears in the account list as an AD account

### Requirement: Binding changes audited
Every creation, rebinding, conversion or removal of a directory binding SHALL be recorded in the system audit log.

#### Scenario: Audit entry
- **WHEN** the administrator provisions an AD user
- **THEN** the audit log shows the action, the user UUID and the SID
