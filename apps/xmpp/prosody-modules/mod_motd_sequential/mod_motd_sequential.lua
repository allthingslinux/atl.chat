-- Prosody IM
-- Copyright (C) 2008-2010 Matthew Wild
-- Copyright (C) 2008-2010 Waqas Hussain
-- Copyright (C) 2010 Jeff Mitchell
--
-- This project is MIT/X11 licensed. Please see the
-- COPYING file in the source package for more information.
--

local core_route_stanza = prosody.core_route_stanza;
local host = module:get_host();
local motd_jid = module:get_option("motd_jid") or host;
local datamanager = require "util.datamanager";
local ipairs = ipairs;
local motd_sequential_messages = module:get_option("motd_sequential_messages") or {};
local motd_messagesets = {};
local max = 1;
for i, message in ipairs(motd_sequential_messages) do
    motd_messagesets[i] = message;
    max = i;
end

local st = require "util.stanza";

module:hook("resource-bind",
    function (event)
            local session = event.session;
    local alreadyseen_list = datamanager.load(session.username, session.host, "motd_sequential_seen") or { max = 0 };
    local alreadyseen = alreadyseen_list["max"] + 1;
    local motd_stanza;
    for i = alreadyseen, max do
            motd_stanza =
                    st.message({ to = session.username..'@'..session.host, from = motd_jid },
                            motd_messagesets[i]);
            core_route_stanza(hosts[host], motd_stanza);
            module:log("debug", "MOTD send to user %s@%s", session.username, session.host);
    end
    alreadyseen_list["max"] = max;
    datamanager.store(session.username, session.host, "motd_sequential_seen", alreadyseen_list);
end);
