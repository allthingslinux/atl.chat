local jid = require("util.jid")
local mod_muc = module:depends("muc")

local gateway_hosts = module:get_option_array("gateway_hosts", {})

function optimize(remote_host, event)
	local stanza = event.stanza
	module:log("debug", "optimize presence event destined for " .. remote_host)

	local muc_x = stanza:get_child("x", "http://jabber.org/protocol/muc#user")
	if muc_x then
		for status in muc_x:childtags("status") do
			if status.attr.status == "110" then
				module:log("debug", "optimize delivering 110")
				-- Always deliver self-presence
				return
			end
		end
	end

	local bare_jid = jid.bare(stanza.attr.to)
	local room = mod_muc.get_room_from_jid(jid.bare(stanza.attr.from))
	if not room then return end
	for nick, occupant in room:each_occupant() do
		local occupant_host = jid.host(occupant.bare_jid)
		if occupant_host == remote_host then
			-- This is the "first" occupant from the host
			-- which is the only one we will route non-110
			-- presence to
			if occupant.bare_jid == bare_jid then
				module:log("debug", "optimize found first occupant, so route")
				return
			else
				module:log("debug", "optimize found non-first occupant, so drop")
				return true
			end
		end
	end
	-- If we get here we found no occupants for this host
	module:log("debug", "optimize found no occupants for host " .. remote_host)
end

-- Note this will only affect gateways over s2s for now
module:hook("route/remote", function (event)
	if event.stanza.name ~= "presence" then
		return
	end

	local remote_host = jid.host(event.stanza.attr.to)
	for _, gateway_host in pairs(gateway_hosts) do
		if remote_host == gateway_host then
			return optimize(remote_host, event)
		end
	end
end, 1000)
