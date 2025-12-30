-- XEP-0215 implementation for time-limited turn credentials
-- Copyright (C) 2012-2013 Philipp Hancke
-- This file is MIT/X11 licensed.

local st = require "util.stanza";
local hmac_sha1 = require "util.hashes".hmac_sha1;
local base64 = require "util.encodings".base64;
local os_time = os.time;
local datetime = require "util.datetime".datetime;
local secret = module:get_option_string("turncredentials_secret");
local host = module:get_option_string("turncredentials_host"); -- use ip addresses here to avoid further dns lookup latency
local port = module:get_option_number("turncredentials_port", 3478);
local ttl = module:get_option_number("turncredentials_ttl", 86400);
if not (secret and host) then
    module:log("error", "turncredentials not configured");
    return;
end

module:add_feature("urn:xmpp:extdisco:1");

module:hook("iq-get/host/urn:xmpp:extdisco:1:services", function(event)
    local origin, stanza = event.origin, event.stanza;
    if origin.type ~= "c2s" then
        return;
    end
    local expires_at = os_time() + ttl;
    local userpart = tostring(expires_at);
    local nonce = base64.encode(hmac_sha1(secret, tostring(userpart), false));
    origin.send(st.reply(stanza):tag("services", {xmlns = "urn:xmpp:extdisco:1"})
        :tag("service", { type = "stun", host = host, port = ("%d"):format(port) }):up()
        :tag("service", { type = "turn", host = host, port = ("%d"):format(port), username = userpart, password = nonce, ttl = ("%d"):format(ttl) }):up()
    );
    return true;
end);

module:add_feature("urn:xmpp:extdisco:2");

module:hook("iq-get/host/urn:xmpp:extdisco:2:services", function(event)
    local origin, stanza = event.origin, event.stanza;
    if origin.type ~= "c2s" then
        return;
    end
    local expires_at = os_time() + ttl;
    local userpart = tostring(expires_at);
    local nonce = base64.encode(hmac_sha1(secret, tostring(userpart), false));
    origin.send(st.reply(stanza):tag("services", {xmlns = "urn:xmpp:extdisco:2"})
        :tag("service", { type = "stun", transport = "udp", host = host, port = ("%d"):format(port) }):up()
        :tag("service", { type = "stun", transport = "tcp", host = host, port = ("%d"):format(port) }):up()
        :tag("service", { type = "turn", transport = "udp", host = host, port = ("%d"):format(port), username = userpart, password = nonce, expires = datetime(expires_at), restricted = "1"  }):up()
        :tag("service", { type = "turn", transport = "tcp", host = host, port = ("%d"):format(port), username = userpart, password = nonce, expires = datetime(expires_at), restricted = "1"  }):up()
    );
    return true;
end);
