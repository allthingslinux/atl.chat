local st = require "util.stanza";

local important_payloads = module:get_option_set("csi_important_payloads", { });

module:hook("csi-is-stanza-important", function (event)
	local stanza = event.stanza;
	if st.is_stanza(stanza) then
		for important in important_payloads do
			if stanza:find(important) then
				return true;
			end
		end
	end
end);
