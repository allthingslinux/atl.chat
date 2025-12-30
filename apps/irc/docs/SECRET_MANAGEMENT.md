# Secret Management

This guide covers the management of passwords and sensitive configuration for IRC.atl.chat.

## Overview

All secrets are managed through the `.env` file and external credential files. Never commit secrets to version control.

## Environment Variables (.env)

### Critical Secrets

#### IRC Operator Password
```bash
# Generate secure password hash
docker compose exec unrealircd /home/unrealircd/unrealircd/bin/unrealircd mkpasswd

# Add to .env
IRC_OPER_PASSWORD='$argon2id$v=19$m=6144,t=2,p=2$...'
```

#### Atheme Service Passwords
```bash
# Generate secure random passwords
openssl rand -base64 32

# Configure in .env
ATHEME_SEND_PASSWORD=your_secure_password_here
ATHEME_RECEIVE_PASSWORD=your_secure_password_here
```

#### WebPanel RPC Password
```bash
# Add to .env
WEBPANEL_RPC_PASSWORD=your_secure_password_here
```

## External Credentials

### Cloudflare API Token
```bash
# Copy template
cp cloudflare-credentials.ini.template cloudflare-credentials.ini

# Edit with your token
vim cloudflare-credentials.ini
# dns_cloudflare_api_token = your-actual-api-token-here

# Secure permissions
chmod 600 cloudflare-credentials.ini
```

## Security Best Practices

### File Permissions
```bash
# Secure .env file
chmod 600 .env

# Secure credential files
chmod 600 cloudflare-credentials.ini
```

### Password Generation
```bash
# Generate secure passwords
openssl rand -base64 32

# Generate password hash for IRC operators
docker compose exec unrealircd /home/unrealircd/unrealircd/bin/unrealircd mkpasswd
```

### Regular Rotation
- Rotate passwords every 6-12 months
- Update API tokens when possible
- Monitor for security updates

## Validation

### Check Configuration
```bash
# Validate environment setup
make test-env

# Check SSL settings
make ssl-status
```

### Verify Secrets
```bash
# Check .env file exists and is secure
ls -la .env

# Verify credential files
ls -la cloudflare-credentials.ini
```

## Troubleshooting

### Permission Issues
```bash
# Fix file permissions
chmod 600 .env cloudflare-credentials.ini

# Check ownership
ls -la .env
```

### Missing Secrets
```bash
# Check required variables
grep -E "(PASSWORD|TOKEN)" .env

# Verify Cloudflare credentials
cat cloudflare-credentials.ini
```

## Related Documentation

- [CONFIG.md](CONFIG.md) - Configuration management
- [SSL.md](SSL.md) - SSL certificate management
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common issues and solutions