local array = require "util.array";
local set = require "util.set";
local hashes = require "util.hashes";
local it = require "util.iterators";
local base64_enc = require "util.encodings".base64.encode;

-- *** The following code is copy-pasted from mod_saslauth/mod_sasl2, like requested by Zash ***
-- *** Please update, if you modify mod_saslauth or mod_sasl2! ***
local allow_unencrypted_plain_auth = module:get_option_boolean("allow_unencrypted_plain_auth", false)
local insecure_mechanisms = module:get_option_set("insecure_sasl_mechanisms", allow_unencrypted_plain_auth and {} or {"PLAIN", "LOGIN"});
local disabled_mechanisms = module:get_option_set("disable_sasl_mechanisms", { "DIGEST-MD5" });
-- *** End of copy-pasted code ***

local hash_functions = {
	["SCRAM-SHA-1"] = hashes.sha1;
	["SCRAM-SHA-1-PLUS"] = hashes.sha1;
	["SCRAM-SHA-256"] = hashes.sha256;
	["SCRAM-SHA-256-PLUS"] = hashes.sha256;
	["SCRAM-SHA-512"] = hashes.sha512;
	["SCRAM-SHA-512-PLUS"] = hashes.sha512;
};

function add_ssdp_info(event)
	local sasl_handler = event.session.sasl_handler;
	local hash = hash_functions[sasl_handler.selected];
	if not hash then
		module:log("debug", "Not enabling SSDP for unsupported mechanism: %s", sasl_handler.selected);
		return;
	end

	-- *** The following code is copy-pasted from mod_saslauth/mod_sasl2, like requested by Zash ***
	-- *** Please update, if you modify mod_saslauth or mod_sasl2! ***
	local usable_mechanisms = set.new();
	local available_mechanisms = sasl_handler:mechanisms()
	for mechanism in pairs(available_mechanisms) do
		if disabled_mechanisms:contains(mechanism) then
			module:log("debug", "Not offering disabled mechanism %s", mechanism);
		elseif not event.session.secure and insecure_mechanisms:contains(mechanism) then
			module:log("debug", "Not offering mechanism %s on insecure connection", mechanism);
		else
			module:log("debug", "Offering mechanism %s", mechanism);
			usable_mechanisms:add(mechanism);
		end
	end
	-- *** End of copy-pasted code ***

	local mechanism_list = array.collect(usable_mechanisms):sort();
	local cb = sasl_handler.profile.cb;
	local cb_list = cb and array.collect(it.keys(cb)):sort();
	local ssdp_string;
	if cb_list then
		ssdp_string = mechanism_list:concat("\30").."\31"..cb_list:concat("\30");
	else
		ssdp_string = mechanism_list:concat("\30");
	end
	module:log("debug", "Calculated SSDP string: %s", ssdp_string);
	event.message = event.message..",h="..base64_enc(hash(ssdp_string));
	sasl_handler.state.server_first_message = event.message;
end

module:hook("sasl/c2s/challenge", add_ssdp_info, 1);
module:hook("sasl2/c2s/challenge", add_ssdp_info, 1);

