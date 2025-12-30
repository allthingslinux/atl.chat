local dataforms = require "util.dataforms";

local form_layout = dataforms.new({
	{ type = "hidden"; var = "FORM_TYPE"; value = "urn:xmpp:sos:0" };
	{ type = "list-multi"; name = "addrs"; var = "external-status-addresses" };
});

local addresses = module:get_option_array("outage_status_urls");
module:add_extension(form_layout:form({ addrs = addresses }, "result"));
