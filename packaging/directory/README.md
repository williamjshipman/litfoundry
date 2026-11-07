# Active Directory Configuration Prerequisites

This document covers the prerequisites and configuration steps for enabling Active Directory (LDAP) authentication in LitFoundry v1.3+.

## Active Directory Prerequisites

Before configuring LitFoundry to use Active Directory, ensure:

### 1. Service Account

- **Create a read-only service account** in the domain with:
  - A non-expiring or long-lived password (e.g., 5 years)
  - Minimal permissions: read permissions on the Users container and permission to read `userAccountControl` and `msDS-User-Account-Control-Computed` attributes
  - The account should **not** have permission to change passwords or modify user objects

- **Avoid using:**
  - The built-in `Administrator` or `Domain Admin` accounts
  - Accounts with unlimited password age (except the service account itself)
  - Privileged accounts that could grant too much access

### 2. Domain Controller Access

- **Ensure network connectivity** from the LitFoundry server to at least one domain controller
- **Note the following for configuration:**
  - Domain DNS name (e.g., `example.com`)
  - Domain NetBIOS name (e.g., `EXAMPLE`)
  - Domain controller hostnames (e.g., `dc1.example.com`, `dc2.example.com`)
  - Base DN for LDAP (e.g., `DC=example,DC=com`)
  - UPN suffixes used in the domain (e.g., `@example.com`)

### 3. TLS/SSL Certificate

LitFoundry **requires** TLS for all directory connections (LDAPS or StartTLS). To verify the certificate chain:

#### For LDAPS (Port 636)

```bash
# On Linux/macOS
echo | openssl s_client -connect dc1.example.com:636 -showcerts

# Or use ldapsearch with -ZZ for StartTLS
ldapsearch -H ldap://dc1.example.com -x -D "CN=admin,CN=Users,DC=example,DC=com" \
  -w password -b "DC=example,DC=com" -s base "(objectclass=*)" > /dev/null
```

#### Obtain the CA Certificate

- **For Active Directory Certificate Services (ADCS):**
  1. Connect to your root or issuing CA: `http://<ca-server>/certsrv`
  2. Select "Download a CA certificate"
  3. Download the CA certificate (PEM format preferred)
  4. If not available in PEM, convert from `.cer`:
     ```bash
     openssl x509 -inform DER -in ca.cer -out ca.pem
     ```

- **For self-signed or third-party CAs:**
  - Obtain the CA bundle from your certificate provider
  - Save in PEM format (one certificate per file or concatenated)

### 4. Firewall and Network Policy

- **Ensure the LitFoundry server can reach domain controllers:**
  - LDAP (port 389) for StartTLS connections
  - LDAPS (port 636) for direct SSL/TLS connections
- **Block untrusted networks** from reaching LitFoundry's Active Directory endpoints

## LitFoundry Configuration Steps

### Step 1: Prepare the CA Certificate

1. Obtain the CA certificate in PEM format (see prerequisites above)
2. Store it securely on the LitFoundry server, e.g., `/var/lib/litfoundry/ad-ca.pem` (Linux) or `%PROGRAMDATA%\LitFoundry\ad-ca.pem` (Windows)
3. Ensure permissions restrict access: `chmod 400 ad-ca.pem` (Linux only)

### Step 2: Access Admin Authentication Settings

1. Sign in as the `admin` user
2. Navigate to **Admin** → **Authentication**
3. Click **Edit** to open the configuration form

### Step 3: Enter AD Configuration

Fill in the following fields:

| Field | Example | Notes |
|-------|---------|-------|
| **Domain Name** | `example.com` | DNS name of the Active Directory domain |
| **NetBIOS Name** | `EXAMPLE` | Short domain name for `DOMAIN\username` format |
| **Base DN** | `DC=example,DC=com` | LDAP base DN for searches |
| **UPN Suffixes** | `example.com,subdomain.example.com` | Comma-separated UPN suffixes; users sign in as `user@suffix` |
| **Domain Controllers** | `dc1.example.com:636` | Hostnames/IPs and optional ports (default 389 for StartTLS, 636 for LDAPS); comma-separated |
| **TLS Mode** | `ldaps` or `starttls` | `ldaps` = port 636 (direct SSL), `starttls` = port 389 (upgraded to SSL) |
| **CA Certificate** | (file content) | Paste the PEM-format certificate content or specify the file path |
| **Connect Timeout** | `5` seconds | Connection timeout (default 5 seconds) |
| **Read Timeout** | `10` seconds | Read timeout for LDAP queries (default 10 seconds) |
| **Revalidation Interval** | `15` minutes | How often to recheck AD user account state (default 15 minutes) |
| **Grace Period** | `60` minutes | How long to allow AD operations if the domain is unreachable (default 60 minutes) |
| **Service Account Username** | `EXAMPLE\svc_litfoundry` or `svc_litfoundry@example.com` | Domain account for LitFoundry to use for LDAP queries |
| **Service Account Password** | (encrypted) | Password for the service account (write-only, never returned) |

