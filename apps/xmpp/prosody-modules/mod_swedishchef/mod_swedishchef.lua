-- Copyright (C) 2009 Florian Zeitz
-- Copyright (C) 2009 Matthew Wild
--
-- This project is MIT/X11 licensed. Please see the
-- COPYING file in the source package for more information.
--

local trigger_string = module:get_option_string("swedishchef_trigger");
trigger_string = (trigger_string and trigger_string .. " ") or "";

local chef = {
  { th = "t" },

  { ow = "o"},
  {["([^%w])o"] = "%1oo",
  O = "Oo"},

  {au = "oo",
  u = "oo", U = "Oo"},
  {["([^o])o([^o])"] = "%1u%2"},
  {ir = "ur",

  an = "un", An = "Un", Au = "Oo"},

  {e = "i", E = "I"},

  { i = function () return select(math.random(2), "i", "ee"); end },

  {a = "e", A = "E"},

  {["e([^%w])"] = "e-a%1"},
  {f = "ff"},

  {v = "f", V = "F"},
  {w = "v", W = "V"} };

function swedish(english)
	local eng, url = english:match("(.*)(http://.*)$");
	if eng then english = eng; end

	for _,v in ipairs(chef) do
		for k,v in pairs(v) do
			english = english:gsub(k,v);
		end
	end
	english = english:gsub("the", "zee");
	english = english:gsub("The", "Zee");
	english = english:gsub("tion", "shun");
	english = english:gsub("[.!?]$", "%1\nBork Bork Bork!");
	return tostring(english..((url and url) or ""));
end

function check_message(data)
	local origin, stanza = data.origin, data.stanza;

	local body, bodyindex;
	for k,v in ipairs(stanza) do
		if v.name == "body" then
			body, bodyindex = v, k;
		end
	end

	if not body then return; end
	body = body:get_text();

	if body and (body:find(trigger_string, 1, true) == 1) then
		module:log("debug", "Found trigger: %s", body:match(trigger_string, 1, true));
		stanza[bodyindex][1] = swedish(body:gsub("^" .. trigger_string, "", 1));
	end
end

if module:get_option_boolean("swedish_chef_enabled", true) then
	module:hook("message/bare", check_message);
end

module:hook("swedish_chef/message_filter", check_message);
