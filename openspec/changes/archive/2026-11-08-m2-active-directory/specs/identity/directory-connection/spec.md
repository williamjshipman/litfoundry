# Spec Delta: identity/directory-connection

## Purpose

Lets the administrator connect one Active Directory domain securely through a read-only service account, and keeps AD-backed sessions consistent with the directory over time.

## ADDED Requirements

### Requirement: Single-domain configuration
`GET`, `PUT` and `DELETE` on `/api/v1/admin/ad-directory` SHALL let only the administrator view, set and remove the configuration of one AD domain. The configuration consists of:
- domain DNS name and NetBIOS name;
- UPN suffixes;
- domain controller hostnames and Base DN;
- TLS mode (`ldaps` or `starttls`) and CA bundle;
- timeouts;
- revalidation interval and grace period;
- service-account identity and password.

#### Scenario: Configure domain
- **WHEN** the administrator saves a complete configuration
- **THEN** it is stored with a new revision and AD sign-in remains disabled until enabled

#### Scenario: Non-admin access
- **WHEN** a non-admin user calls `/api/v1/admin/ad-directory`
- **THEN** the response is 403

### Requirement: Required service account
An AD connection SHALL NOT be enabled without a service-account identity and password. The service-account password SHALL be write-only and stored encrypted.

#### Scenario: Enable without service account
- **WHEN** the administrator enables AD with no service account configured
- **THEN** the request fails with `VALIDATION_ERROR`

### Requirement: Connection test before enabling
`POST /api/v1/admin/ad-directory/test` SHALL check, and return sanitised per-check results for:
- TLS connectivity to each configured domain controller;
- the certificate chain and hostname;
- the service-account bind and a test search.

Enabling AD SHALL require a passing test of the current configuration revision.

#### Scenario: Certificate failure
- **WHEN** a domain controller's certificate does not chain to the configured CA
- **THEN** the test reports a certificate failure and AD cannot be enabled

#### Scenario: Config changed after test
- **WHEN** the configuration is edited after a passing test
- **THEN** enabling requires a new passing test

### Requirement: Mandatory transport security
Every directory connection SHALL use LDAPS or StartTLS with certificate-chain and hostname validation. In server mode, plaintext simple binds and disabled certificate verification SHALL be refused.

#### Scenario: Plaintext refused
- **WHEN** a configuration attempts plain LDAP without TLS in server mode
- **THEN** it is rejected with `VALIDATION_ERROR`

### Requirement: Bounded directory connections
Directory connections SHALL use finite connect and read timeouts. They SHALL go only to the configured domain controllers and SHALL NOT follow referrals elsewhere.

#### Scenario: Referral returned
- **WHEN** a domain controller returns a referral to another host
- **THEN** LitFoundry does not contact that host

### Requirement: Admin-only diagnostics
Domain-unreachable, certificate and service-account failures SHALL be recorded as distinct diagnostic events visible only to the administrator. Sign-in responses SHALL stay generic.

#### Scenario: Service account password expired
- **WHEN** the service-account bind fails during sign-in
- **THEN** the user sees a generic failure and the administrator sees a service-account failure event

### Requirement: Periodic revalidation
At each revalidation interval (default 15 minutes), the system SHALL recheck every active AD-bound user through the service account. It SHALL revoke the user's sessions if the AD account is disabled, locked, deleted or has a changed SID.

#### Scenario: Account disabled in AD
- **WHEN** an AD account with a live LitFoundry session is disabled in the directory
- **THEN** the session is revoked at or before the next revalidation

### Requirement: Unreachable domain grace period
If the domain cannot be reached for longer than the configured grace period, AD-backed sessions SHALL be refused for mutations. AD users SHALL sign in again once the domain is reachable. LitFoundry SHALL never fail open indefinitely.

#### Scenario: Long outage
- **WHEN** the domain has been unreachable for longer than the grace period
- **THEN** AD users' write requests are refused and local accounts are unaffected

### Requirement: Disabling or removing AD
Disabling or deleting the AD configuration SHALL block AD sign-in and revoke all AD users' sessions on their next request. AD users' projects SHALL remain, and the administrator SHALL still be able to open or transfer them.

#### Scenario: Disable AD
- **WHEN** the administrator disables AD
- **THEN** every AD session is rejected on its next request and `/api/v1/auth/methods` no longer lists AD

### Requirement: Admin authentication screen
Admin → Authentication SHALL present the AD connection settings, enable/disable, the connection test with sanitised results, and the audit history of authentication changes. It SHALL state that the per-identifier failure limit must stay below the domain lockout threshold.

#### Scenario: Lockout guidance shown
- **WHEN** the administrator opens the AD settings
- **THEN** the lockout-threshold guidance is displayed next to the throttling settings
