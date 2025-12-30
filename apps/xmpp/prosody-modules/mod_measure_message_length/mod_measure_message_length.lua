local bytes = module:measure("bytes", "sizes");
local lines = module:measure("lines", "distribution");
local words = module:measure("words", "distribution");

local function measure_length(event)
	local body = event.stanza:get_child_text("body");
	if body then
		bytes(#body);
		lines(select(2, body:gsub("[^\n]+","")));
		words(select(2, body:gsub("%S+","")));
	end
end

module:hook("message/full", measure_length);
module:hook("message/bare", measure_length);
module:hook("message/host", measure_length);

module:hook("pre-message/full", measure_length);
module:hook("pre-message/bare", measure_length);
module:hook("pre-message/host", measure_length);

