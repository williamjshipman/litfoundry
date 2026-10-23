# Spec Delta: identity/user-administration

## Purpose

Lets the built-in administrator, and only the administrator, create and manage user accounts and their sessions. LitFoundry has no self-registration.

## ADDED Requirements

### Requirement: Administrator-only account management
Only the `admin` account SHALL be able to call `/api/v1/admin/users` endpoints or open Admin → Users. Other accounts SHALL receive 403 `FORBIDDEN`.

#### Scenario: User calls admin endpoint
- **WHEN** a non-admin user calls `GET /api/v1/admin/users`
- **THEN** the response is 403

### Requirement: No self-registration
No endpoint or screen SHALL let an unauthenticated or non-admin caller create an account.

#### Scenario: Registration attempt
- **WHEN** an unauthenticated client posts account details to any endpoint
- **THEN** no account is created

### Requirement: List accounts
`GET /api/v1/admin/users` SHALL return a paginated, filterable list of accounts. Each entry includes UUID, account type, username or directory name, display name, contact email, role, active state, password-change flag, creation time and last sign-in time. Password hashes SHALL never be returned.

#### Scenario: Account list
- **WHEN** the administrator lists accounts
- **THEN** every account is listed without any password hash

### Requirement: Create local account
`POST /api/v1/admin/users` with account type `local` SHALL create an account from a username, display name, optional contact email and initial password. The account SHALL be required to change the password at first sign-in.

#### Scenario: New local user
- **WHEN** the administrator creates local user `jsmith` with an initial password
- **THEN** `jsmith` can sign in and must change the password before doing anything else

#### Scenario: Duplicate username
- **WHEN** the administrator creates a local user whose normalised username already exists
- **THEN** creation fails with `CONFLICT`

### Requirement: Update and disable accounts
`PATCH /api/v1/admin/users/{user_id}` SHALL let the administrator change display name, contact email and active state. Disabling an account SHALL end its sessions on their next request and SHALL keep its projects.

#### Scenario: Disable user
- **WHEN** the administrator disables a user who owns projects
- **THEN** the user cannot sign in and their projects still exist

### Requirement: Reset local password
`POST /api/v1/admin/users/{user_id}/reset-password` SHALL set a new temporary password on a local account. It SHALL require a password change at next sign-in and revoke the account's sessions. For accounts that are not local, it SHALL fail with `VALIDATION_ERROR`.

#### Scenario: Reset password
- **WHEN** the administrator resets a local user's password
- **THEN** the user's existing sessions end and the next sign-in requires a password change

### Requirement: Revoke sessions
`POST /api/v1/admin/users/{user_id}/revoke-sessions` SHALL invalidate all of the account's sessions and refresh tokens.

#### Scenario: Revoke sessions
- **WHEN** the administrator revokes a user's sessions
- **THEN** every browser session of that user is rejected on its next request

### Requirement: Account type is fixed
An account's type, `local` or directory, SHALL be read-only after creation. The only exception is an explicit, audited conversion action provided by the directory capability.

#### Scenario: Type change through PATCH
- **WHEN** a PATCH request sets a different account type directly, without the explicit conversion action
- **THEN** the request fails with `VALIDATION_ERROR`

### Requirement: Administrator users screen
Admin → Users SHALL list accounts and provide create-local-account, enable/disable, reset-password and revoke-sessions actions. Disable, reset and revoke SHALL require confirmation.

#### Scenario: Create from the GUI
- **WHEN** the administrator completes the create-local-account form
- **THEN** the new account appears in the list
