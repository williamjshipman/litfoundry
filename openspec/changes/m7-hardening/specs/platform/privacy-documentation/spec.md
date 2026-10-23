# Spec Delta: platform/privacy-documentation

## Purpose

Tells users and administrators plainly who can see what and which personal data LitFoundry stores. This documentation replaces personal-data tooling in v1.

## ADDED Requirements

### Requirement: Trust model statement
The security documentation SHALL state that:
- the administrator can read and change everything in the application, on the host and in backups;
- project isolation protects users from each other, but not from the administrator or a compromised service identity.

The same statement SHALL appear on the About screen.

#### Scenario: Consistent statements
- **WHEN** the security documentation and the About screen are compared
- **THEN** both describe the same administrator trust model

### Requirement: Personal data inventory
The documentation SHALL list the personal data LitFoundry stores, where it is stored, and whether it is included in project exports and full backups. This covers:
- account names and display names;
- contact emails;
- directory identifiers;
- reviewer decisions and notes;
- audit trails;
- sign-in records.

#### Scenario: Reviewer data in exports
- **WHEN** an administrator reads the personal data inventory
- **THEN** it states that reviewer identities and decisions are included in project exports

### Requirement: Manual request process
The documentation SHALL describe how the administrator handles personal-data access and erasure requests manually in v1, and what the limits are. In particular, append-only audit and review histories are kept for research integrity.

#### Scenario: Erasure request guidance
- **WHEN** an administrator looks up how to handle an erasure request
- **THEN** the documentation gives the manual steps and explains which histories cannot be removed

### Requirement: Security notes
The security documentation SHALL describe:
- the deployment boundary (HTTPS, loopback application, firewall);
- the authentication methods;
- secret storage, including that backups are unencrypted;
- upload handling;
- log redaction.

#### Scenario: Backup warning in security notes
- **WHEN** an administrator reads the security notes
- **THEN** they state that full backups are unencrypted, contain secrets and must be stored with restricted access
