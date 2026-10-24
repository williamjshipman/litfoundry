# Spec Delta: identity/sessions

## Purpose

Browser sessions for every sign-in method. Sessions use secure cookies with CSRF protection, rotate their refresh tokens and are revalidated on every request, so revocations take effect immediately.

## ADDED Requirements

### Requirement: Session cookies
Successful sign-in SHALL set the access token in a cookie that is `HttpOnly`, `SameSite=Lax` and `Secure`. `Secure` SHALL be omitted only in workstation mode while bound to loopback. Tokens SHALL never be exposed to JavaScript storage.

#### Scenario: Server-mode cookie flags
- **WHEN** a user signs in through the HTTPS reverse proxy in server mode
- **THEN** the access cookie has `HttpOnly`, `Secure` and `SameSite=Lax`

#### Scenario: No token in browser storage
- **WHEN** the end-to-end suite inspects `localStorage` and `sessionStorage` after sign-in
- **THEN** neither contains a token

### Requirement: CSRF protection
Unsafe HTTP methods on authenticated endpoints SHALL require an `X-CSRF-TOKEN` header that matches the double-submit CSRF cookie issued at sign-in. A missing or wrong header SHALL be rejected with 403 `FORBIDDEN` before the handler runs.

#### Scenario: Missing CSRF header
- **WHEN** a signed-in browser sends a POST without `X-CSRF-TOKEN`
- **THEN** the response is 403 and nothing changes

### Requirement: Short-lived access tokens
Access tokens SHALL expire after a configurable period, 15 minutes by default, set through `/api/v1/admin/auth-settings`.

#### Scenario: Expired access token
- **WHEN** a request presents an access token older than its lifetime
- **THEN** the response is 401 `UNAUTHENTICATED`

### Requirement: Refresh token rotation
A refresh cookie scoped to `/api/v1/auth/refresh` SHALL carry a refresh token with a configurable lifetime. Each refresh SHALL issue a new access token and a new refresh token and revoke the old refresh token. Presenting a rotated refresh token again SHALL revoke its whole token family.

#### Scenario: Normal refresh
- **WHEN** a client calls `POST /api/v1/auth/refresh` with a valid refresh token
- **THEN** new access and refresh cookies are set and the old refresh token is revoked

#### Scenario: Refresh token reuse
- **WHEN** an already-rotated refresh token is presented again
- **THEN** the request fails and every refresh token in that family is revoked

### Requirement: Logout
`POST /api/v1/auth/logout` SHALL revoke the session's refresh-token family and clear the session cookies.

#### Scenario: Logout
- **WHEN** a user logs out
- **THEN** the old refresh token cannot be used

### Requirement: Per-request revalidation
Every protected request SHALL verify, before any processing:
- the account is active;
- the token's session version still matches the account;
- the authentication settings revision has not changed.

Therefore disabling an account, changing or resetting a password, revoking sessions and changing authentication settings that invalidate sessions all take effect on the next request.

#### Scenario: Disabled during session
- **WHEN** the administrator disables an account that has a live session
- **THEN** that session's next request is rejected with 401

### Requirement: Identity is the user UUID
Sessions SHALL identify the account by its immutable user UUID and sign-in provider. Caller-supplied roles, user IDs, SIDs, DNs, LDAP filters or server addresses SHALL never be accepted as proof of identity.

#### Scenario: Forged role field
- **WHEN** a sign-in or API request includes `"role": "admin"` or a `user_id`
- **THEN** the field has no effect on identity or permissions

### Requirement: Current user endpoint
`GET /api/v1/auth/me` SHALL return the current user's UUID, username or directory name, display name, provider, role and global permissions. It SHALL never return credentials or hashes.

#### Scenario: Me endpoint
- **WHEN** a signed-in local user calls `/api/v1/auth/me`
- **THEN** the response contains their UUID, provider `local` and role `user`

### Requirement: Sign-in method discovery
`GET /api/v1/auth/methods` SHALL be available without authentication. It SHALL report that local sign-in is available, and whether Active Directory sign-in is currently available, without revealing configuration details or secrets.

#### Scenario: Local only
- **WHEN** no directory connection is enabled
- **THEN** `/api/v1/auth/methods` lists only local sign-in
- **AND** the sign-in page shows no method selector
