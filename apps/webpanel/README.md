# UnrealIRCd WebPanel

This directory contains the UnrealIRCd WebPanel - a web-based administration interface for managing your IRC network.

## Files

- **`Containerfile`** - Container build configuration for the webpanel
- **`config.php`** - PHP configuration file for the webpanel (template)

## What is the WebPanel?

The UnrealIRCd WebPanel provides a user-friendly web interface to:

- Monitor your IRC network in real-time
- Manage users, channels, and server settings
- Configure bans, spamfilters, and other administrative tasks
- View network statistics and performance metrics

## Access

Once running, access the webpanel at: **<http://localhost:8080>**

## Configuration

The webpanel automatically configures itself during the first run. You can customize:

- Authentication backend (file-based or SQL)
- RPC connection settings
- Security parameters
- Feature toggles

## Dependencies

- **UnrealIRCd**: Must be running with JSON-RPC enabled (port 8600)
- **PHP 8.2+**: With required extensions (zip, curl, mbstring, etc.)
- **Nginx**: Web server for hosting the interface

## Security

- **IP Restrictions**: By default, only accessible from localhost (127.*)
- **Authentication**: File-based or SQL backend authentication
- **RPC Access**: Secure JSON-RPC communication with UnrealIRCd

## Troubleshooting

If the webpanel fails to start:

1. Check that UnrealIRCd is running and healthy
2. Verify port 8600 is accessible for JSON-RPC
3. Check container logs: `docker compose logs unrealircd-webpanel`
4. Ensure proper volume permissions

## More Information

- [Official Documentation](https://www.unrealircd.org/docs/UnrealIRCd_webpanel)
- [GitHub Repository](https://github.com/unrealircd/unrealircd-webpanel)
- [JSON-RPC API](https://www.unrealircd.org/docs/JSON-RPC)
