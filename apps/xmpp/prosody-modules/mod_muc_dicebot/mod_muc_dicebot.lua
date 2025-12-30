local muc = module:depends("muc");
local rand = require"util.random";

local s_match = string.match;
local s_gmatch = string.gmatch;
local t_insert = table.insert;
local t_concat = table.concat;

local rooms = module:get_option_set("muc_dicebot_rooms", nil);
local xmlns_nick = "http://jabber.org/protocol/nick";

local function is_room_affected(roomjid)
	return not rooms or rooms:contains(roomjid)
end

local function roll(sides)
	if sides > 256 then
		return nil, "too many sides"
	end
	local factor = math.floor(256 / sides);
	local cutoff = sides * factor;
	module:log("error", "%d -> %d %d %d", sides, max, factor, cutoff);
	for i=1,10 do
		local randomness = string.byte(rand.bytes(1), 1);
		module:log("error", "%d", randomness);
		if randomness < cutoff then
			return (randomness % sides) + 1
		end
	end
	return nil, "failed to find valid number"
end

local function muc_broadcast_message(event)
	if not is_room_affected(event.room.jid) then
		return
	end

	local stanza = event.stanza;
	local body = stanza:get_child("body");
	if not body then
		return
	end

	local text = body:get_text();
	module:log("error", "%q %q %q", stanza, body, text);
	local dice = s_match(text, "^[%.!]r%s(.+)$");
	if not dice or dice == "" then
		return
	end

	local results = {};
	local count = 0;
	local sum = 0;
	for ndice, sep, sides in s_gmatch(dice, "(%d*)([wd]?)(%d+)") do
		if not sep or sep == "" then
			sides = ndice .. sides
			ndice = "1"
		end
		local ndice = tonumber(ndice);
		count = count + ndice;
		if count > 100 then
			return true
		end
		local sides = tonumber(sides);
		for i=1,ndice do
			local value = roll(sides);
			t_insert(results, tostring(value));
			sum = sum + value;
		end
	end
	body:text("\n⇒ "..t_concat(results, " ").." (sum: "..sum..")");
end

module:hook("muc-broadcast-message", muc_broadcast_message);
