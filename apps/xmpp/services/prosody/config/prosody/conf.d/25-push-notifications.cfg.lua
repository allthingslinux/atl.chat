-- ===============================================
-- PUSH NOTIFICATIONS CONFIGURATION
-- ===============================================
-- Configuration for mod_cloud_notify and mod_cloud_notify_extensions
-- XEP-0357: Push Notifications for mobile devices
-- https://modules.prosody.im/mod_cloud_notify.html

-- ===============================================
-- CLOUD NOTIFY CORE MODULE (XEP-0357)
-- ===============================================

-- Body text for important messages when real body cannot be sent
-- Used when messages are encrypted or have no body
push_notification_important_body = Lua.os.getenv("PROSODY_PUSH_IMPORTANT_BODY") or "New Message!"

-- Maximum persistent push errors before disabling notifications for a device
-- Default: 16, Production: 16-32 depending on tolerance
push_max_errors = Lua.tonumber(Lua.os.getenv("PROSODY_PUSH_MAX_ERRORS")) or 16

-- Maximum number of devices per user
-- Default: 5, Production: 5-10 depending on user needs
push_max_devices = Lua.tonumber(Lua.os.getenv("PROSODY_PUSH_MAX_DEVICES")) or 5

-- Extend smacks timeout if no push was triggered yet
-- Default: 259200 (72 hours), Production: 259200-604800 (3-7 days)
push_max_hibernation_timeout = Lua.tonumber(Lua.os.getenv("PROSODY_PUSH_MAX_HIBERNATION_TIMEOUT")) or 259200

-- Privacy settings (configured in 21-security.cfg.lua)
-- push_notification_with_body = false      -- Don't send message body to push gateway
-- push_notification_with_sender = false    -- Don't send sender info to push gateway

-- ===============================================
-- CLOUD NOTIFY EXTENSIONS (iOS CLIENT SUPPORT)
-- ===============================================
-- Enhanced push notification features for Siskin, Snikket iOS, and other clients
-- that require additional extensions beyond XEP-0357

-- Enable iOS-specific push notification features
-- This module provides enhanced support for:
-- - Siskin (iOS XMPP client)
-- - Snikket (iOS XMPP client)
-- - Other iOS clients with extended push requirements

-- ===============================================
-- INTEGRATION WITH OTHER MODULES
-- ===============================================

-- This module works with:
-- - mod_smacks: Stream Management for connection resumption
-- - mod_mam: Message Archive Management for offline messages
-- - mod_carbons: Message Carbons for multi-device sync
-- - mod_csi: Client State Indication for mobile optimization

-- ===============================================
-- BUSINESS RULES AND MESSAGE HANDLING
-- ===============================================
-- The module automatically handles:
-- - Offline messages stored by mod_offline
-- - Messages stored by mod_mam (Message Archive Management)
-- - Messages waiting in the smacks queue
-- - Hibernated sessions via mod_smacks
-- - Delayed acknowledgements via mod_smacks

-- ===============================================
-- MONITORING AND DEBUGGING
-- ===============================================
-- To monitor push notification activity:
-- - Check Prosody logs for "cloud_notify" entries
-- - Monitor for push errors and device registration
-- - Use prosodyctl shell to inspect push registrations

-- ===============================================
-- CLIENT COMPATIBILITY
-- ===============================================
-- Supported clients include:
-- - Conversations (Android)
-- - Monal (iOS)
-- - Siskin (iOS) - requires mod_cloud_notify_extensions
-- - Snikket (iOS) - requires mod_cloud_notify_extensions
-- - ChatSecure (iOS)
-- - Xabber (Android)
-- - Blabber (Android)

-- Note: Some iOS clients require mod_cloud_notify_extensions for full functionality
-- as they use extensions not currently defined in XEP-0357
