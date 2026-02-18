# Backup & Recovery

This guide covers essential backup procedures for IRC.atl.chat data and configuration.

## What to Backup

### Critical Data
- **Atheme Database**: User accounts, channel registrations (`data/atheme/data/services.db`)
- **SSL Certificates**: Private keys and certificates (`data/certs/`)
- **Configuration**: Environment variables (`.env`)

### Optional Data
- **Logs**: Service logs (`data/irc/logs/`, `data/atheme/logs/`)
- **Channel Data**: UnrealIRCd runtime data (`data/irc/data/`)

## Backup Procedures

### Manual Backup
```bash
# Create backup directory
mkdir -p backup/$(date +%Y%m%d)

# Backup Atheme database
cp -r data/atheme backup/$(date +%Y%m%d)/

# Backup SSL certificates
cp -r data/certs backup/$(date +%Y%m%d)/

# Backup configuration
cp .env backup/$(date +%Y%m%d)/

# Create archive
tar -czf backup-$(date +%Y%m%d).tar.gz backup/$(date +%Y%m%d)/
```

### Automated Backup Script
```bash
#!/bin/bash
# Simple backup script

BACKUP_DIR="backup/$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"

# Stop services
docker compose down

# Backup data
cp -r data/ "$BACKUP_DIR/"
cp .env "$BACKUP_DIR/"

# Create archive
tar -czf "irc-backup-$(date +%Y%m%d).tar.gz" "$BACKUP_DIR"

# Start services
docker compose up -d

echo "Backup completed: irc-backup-$(date +%Y%m%d).tar.gz"
```

## Recovery Procedures

### Restore from Backup
```bash
# Stop services
docker compose down

# Extract backup
tar -xzf irc-backup-YYYYMMDD.tar.gz

# Restore data
cp -r backup/YYYYMMDD/data/* data/
cp backup/YYYYMMDD/.env .env

# Start services
docker compose up -d
```

### Verify Recovery
```bash
# Check services are running
make status

# Test IRC connection
make test-irc

# Check SSL certificates
make ssl-status
```

## Best Practices

1. **Regular Backups**: Weekly automated backups
2. **Test Restores**: Monthly restore testing
3. **Offsite Storage**: Store backups in different location
4. **Documentation**: Keep backup procedures documented

## Troubleshooting

### Backup Issues
```bash
# Check disk space
df -h

# Check backup integrity
tar -tzf backup-file.tar.gz

# Verify data permissions
ls -la data/
```

### Recovery Issues
```bash
# Check service logs
make logs

# Verify configuration
make test-env

# Check file permissions
ls -la data/ logs/
```

## Related Documentation

- [CONFIG.md](CONFIG.md) - Configuration management
- [SSL.md](SSL.md) - SSL certificate management
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common issues and solutions