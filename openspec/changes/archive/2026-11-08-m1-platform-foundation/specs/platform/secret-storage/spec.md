# Spec Delta: platform/secret-storage

## Purpose

Protects stored secrets at rest and keeps them out of API responses, logs and exports, while a full backup can still restore them on another machine. The stored secrets are source API keys, the Active Directory service-account password and the session signing key.

## ADDED Requirements

### Requirement: Portable master key
`litfoundry init` SHALL generate a random master key and store it as a file in `<data_root>/secret_material/`, protected by operating-system permissions. The key SHALL NOT be bound to Windows DPAPI or to a macOS or Linux keychain.

#### Scenario: Master key created
- **WHEN** `litfoundry init` initialises a data root
- **THEN** a master key file exists in `secret_material/`, readable only by the service identity and host administrators

#### Scenario: Restore on another machine
- **WHEN** a data root, including `secret_material/`, is copied to a different machine
- **THEN** stored secrets can be decrypted there without any extra step

### Requirement: Encryption of stored secrets
Source API keys and the Active Directory service-account password SHALL be stored in the catalogue only in encrypted form, using the master key. No catalogue column or settings value SHALL hold such a secret in clear text.

#### Scenario: Ciphertext at rest
- **WHEN** an administrator saves a shared API key
- **THEN** reading `catalog.sqlite` directly does not reveal the key

### Requirement: Session signing key
`litfoundry init` SHALL generate a random session signing key and store it in `secret_material/`. The key SHALL be replaceable by a rotation operation that invalidates all existing sessions.

#### Scenario: Rotation invalidates sessions
- **WHEN** the session signing key is rotated
- **THEN** every previously issued session is rejected on its next request

### Requirement: Write-only secret fields
No REST response or GUI screen SHALL return a stored secret value. Secret fields SHALL report only whether a value is configured. An update that omits a secret field SHALL keep the stored value.

#### Scenario: Reading a credential
- **WHEN** an administrator reads a configured shared credential
- **THEN** the response states that a secret is configured and contains no part of it

#### Scenario: Partial update keeps secret
- **WHEN** an administrator updates other fields of a credential and omits the secret field
- **THEN** the stored secret is unchanged

### Requirement: Secrets never leak
Stored secrets, password hashes and tokens SHALL NOT appear in any of the following:
- log entries;
- job arguments;
- error responses;
- audit details;
- project exports;
- configuration metadata;
- archive manifests.

No HTTP route SHALL serve files from `secret_material/`.

#### Scenario: Secret scan after test run
- **WHEN** the integration suite has configured known test secrets and run to completion
- **THEN** none of those secrets appears in any log file, audit record, job record or generated export

#### Scenario: Secret files not served
- **WHEN** a client requests any URL that maps to `secret_material/`
- **THEN** the server returns 404 and no file content
