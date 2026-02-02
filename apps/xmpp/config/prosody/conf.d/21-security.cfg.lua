-- ===============================================
-- SECURITY (limits, registration, firewall)
-- ===============================================

limits = {
	c2s = {
		rate = Lua.os.getenv("PROSODY_C2S_RATE") or "10kb/s",
		burst = Lua.os.getenv("PROSODY_C2S_BURST") or "25kb",
		stanza_size = Lua.tonumber(Lua.os.getenv("PROSODY_C2S_STANZA_SIZE")) or (1024 * 256)
	},
	s2s = {
		rate = Lua.os.getenv("PROSODY_S2S_RATE") or "30kb/s",
		burst = Lua.os.getenv("PROSODY_S2S_BURST") or "100kb",
		stanza_size = Lua.tonumber(Lua.os.getenv("PROSODY_S2S_STANZA_SIZE")) or (1024 * 512)
	},
	http_upload = {
		rate = Lua.os.getenv("PROSODY_HTTP_UPLOAD_RATE") or "2mb/s",
		burst = Lua.os.getenv("PROSODY_HTTP_UPLOAD_BURST") or "10mb"
	},
}

max_connections_per_ip = Lua.tonumber(Lua.os.getenv("PROSODY_MAX_CONNECTIONS_PER_IP")) or 5
registration_throttle_max = Lua.tonumber(Lua.os.getenv("PROSODY_REGISTRATION_THROTTLE_MAX")) or 3
registration_throttle_period = Lua.tonumber(Lua.os.getenv("PROSODY_REGISTRATION_THROTTLE_PERIOD")) or 3600

-- ===============================================
-- TLS/SSL SECURITY
-- ===============================================
-- Global TLS configuration. See:
-- https://prosody.im/doc/certificates
-- https://prosody.im/doc/security
-- ssl = {
-- protocol = "tlsv1_2+",
-- ciphers = "ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS",
-- curve = "secp384r1",
-- options = { "cipher_server_preference", "single_dh_use", "single_ecdh_use" },
-- }

-- Let's Encrypt certificate location (mounted into the container)
certificates = "certs"

-- Require encryption and secure s2s auth
c2s_require_encryption = Lua.os.getenv("PROSODY_C2S_REQUIRE_ENCRYPTION") ~= "false"
s2s_require_encryption = Lua.os.getenv("PROSODY_S2S_REQUIRE_ENCRYPTION") ~= "false"
s2s_secure_auth = Lua.os.getenv("PROSODY_S2S_SECURE_AUTH") ~= "false"
allow_unencrypted_plain_auth = Lua.os.getenv("PROSODY_ALLOW_UNENCRYPTED_PLAIN_AUTH") == "true"

-- Channel binding strengthens SASL against MITM
tls_channel_binding = Lua.os.getenv("PROSODY_TLS_CHANNEL_BINDING") ~= "false"

-- Recommended privacy defaults for push notifications
-- See https://modules.prosody.im/mod_cloud_notify.html
push_notification_with_body = Lua.os.getenv("PROSODY_PUSH_NOTIFICATION_WITH_BODY") == "true"
push_notification_with_sender = Lua.os.getenv("PROSODY_PUSH_NOTIFICATION_WITH_SENDER") == "true"

-- ===============================================
-- AUTHENTICATION & ACCOUNT POLICY
-- ===============================================
-- Hashed password storage and preferred SASL mechanisms
authentication = "internal_hashed"
sasl_mechanisms = {
	"SCRAM-SHA-256",
	"SCRAM-SHA-1",
	"DIGEST-MD5",
}

-- Account lifecycle and registration hygiene
user_account_management = {
	grace_period = Lua.tonumber(Lua.os.getenv("PROSODY_ACCOUNT_GRACE_PERIOD")) or (7 * 24 * 3600),
	deletion_confirmation = Lua.os.getenv("PROSODY_ACCOUNT_DELETION_CONFIRMATION") ~= "false",
}

-- Disallow common/abusive usernames during registration
block_registrations_users = {
	"administrator",
	"admin",
	"root",
	"postmaster",
	"xmpp",
	"jabber",
	"contact",
	"mail",
	"abuse",
	"support",
	"security",
}
block_registrations_require = Lua.os.getenv("PROSODY_BLOCK_REGISTRATIONS_REQUIRE") or "^[a-zA-Z0-9_.-]+$"

-- Inline firewall rules for mod_firewall
-- firewall_rules = [=[
-- %ZONE spam: log=debug
-- RATE: 10 (burst 15) on full-jid
-- TO: spam
-- DROP.

-- %LENGTH > 262144
-- BOUNCE: policy-violation (Stanza too large)
-- ]=]
