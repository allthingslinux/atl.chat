local st = require "util.stanza";
local jid = require "util.jid";
local nodeprep = require "util.encodings".stringprep.nodeprep;

local rooms = module:shared "muc/rooms";
if not rooms then
        module:log("error", "This module only works on MUC components!");
        return;
end

local restrict_patterns = module:get_option("muc_restrict_matching", {});
local restrict_excepts = module:get_option_set("muc_restrict_exceptions", {});
local restrict_allow_admins = module:get_option_boolean("muc_restrict_allow_admins", false);

local function is_restricted(room, who)
	-- If admins can join prohibited rooms, we allow them to
	if restrict_allow_admins and usermanager.is_admin(who, module.host) then
		module:log("debug", "Admins are allowed to enter restricted rooms (%s on %s)", who, room)
		return nil;
	end

	-- Don't evaluate exceptions
	if restrict_excepts:contains(room) then
		module:log("debug", "Room %s is amongst restriction exceptions", room())
		return nil;
	end

	-- Evaluate regexps of restricted patterns
        for pattern,reason in pairs(restrict_patterns) do
                if room:match(pattern) then
			module:log("debug", "Room %s is restricted by pattern %s, user %s is not allowed to join (%s)", room, pattern, who, reason)
                        return reason;
                end
        end

	return nil
end

module:hook("presence/full", function(event)
        local stanza = event.stanza;

        if stanza.name == "presence" and stanza.attr.type == "unavailable" then   -- Leaving events get discarded
                return;
        end

	-- Get the room
	local room = jid.split(stanza.attr.to);
        if not room then return; end

	-- Get who has tried to join it
	local who = jid.bare(stanza.attr.from)

	-- Checking whether room is restricted
	local check_restricted = is_restricted(room, who)
        if check_restricted ~= nil then
                event.allowed = false;
                event.stanza.attr.type = 'error';
	        return event.origin.send(st.error_reply(event.stanza, "cancel", "forbidden", "You're not allowed to enter this room: " .. check_restricted));
        end
end, 10);
