# LitFoundry Deployment Guide

This guide covers deploying LitFoundry in server mode behind an HTTPS reverse proxy for LAN access.

## Quick Start

1. **Install LitFoundry:** Use the installer for your OS
2. **Initialize data root:** `litfoundry init`
3. **Install and configure Caddy:** Use the provided `Caddyfile.example`
4. **Start the server:** `litfoundry serve --mode server`
5. **Distribute CA trust:** See "CA Trust" section below

## Architecture

LitFoundry runs in server mode behind a reverse proxy:

```
Browser (HTTPS)
    ↓
Caddy (TLS termination, reverse proxy)
    ↓
LitFoundry (HTTP, loopback only)
    ↓
SQLite database
```

- **LitFoundry** listens only on `127.0.0.1:5080` (plaintext HTTP)
- **Caddy** receives HTTPS requests from LAN clients and proxies to LitFoundry
- **All network communication** between clients and Caddy is encrypted with TLS

## Installation

### 1. Install LitFoundry

Download the installer for your operating system from the LitFoundry releases page and run it.

### 2. Initialize the Data Root

```bash
litfoundry init
```

This creates the data directory with proper permissions and database schema.

**Data root locations:**
- **Windows:** `C:\ProgramData\LitFoundry` (or set `LITFOUNDRY_DATA_ROOT`)
- **macOS:** `~/Library/Application Support/LitFoundry`
- **Linux:** `/var/lib/litfoundry` (or set `LITFOUNDRY_DATA_ROOT`)

### 3. Install Caddy

Install Caddy for your operating system: https://caddyserver.com/download

### 4. Configure Caddy

Copy `packaging/caddy/Caddyfile.example` to a configuration location:

**Windows:**
```powershell
Copy-Item Caddyfile.example C:\ProgramData\Caddy\Caddyfile
```

**Linux/macOS:**
```bash
sudo cp Caddyfile.example /etc/caddy/Caddyfile
```

Edit the Caddyfile:
- Replace `litfoundry.example.internal` with your actual hostname
- Configure the TLS directive (see "TLS Certificate" section)
- Update any firewall rules (see "Firewall" section)

## Running the Server

### LitFoundry

Start the LitFoundry server in server mode:

```bash
litfoundry serve --mode server --data-root /path/to/data/root
```

The server listens on `127.0.0.1:5080` by default. This is intentional—only Caddy (on the same host) can connect.

**Environment variables:**
- `LITFOUNDRY_DATA_ROOT` – Path to data directory
- `LITFOUNDRY_RUN_MODE` – `server` or `workstation` (default: `server`)
- `LITFOUNDRY_PORT` – Listener port (default: `5080`)
- `LITFOUNDRY_ALLOWED_HOSTS` – Comma-separated allowed Host headers (default: `localhost,127.0.0.1`)
- `LITFOUNDRY_TRUSTED_PROXIES` – Comma-separated trusted proxy IPs (informational)
- `LITFOUNDRY_CORS_ORIGINS` – Comma-separated allowed CORS origins (leave empty for same-origin default)

### Caddy

Start Caddy with the configuration:

**Windows:**
```powershell
caddy start --config C:\ProgramData\Caddy\Caddyfile
```

**Linux/macOS:**
```bash
sudo caddy start --config /etc/caddy/Caddyfile
```

Or use your system's service manager:

**systemd (Linux):**
```bash
sudo systemctl start caddy
sudo systemctl enable caddy
```

**launchd (macOS):**
```bash
brew services start caddy
```

**Windows Service:**
Use the Caddy Windows service installer or start manually.

## TLS Certificate

### Option 1: Self-Signed Certificate (Development/Testing)

Generate a self-signed certificate:

```bash
# Linux/macOS
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes

# Windows (with OpenSSL installed)
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes
```

Update the Caddyfile:
```caddyfile
tls /path/to/cert.pem /path/to/key.pem
```

### Option 2: Caddy Internal CA (Automatic)

Caddy can generate self-signed certificates automatically:

```caddyfile
litfoundry.example.internal {
    tls internal
    # ... rest of config
}
```

This creates certificates in Caddy's data directory.

### Option 3: Organization CA Certificate

If your organization has an internal CA, use its certificate:

1. Get the certificate and key from your IT department
2. Update the Caddyfile:
   ```caddyfile
   tls /path/to/org/cert.pem /path/to/org/key.pem
   ```

## CA Trust Distribution

Since LitFoundry uses HTTPS, clients must trust the CA certificate. Self-signed certificates require manual trust installation.

### Windows

1. Obtain the certificate file (`cert.pem`)
2. Right-click → "Install Certificate"
3. Choose "Local Machine" or "Current User"
4. Select "Trusted Root Certification Authorities"
5. Click "Next" and "Finish"

Or use PowerShell:
```powershell
Import-Certificate -FilePath cert.pem -CertStoreLocation Cert:\LocalMachine\Root
```

