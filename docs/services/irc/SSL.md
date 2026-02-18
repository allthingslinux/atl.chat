# SSL/TLS Certificate Management

This guide covers the automated SSL certificate management system for IRC.atl.chat, which uses Let's Encrypt with Cloudflare DNS-01 challenge for secure certificate provisioning and renewal.

## Overview

IRC.atl.chat enforces **TLS-only connections** for security. All IRC clients must connect via SSL/TLS on port 6697. Plaintext connections on port 6667 are disabled.

### Architecture

- **Certificate Authority**: Let's Encrypt (free, automated certificates)
- **Challenge Method**: DNS-01 via Cloudflare API
- **Automation**: cert-manager (Lego) in `infra/compose/cert-manager.yaml`
- **Storage**: Certificates in `data/certs/certificates/` (Lego layout: `_.<domain>.crt`, `_.<domain>.key`)
- **Renewal**: Automatic renewal every 24h by cert-manager container

## Prerequisites

### 1. Domain and DNS Setup

- Domain must be managed by Cloudflare
- DNS records must exist for your domain and `*.yourdomain.com`
- DNS must be propagated (verify with `dig yourdomain.com`)

### 2. Cloudflare API Token

1. Log into [Cloudflare Dashboard](https://dash.cloudflare.com/)
2. Go to **My Profile** → **API Tokens**
3. Create a new token with these permissions:
   - **Zone:DNS:Edit** permission for your domain
4. Copy the token (keep it secure!)

### 3. Environment Configuration

Ensure your `.env` file has the required SSL variables:

```bash
# Required for cert-manager (Lego)
CLOUDFLARE_DNS_API_TOKEN=your-cloudflare-api-token
LETSENCRYPT_EMAIL=admin@yourdomain.com

# Optional: domain (default: atl.chat)
IRC_ROOT_DOMAIN=yourdomain.com
```

## SSL Setup Process

### Step 1: Configure Cloudflare Credentials

Add `CLOUDFLARE_DNS_API_TOKEN` to your `.env` file. See `docs/examples/cloudflare-credentials.ini.example` for format reference.

### Step 2: Start cert-manager

```bash
# Start cert-manager (Lego) - issues certs to data/certs/certificates/
just irc ssl-setup

# Or directly:
docker compose up -d cert-manager
```

**Important**: cert-manager must run before IRC/XMPP services to populate `data/certs/`. For dev, `just init` creates self-signed certs in `data/certs/live/<domain>/` (Let's Encrypt layout, shared by IRC and XMPP).

### Step 3: Start Services

```bash
# Start all services (cert-manager populates data/certs/ for prod)
just dev
# or: docker compose up -d
```

## Certificate Management

### Checking Certificate Status

```bash
# Quick status check
just irc ssl-status

# View cert-manager logs
just irc ssl-logs
```

### cert-manager Operations

```bash
# Start cert-manager
just irc ssl-setup

# Restart to trigger renewal check
just irc ssl-renew

# Stop cert-manager
just irc ssl-stop
```

### Certificate Locations

**Certificate layout:**
```
data/certs/
├── certificates/       # cert-manager (Lego) output
│   ├── _.atl.chat.crt
│   └── _.atl.chat.key
├── live/               # Let's Encrypt layout (dev certs from init, or certbot/copied prod certs)
│   ├── irc.atl.chat/
│   │   ├── fullchain.pem
│   │   └── privkey.pem
│   └── xmpp.atl.chat/
│       ├── fullchain.pem
│       └── privkey.pem
└── accounts/           # ACME account data (cert-manager)

apps/unrealircd/config/tls/
└── curl-ca-bundle.crt  # CA bundle for TLS peer validation (server certs live in data/certs)
```

See [Data Directory Structure](../../infra/data-structure.md) for the full canonical layout.

## Automation and Monitoring

### Automatic Renewal

cert-manager (Lego) runs a renewal loop every 24 hours. Certificates are renewed automatically when nearing expiry.

### Monitoring Commands

```bash
# Check SSL status
just irc ssl-status

# View cert-manager logs
just irc ssl-logs

# Check overall service health
just status
```

## Troubleshooting

### Common Issues

#### "CLOUDFLARE_DNS_API_TOKEN not set"
```bash
# Add to .env file
echo "CLOUDFLARE_DNS_API_TOKEN=your-token" >> .env

# Restart cert-manager
just irc ssl-stop
just irc ssl-setup
```

#### "DNS challenge failed"
```bash
# Verify DNS records exist
dig TXT _acme-challenge.yourdomain.com
dig TXT _acme-challenge.*.yourdomain.com

# Check Cloudflare DNS settings
# Ensure records exist and are not proxied (orange cloud off)

# Wait for DNS propagation (can take 24+ hours)
```

#### "Certificate expiry warnings"
```bash
# Restart cert-manager to trigger renewal check
just irc ssl-renew

# Check cert validity
openssl x509 -in data/certs/certificates/_.atl.chat.crt -noout -dates
```

#### "Services won't start after certificate update"
```bash
# Check certificate file permissions
ls -la data/certs/live/

# Manually restart services
docker restart unrealircd atl-irc-webpanel

# Check service logs
make logs
```

### Debug Mode

View cert-manager logs for troubleshooting:

```bash
# Follow cert-manager logs
just irc ssl-logs

# Or directly
docker compose logs -f cert-manager
```

### Certificate Validation

```bash
# Verify certificate chain (replace irc.atl.chat with your IRC_DOMAIN)
openssl verify -CAfile apps/unrealircd/config/tls/curl-ca-bundle.crt \
               data/certs/live/irc.atl.chat/fullchain.pem

# Check certificate details
openssl x509 -in data/certs/live/irc.atl.chat/fullchain.pem -text -noout

# Test SSL connection
openssl s_client -connect yourdomain.com:6697 -servername yourdomain.com
```

## Security Considerations

### Certificate Security

- **Private keys**: Stored with 644 permissions (readable by UnrealIRCd)
- **File permissions**: Credentials file must be 600 (owner read/write only)
- **API tokens**: Never commit to version control
- **Certificate validation**: Full chain validation with trusted CA bundle

### Network Security

- **TLS-only policy**: Plaintext IRC connections disabled
- **Modern TLS**: Configured for security (see UnrealIRCd config)
- **Perfect Forward Secrecy**: Supported cipher suites
- **HSTS**: HTTP Strict Transport Security headers

### Monitoring and Alerts

- **Certificate expiry**: Monitored automatically
- **Renewal failures**: Logged with error details
- **Service restarts**: Automatic after certificate updates
- **Health checks**: Certificate validity included in service health

## Advanced Configuration

### Custom Certificate Paths

IRC and XMPP both use `data/certs/live/<domain>/` (Let's Encrypt layout). Override in `.env`:

```bash
IRC_SSL_CERT_PATH=/home/unrealircd/unrealircd/certs/live/irc.atl.chat/fullchain.pem
IRC_SSL_KEY_PATH=/home/unrealircd/unrealircd/certs/live/irc.atl.chat/privkey.pem
```

### Multiple Domains

The current setup issues certificates for:
- `yourdomain.com`
- `*.yourdomain.com`

For additional domains, set `IRC_ROOT_DOMAIN` in `.env` and restart cert-manager.

### Rate Limiting

Let's Encrypt has rate limits:
- **Certificates per domain**: 5 per week
- **Failed validations**: 5 per hour
- **Duplicate certificates**: 1 per week

## Maintenance

### Regular Tasks

```bash
# Weekly: Check certificate status
just irc ssl-status

# Monthly: Verify automation works
just irc ssl-renew

# Quarterly: Review SSL configuration
# Check UnrealIRCd TLS settings
# Verify Cloudflare DNS settings
```

### Emergency Procedures

If certificates expire unexpectedly:

1. **Immediate action**: Check why renewal failed
   ```bash
   just irc ssl-logs
   ```

2. **Manual renewal**: Force certificate issuance
   ```bash
   just irc ssl-setup
   ```

3. **Service restart**: Ensure services use new certificates
   ```bash
   make restart
   ```

### Backup and Recovery

Certificates live in `data/certs/`. cert-manager writes to `data/certs/certificates/`; dev certs and Let's Encrypt-style layouts use `data/certs/live/`. To restore:

```bash
# Restart services
docker compose restart atl-irc-server
```

## Related Documentation

- [README.md](../README.md) - Quick start guide
- [SECRET_MANAGEMENT.md](SECRET_MANAGEMENT.md) - API token and password management
- [USERMODES.md](USERMODES.md) - IRC user mode reference
- [UnrealIRCd Documentation](https://www.unrealircd.org/docs/) - Server configuration
- [Let's Encrypt Documentation](https://letsencrypt.org/docs/) - Certificate authority
- [Cloudflare API Documentation](https://developers.cloudflare.com/api/) - DNS management