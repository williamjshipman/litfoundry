# Spec Delta: search/source-credentials

## Purpose

Manages bibliographic API credentials: administrator-provided shared keys and optional personal overrides. Jobs always use the right key and never expose or borrow another user's secret.

## ADDED Requirements

### Requirement: Shared credentials
`GET` and `PUT /api/v1/admin/source-credentials/{provider}` SHALL let only the administrator set, enable, disable and remove the shared credential for each provider. They SHALL report whether a secret is configured, its validation status and its usage, never the secret.

#### Scenario: Set shared key
- **WHEN** the administrator saves a shared OpenAlex key
- **THEN** reading the credential shows it as configured and enabled without revealing it

#### Scenario: Non-admin
- **WHEN** a non-admin user calls the shared-credentials endpoint
- **THEN** the response is 403

### Requirement: Personal credentials
`GET` and `PUT /api/v1/me/source-credentials/{provider}` SHALL let each user, local or directory, set, enable, disable and remove their own personal credential for a provider. Users SHALL never see or use another user's personal credential.

#### Scenario: Personal override
- **WHEN** a user saves and enables a personal WoS Starter key
- **THEN** their personal credential status shows it as configured and enabled

### Requirement: Credential precedence
For each provider, a job SHALL use:
1. the job requester's enabled personal credential, if one exists;
2. otherwise, the enabled shared credential;
3. otherwise, none.

A job SHALL never use another user's personal credential, including when the administrator runs or retries it.

#### Scenario: Personal wins
- **WHEN** a user with an enabled personal OpenAlex key runs a search and a shared key also exists
- **THEN** the search uses the personal key

#### Scenario: Admin runs job in user's project
- **WHEN** the administrator launches a search in a project whose owner has a personal key
- **THEN** the search uses the administrator's own personal key or the shared key, never the owner's

### Requirement: Credential origin shown
The GUI SHALL show, for each provider, whether the effective credential for the current user is `personal`, `shared` or `not configured`, without showing secret values.

#### Scenario: Origin indicator
- **WHEN** a user without a personal key opens the search editor and a shared key exists
- **THEN** the source shows credential origin `shared`

### Requirement: Credential validation
Saving a credential, or requesting validation, SHALL test the credential with the provider using a minimal request. The result (valid, invalid or provider unavailable) SHALL be stored and shown.

#### Scenario: Invalid key
- **WHEN** a user saves a key that the provider rejects
- **THEN** the credential is stored with status invalid and the user is told why

### Requirement: Credential provenance
Every source run SHALL record which credential scope it used (`personal`, `shared` or `none`). It SHALL never record the secret.

#### Scenario: Run provenance
- **WHEN** a search runs with the shared key
- **THEN** its source run records credential scope `shared`
