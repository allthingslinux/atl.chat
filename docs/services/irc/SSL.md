# SSL/TLS Certificate Management

This guide covers the automated SSL certificate management system for IRC.atl.chat, which uses Let's Encrypt with Cloudflare DNS-01 challenge for secure certificate provisioning and renewal.

## Overview

IRC.atl.chat enforces **TLS-only connections** for security. All IRC clients must connect via SSL/TLS on port 6697. Plaintext connections on port 6667 are disabled.

### Architecture

- **Certificate Authority**: Let's Encrypt (free, automated certificates)
- **Challenge Method**: DNS-01 via Cloudflare API
- **Automation**: Custom SSL manager script with Docker integration
- **Storage**: Certificates stored in `data/letsencrypt/` and copied to UnrealIRCd
- **Renewal**: Automatic renewal with service restart

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
# Required for SSL
IRC_ROOT_DOMAIN=yourdomain.com
LETSENCRYPT_EMAIL=admin@yourdomain.com
```

## SSL Setup Process

### Step 1: Configure Cloudflare Credentials

```bash
# Copy the template
cp cloudflare-credentials.ini.template cloudflare-credentials.ini

# Edit with your API token
vim cloudflare-credentials.ini
# Add: dns_cloudflare_api_token = your-actual-token-here

# Secure the file
chmod 600 cloudflare-credentials.ini
```

### Step 2: Initial SSL Certificate Issuance

```bash
# Issue initial certificates
make ssl-setup

# This runs the SSL manager script which:
# 1. Validates configuration
# 2. Issues certificates via Let's Encrypt
# 3. Copies certificates to UnrealIRCd
# 4. Restarts services
```

**Important**: SSL setup must complete before starting services. UnrealIRCd configuration expects certificates to exist.

### Step 3: Start Services

```bash
# Start all services (SSL certificates must exist first)
make up
```

## Certificate Management

### Checking Certificate Status

```bash
# Quick status check
make ssl-status

# Detailed certificate information
./scripts/ssl-manager.sh check --verbose
```

### Manual Certificate Operations

```bash
# Check certificates
./scripts/ssl-manager.sh check

# Issue new certificates (force renewal)
./scripts/ssl-manager.sh issue

# Renew if needed (checks expiry first)
./scripts/ssl-manager.sh renew

# Copy certificates to UnrealIRCd
./scripts/ssl-manager.sh copy

# Restart services after certificate update
./scripts/ssl-manager.sh restart
```

### Certificate Locations

```
data/letsencrypt/
├── live/yourdomain.com/
│   ├── fullchain.pem    # Certificate chain
│   ├── privkey.pem      # Private key
│   └── cert.pem         # Certificate only

src/backend/unrealircd/conf/tls/
├── server.cert.pem     # Certificate for UnrealIRCd
├── server.key.pem      # Private key for UnrealIRCd
└── curl-ca-bundle.crt  # CA bundle for SSL validation
```

## Automation and Monitoring

### Automatic Renewal

Certificates are automatically renewed when:
- Expiry is within 30 days (warning threshold)
- Expiry is within 7 days (critical threshold)

The renewal process:
1. Checks certificate expiry
2. Renews via Let's Encrypt if needed
3. Copies new certificates to UnrealIRCd
4. Restarts affected services

### Monitoring Commands

```bash
# Check SSL status
make ssl-status

# View SSL logs
make ssl-logs

# Check overall service health
make status
```

## Troubleshooting

### Common Issues

#### "Cloudflare credentials not found"
```bash
# Check if credentials file exists
ls -la cloudflare-credentials.ini

# Verify file permissions (should be 600)
chmod 600 cloudflare-credentials.ini

# Check file format
cat cloudflare-credentials.ini
# Should contain: dns_cloudflare_api_token = your-token
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
# Check current certificate details
./scripts/ssl-manager.sh check --verbose

# Force renewal if needed
./scripts/ssl-manager.sh issue
```

#### "Services won't start after certificate update"
```bash
# Check certificate file permissions
ls -la src/backend/unrealircd/conf/tls/

# Manually restart services
docker restart unrealircd atl-irc-webpanel

# Check service logs
make logs
```

### Debug Mode

Enable detailed logging for troubleshooting:

```bash
# Debug SSL operations
./scripts/ssl-manager.sh --debug check
./scripts/ssl-manager.sh --debug issue

# Verbose output
./scripts/ssl-manager.sh --verbose renew
```

### Certificate Validation

```bash
# Verify certificate chain
openssl verify -CAfile src/backend/unrealircd/conf/tls/curl-ca-bundle.crt \
               src/backend/unrealircd/conf/tls/server.cert.pem

# Check certificate details
openssl x509 -in src/backend/unrealircd/conf/tls/server.cert.pem -text -noout

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

The SSL manager uses these default paths (configurable in the script):

```bash
TLS_DIR="./src/backend/unrealircd/conf/tls"
LETSENCRYPT_DIR="./data/letsencrypt"
CREDENTIALS_FILE="./cloudflare-credentials.ini"
```

### Multiple Domains

The current setup issues certificates for:
- `yourdomain.com`
- `*.yourdomain.com`

For additional domains, modify the certbot command in `ssl-manager.sh`.

### Rate Limiting

Let's Encrypt has rate limits:
- **Certificates per domain**: 5 per week
- **Failed validations**: 5 per hour
- **Duplicate certificates**: 1 per week

## Maintenance

### Regular Tasks

```bash
# Weekly: Check certificate status
make ssl-status

# Monthly: Verify automation works
./scripts/ssl-manager.sh renew --verbose

# Quarterly: Review SSL configuration
# Check UnrealIRCd TLS settings
# Verify Cloudflare DNS settings
```

### Emergency Procedures

If certificates expire unexpectedly:

1. **Immediate action**: Check why renewal failed
   ```bash
   make ssl-logs
   ./scripts/ssl-manager.sh check --debug
   ```

2. **Manual renewal**: Force certificate issuance
   ```bash
   ./scripts/ssl-manager.sh issue --verbose
   ```

3. **Service restart**: Ensure services use new certificates
   ```bash
   make restart
   ```

### Backup and Recovery

Certificates are automatically backed up in `data/letsencrypt/`. To restore:

```bash
# Copy from Let's Encrypt backup
./scripts/ssl-manager.sh copy

# Restart services
./scripts/ssl-manager.sh restart
```

## Related Documentation

- [README.md](../README.md) - Quick start guide
- [SECRET_MANAGEMENT.md](SECRET_MANAGEMENT.md) - API token and password management
- [USERMODES.md](USERMODES.md) - IRC user mode reference
- [UnrealIRCd Documentation](https://www.unrealircd.org/docs/) - Server configuration
- [Let's Encrypt Documentation](https://letsencrypt.org/docs/) - Certificate authority
- [Cloudflare API Documentation](https://developers.cloudflare.com/api/) - DNS management