### Step 4: Test the Connection

1. Click **Test Connection**
2. Review the results:
   - ✅ **TLS Connectivity:** Should pass for all domain controllers
   - ✅ **Certificate:** Should pass if the CA certificate is valid
   - ✅ **Service Account:** Should pass if the credentials are correct
   - ✅ **Search:** Should pass if the base DN and search permissions are correct
3. If any test fails:
   - Verify the certificate is correct (see Prerequisites → TLS/SSL Certificate)
   - Verify the service account credentials
   - Verify network connectivity to domain controllers

### Step 5: Enable Active Directory

1. After passing the test, click **Enable AD**
2. The sign-in page will now show a method selector to choose between "LitFoundry account" and "Active Directory"

## Lockout Threshold Guidance

**Important:** The default throttling policy for AD sign-in is **3 failures per identifier per 15 minutes**. This threshold is designed to stay **below** the default Active Directory lockout policy (usually 5 failed attempts within 30 minutes).

If your organization uses a **stricter lockout threshold**, adjust the throttling limit:

- **Example:** If your domain locks out after 3 failed attempts in 15 minutes:
  - Configure LitFoundry throttling to **2 failures per identifier per 15 minutes**
  - This provides a safety margin to prevent denial-of-service attacks

Contact your domain administrator to confirm your organization's lockout policy.

## Disabling or Removing Active Directory

To disable or remove Active Directory:

1. Navigate to **Admin** → **Authentication**
2. Click **Disable AD** to stop accepting AD sign-ins (existing AD sessions will be revoked on their next request)
3. Click **Remove Configuration** to fully delete the AD configuration

**Note:** Disabling AD does not delete AD-bound users or their projects. The administrator can still manage their accounts and projects.

## Troubleshooting

### Certificate Errors

**Symptom:** "Certificate verification failed" in test results

**Solutions:**
1. Ensure the CA certificate is in PEM format (check for `-----BEGIN CERTIFICATE-----` and `-----END CERTIFICATE-----`)
2. Verify the CA certificate matches the issuing CA for the domain controller certificate
3. For self-signed certificates, ensure the exact certificate (not just the CA) is provided
4. Check the certificate expiration date

### Connection Timeouts

**Symptom:** "Connection timed out" for domain controllers

**Solutions:**
1. Verify network connectivity: `ping dc1.example.com`
2. Verify the port is open:
   - LDAPS (636): `openssl s_client -connect dc1.example.com:636`
   - StartTLS (389): `telnet dc1.example.com 389` or `curl -v ldap://dc1.example.com/`
3. Check firewall rules and network policies
4. Increase the **Connect Timeout** setting if the network is slow

### Service Account Authentication Failures

**Symptom:** "Service account authentication failed" in test results

**Solutions:**
1. Verify the service account password is correct
2. Ensure the service account password has not expired
3. Use the correct format:
   - `DOMAIN\username` for NetBIOS names
   - `username@domain.com` for UPN format
4. Confirm the service account has read permissions on the Users container

### Search Failures

**Symptom:** "Search failed" or no results for test users

**Solutions:**
1. Verify the **Base DN** is correct for your domain
2. Ensure the service account has read permissions on the Users container
3. Confirm the **UPN Suffixes** match those configured in Active Directory
4. Check for typos in the domain or controller names

## Migrating from Local to Active Directory

To migrate existing local users to Active Directory:

1. **Keep local users active** until migration is complete
2. **For each user to migrate:**
   1. Navigate to **Admin** → **Users**
   2. Find the user in the list
   3. Click on their row to open details
   4. Look for a "Convert to Active Directory" option (or use the API)
   5. Resolve the user in AD and confirm the conversion
3. **After migration:**
   - The user's old LitFoundry password is removed
   - The user must sign in using their AD credentials
   - The conversion is audited in the admin logs

## Support and Diagnostics

If users report sign-in failures:

1. Check **Admin** → **Logs** for authentication errors
2. Filter logs by the user's username or IP address
3. Look for `DIRECTORY_UNAVAILABLE` errors (domain temporarily unreachable)
4. Look for `AUTH_PROVIDER_DISABLED` errors (AD was disabled)
5. Check the **Authentication** page for the last successful directory connection time

For persistent issues:

- Verify the service account password (it may have expired)
- Re-run the connection test to identify which step is failing
- Check Active Directory logs on the domain controllers for authentication failures