### macOS

1. Double-click the certificate file
2. Keychain Access opens
3. Right-click the certificate → "Get Info"
4. Expand "Trust" section
5. Set "When using this certificate" to "Always Trust"

Or use Terminal:
```bash
sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain cert.pem
```

### Linux

**RHEL/CentOS/Fedora:**
```bash
sudo cp cert.pem /etc/pki/ca-trust/source/anchors/
sudo update-ca-trust
```

**Debian/Ubuntu:**
```bash
sudo cp cert.pem /usr/local/share/ca-certificates/
sudo update-ca-certificates
```

**Arch:**
```bash
sudo cp cert.pem /etc/ca-certificates/trust-source/anchors/
sudo trust extract-compat
```

### Browser Trust (If OS Trust Fails)

**Firefox:**
1. Preferences → Privacy & Security → Certificates
2. Click "View Certificates"
3. Authorities tab → Import (`cert.pem`)
4. Check "Trust this CA to identify websites"

**Chrome:**
Uses the OS certificate store (Windows/macOS/Linux).

## Firewall Configuration

LitFoundry listens only on loopback (127.0.0.1), so firewall rules should allow:

1. **Inbound:** HTTPS (port 443) to Caddy from trusted subnets
2. **Internal:** Communication between Caddy and LitFoundry (already loopback-only)

### Windows Firewall

```powershell
# Allow Caddy (HTTPS)
New-NetFirewallRule -DisplayName "Caddy HTTPS" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 443 -RemoteAddress 10.0.0.0/8

# Block LitFoundry loopback listener (not needed—loopback traffic is internal)
```

### Linux (iptables/firewalld)

**Using firewalld:**
```bash
sudo firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="10.0.0.0/8" port protocol="tcp" port="443" accept'
sudo firewall-cmd --reload
```

**Using iptables:**
```bash
sudo iptables -A INPUT -i eth0 -s 10.0.0.0/8 -p tcp --dport 443 -j ACCEPT
sudo iptables -A INPUT -i eth0 -p tcp --dport 443 -j REJECT
```

### macOS

Use the built-in firewall or a third-party tool (e.g., Little Snitch).

## Monitoring and Logging

### LitFoundry Logs

View logs:
```bash
litfoundry status --data-root /path/to/data/root
```

Logs are stored in the data root directory.

### Caddy Logs

The Caddyfile example includes JSON logging to a file. View logs:

**Linux/macOS:**
```bash
tail -f /var/log/caddy/litfoundry.log
```

**Windows:**
```powershell
Get-Content C:\ProgramData\Caddy\logs\litfoundry.log -Tail 20 -Wait
```

## Troubleshooting

### Browser Cannot Connect

1. **Check hostname:** Verify `litfoundry.example.internal` is correct
2. **Check TLS:** Ensure the certificate is valid and CA is trusted
3. **Check Caddy:** Verify Caddy is running: `caddy list`
4. **Check LitFoundry:** Verify it's running on 127.0.0.1:5080

### Certificate Trust Issues

1. **Re-import certificate:** Remove old certificate from trust store and re-import
2. **Browser cache:** Clear browser cache and restart browser
3. **System trust:** Verify the OS trusts the certificate (not just browser)

### Performance Issues

1. **Increase Caddy timeout:** Edit `Caddyfile`, increase `timeout` value
2. **Increase LitFoundry workers:** Set `LITFOUNDRY_WORKERS` environment variable
3. **Check logs:** View Caddy and LitFoundry logs for errors

### Port Already in Use

If port 443 (HTTPS) is already in use, choose an alternate port:

```caddyfile
litfoundry.example.internal:8443 {
    tls /path/to/cert.pem /path/to/key.pem
    reverse_proxy 127.0.0.1:5080
}
```

Then access `https://litfoundry.example.internal:8443`.

## Security Considerations

1. **Network isolation:** LitFoundry listens only on loopback; restrict Caddy firewall rules
2. **TLS only:** Always use HTTPS; Caddy handles the redirect
3. **CA trust:** Distribute organizational CA to all clients to avoid trust warnings
4. **Credential handling:** Use strong authentication; see `litfoundry` documentation for auth setup
5. **Audit logging:** Enable LitFoundry audit logs for compliance tracking

## Backing Up

Back up the data root directory regularly:

```bash
# Linux/macOS
tar -czf litfoundry_backup_$(date +%Y%m%d).tar.gz /var/lib/litfoundry/

# Windows
Compress-Archive -Path "C:\ProgramData\LitFoundry" -DestinationPath "litfoundry_backup_$(Get-Date -Format 'yyyyMMdd').zip"
```

## Further Reading

- [LitFoundry README](../README.md)
- [Caddy Documentation](https://caddyserver.com/docs)
- [RFC 5280: X.509 Certificates](https://tools.ietf.org/html/rfc5280)
