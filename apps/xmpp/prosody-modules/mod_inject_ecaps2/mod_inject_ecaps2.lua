module:depends("cache_c2s_caps");

local st = require "util.stanza";
local hashes = require "util.hashes";
local base64 = require "util.encodings".base64;
local t_insert, t_sort, t_concat = table.insert, table.sort, table.concat;

local algorithms = module:get_option_set("ecaps2_hashes", { "sha-256", "sha-512" });

-- TODO: Add all of the other hashes supported.
local algorithm_map = {
	["sha-256"] = hashes.sha256;
	["sha-512"] = hashes.sha512;
};

-- TODO: move that to util.caps maybe.
local function calculate_hash(disco_info)
	local identities, features, extensions = {}, {}, {};
	for _, tag in ipairs(disco_info) do
		if tag.name == "identity" then
			t_insert(identities, ((tag.attr.category or "").."\31"..
			                      (tag.attr.type or "").."\31"..
					      (tag.attr["xml:lang"] or "").."\31"..
					      (tag.attr.name or "").."\31\30"));
		elseif tag.name == "feature" then
			t_insert(features, (tag.attr.var or "").."\31");
		elseif tag.name == "x" and tag.attr.xmlns == "jabber:x:data" then
			local form = {};
			for _, field in ipairs(tag.tags) do
				if field.name == "field" and field.attr.xmlns == "jabber:x:data" and field.attr.var then
					local values = {};
					for _, value in ipairs(field.tags) do
						if value.name == "value" and value.attr.xmlns == "jabber:x:data" then
							value = #value.tags == 0 and value:get_text();
							if value then t_insert(values, value.."\31"); end
						end
					end
					t_sort(values);
					if #values > 0 then
						t_insert(form, field.attr.var.."\31"..t_concat(values, "\31").."\31\30");
					else
						t_insert(form, field.attr.var.."\31\30");
					end
				end
			end
			t_sort(form);
			form = t_concat(form, "\29").."\29";
			t_insert(extensions, form);
		else
			return nil, "Unknown element in disco#info";
		end
	end
	t_sort(identities);
	t_sort(features);
	t_sort(extensions);
	if #identities > 0 then identities = t_concat(identities, "\28").."\28"; else identities = "\28"; end
	if #features > 0 then features = t_concat(features).."\28"; else features = "\28"; end
	if #extensions > 0 then extensions = t_concat(extensions, "\28").."\28"; else extensions = "\28"; end
	return features..identities..extensions;
end

local function caps_handler(event)
	local origin = event.origin;

	if origin.presence == nil or origin.presence:get_child("c", "urn:xmpp:caps") then
		return;
	end

	local disco_info = origin.caps_cache;
	if disco_info == nil then
		return;
	end

	local extension_string, err = calculate_hash(disco_info);
	if extension_string == nil then
		module:log("warn", "Failed to calculate ecaps2 hash: %s", err)
		return;
	end

	local ecaps2 = st.stanza("c", { xmlns = "urn:xmpp:caps" });
	for algo in algorithms do
		local func = algorithm_map[algo];
		if func ~= nil then
			local hash = base64.encode(func(extension_string));
			ecaps2:tag("hash", { xmlns = "urn:xmpp:hashes:2"; algo = algo })
			      :text(hash)
			      :up();
		end
	end

	module:log("debug", "Injected ecaps2 element in presence");
	origin.presence:add_child(ecaps2);
end

module:hook("c2s-capabilities-changed", caps_handler);
