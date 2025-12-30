-- Log common stats to statsd
--
-- Copyright (C) 2014 Daurnimator
--
-- This module is MIT/X11 licensed.

local socket = require "socket"
local iterators = require "util.iterators"
local jid = require "util.jid"
local bare_sessions = prosody.bare_sessions;

local options = module:get_option("statsd") or {}

-- Create UDP socket to statsd server
local sock = socket.udp()
sock:setpeername(options.hostname or "127.0.0.1", options.port or 8125)

-- Metrics are namespaced by ".", and separated by newline
function clean(s) return (s:gsub("[%.:\n]", "_")) end

-- A 'safer' send function to expose
function send(s) return sock:send(s) end

-- prefix should end in "."
local prefix = (options.prefix or "prosody") .. "."
if not options.no_host then
	prefix = prefix .. clean(module.host) .. "."
end

-- Track users as they bind/unbind
-- count bare sessions every time, as we have no way to tell if it's a new bare session or not
module:hook("resource-bind", function(event)
	send(prefix.."bare_sessions:"..iterators.count(pairs(bare_sessions)).."|g")
	send(prefix.."full_sessions:+1|g")
end, 1)
module:hook("resource-unbind", function(event)
	send(prefix.."bare_sessions:"..iterators.count(pairs(bare_sessions)).."|g")
	send(prefix.."full_sessions:-1|g")
end, 1)

-- Track MUC occupants as they join/leave
module:hook("muc-occupant-joined", function(event)
	send(prefix.."n_occupants:+1|g")
	local room_node = jid.split(event.room.jid)
	send(prefix..clean(room_node)..".occupants:+1|g")
end)
module:hook("muc-occupant-left", function(event)
	send(prefix.."n_occupants:-1|g")
	local room_node = jid.split(event.room.jid)
	send(prefix..clean(room_node)..".occupants:-1|g")
end)

-- Misc other MUC
module:hook("muc-broadcast-message", function(event)
	send(prefix.."broadcast-message:1|c")
	local room_node = jid.split(event.room.jid)
	send(prefix..clean(room_node)..".broadcast-message:1|c")
end)
module:hook("muc-invite", function(event)
	-- Total count
	send(prefix.."invite:1|c")
	local room_node = jid.split(event.room.jid)
	-- Counts per room
	send(prefix..clean(room_node)..".invite:1|c")
	-- Counts per recipient
	send(prefix..clean(event.stanza.attr.to)..".invited:1|c")
end)
module:hook("muc-decline", function(event)
	-- Total count
	send(prefix.."decline:1|c")
	local room_node = jid.split(event.room.jid)
	-- Counts per room
	send(prefix..clean(room_node)..".decline:1|c")
	-- Counts per sender
	send(prefix..clean(event.incoming.attr.from)..".declined:1|c")
end)
