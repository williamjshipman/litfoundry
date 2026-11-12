# Spec Delta: identity/admin-bootstrap

## Purpose

Creates the single built-in local `admin` account safely on first run, with no factory default password, and guarantees that the administrator can always be recovered by someone with host access.

## ADDED Requirements

### Requirement: Setup gate
While no administrator exists, every endpoint except the following SHALL be refused with 503 `SETUP_REQUIRED`:
- `/api/v1/health/live`
- `/api/v1/setup/status`
- `/api/v1/setup/admin`
- static GUI assets

The GUI SHALL show the setup page.

#### Scenario: Locked before setup
- **WHEN** a client calls `GET /api/v1/projects` on an installation without an administrator
- **THEN** the response is 503 with code `SETUP_REQUIRED`

#### Scenario: Setup status
- **WHEN** a client calls `GET /api/v1/setup/status`
- **THEN** the response states whether setup is required and contains no secrets

### Requirement: Bootstrap token issuance
`litfoundry init`, or the first service start while setup is pending, SHALL generate a single-use, short-lived bootstrap token. It SHALL print the token on the interactive console when there is one, and write it to `<data_root>/bootstrap-token.txt`, readable only by the service identity and host administrators. The token SHALL never be logged.

#### Scenario: Token delivered on host
- **WHEN** `litfoundry init` runs interactively on a new data root
- **THEN** the token is printed and written to `bootstrap-token.txt` with restricted permissions
- **AND** no log file contains the token

### Requirement: Bootstrap token reissue
`litfoundry bootstrap-token` SHALL issue a new token and invalidate any earlier one while setup is pending. It SHALL refuse once setup is complete.

#### Scenario: Reissue after expiry
- **WHEN** the token expired and the operator runs `litfoundry bootstrap-token`
- **THEN** a new token is issued and the old token no longer works

#### Scenario: Reissue after setup
- **WHEN** an operator runs `litfoundry bootstrap-token` after setup
- **THEN** the command fails and issues nothing

### Requirement: Expired token cleanup
An expired bootstrap token SHALL never be accepted. Its `bootstrap-token.txt` file SHALL be deleted at the next service start, at the next housekeeping run, or when the expired token is used, whichever comes first.

#### Scenario: Token expires unused
- **WHEN** the bootstrap token expires without being used and the service restarts
- **THEN** `bootstrap-token.txt` no longer exists and setup requires a newly issued token

#### Scenario: Expired token used
- **WHEN** a client calls `POST /api/v1/setup/admin` with an expired token
- **THEN** the request fails and the token file is deleted

### Requirement: Administrator creation
`POST /api/v1/setup/admin` SHALL accept a valid bootstrap token and a new password that meets the password policy. It SHALL create the local account with username exactly `admin` and role `admin`. Clients SHALL NOT be able to choose the username. No factory default password SHALL exist.

#### Scenario: Successful setup
- **WHEN** a client posts a valid token and a strong password
- **THEN** the local account `admin` exists with that password, the token file is deleted and the token cannot be reused

#### Scenario: Weak password
- **WHEN** the password violates the password policy
- **THEN** setup fails with `VALIDATION_ERROR` and the token remains usable

### Requirement: Single successful bootstrap
Token consumption SHALL be atomic, so that exactly one of any concurrent setup attempts succeeds. After setup, `/api/v1/setup/admin` SHALL always fail.

#### Scenario: Concurrent setup attempts
- **WHEN** two setup requests with the same valid token arrive at the same time
- **THEN** exactly one creates the administrator and the other fails

#### Scenario: Setup repeated
- **WHEN** a client calls `POST /api/v1/setup/admin` after setup is complete
- **THEN** the request fails and no account changes

### Requirement: Administrator invariants
The `admin` account SHALL NOT be deletable, renamable or disableable. No second account SHALL ever hold the `admin` role. The `admin` account SHALL always be a local account.

#### Scenario: Disable admin refused
- **WHEN** a request tries to disable or rename `admin`
- **THEN** the request fails with `FORBIDDEN` and the account is unchanged

#### Scenario: Second admin refused
- **WHEN** any request tries to give another account the `admin` role
- **THEN** the request fails and no account has the role except `admin`

### Requirement: Host-only administrator recovery
`litfoundry admin reset-password` SHALL reset the `admin` password from the host. It requires operating-system access to the data root, enforces the password policy, revokes all `admin` sessions and records an audit event. No web endpoint SHALL reset the `admin` password without the current password.

#### Scenario: Lost admin password
- **WHEN** an operator with access to the data root runs `litfoundry admin reset-password` and enters a new password
- **THEN** `admin` can sign in with the new password, earlier `admin` sessions are rejected and an audit event is recorded

### Requirement: Administrator password changes audited
Every change to the `admin` password SHALL record an audit event without the password.

#### Scenario: Admin changes own password
- **WHEN** `admin` changes their password through the GUI
- **THEN** an audit event records the change
