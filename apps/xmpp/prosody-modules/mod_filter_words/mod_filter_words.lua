local filters = require "util.filters";

local replacements = module:get_option("filter_words", {});

if not replacements then
	module:log("warn", "No 'filter_words' option set, filters inactive");
	return
end

function filter_stanza(stanza)
	if stanza.name == "message" then
		local body = stanza:get_child("body");
		if body then
			body[1] = body[1]:gsub("%a+", replacements);
		end
	end
	return stanza;
end

function filter_session(session)
	filters.add_filter(session, "stanzas/in", filter_stanza);
end

function module.load()
	if module.reloading then
		module:log("warn", "RELOADING!!!");
	end
	filters.add_filter_hook(filter_session);
end

function module.unload()
	filters.remove_filter_hook(filter_session);	
end
