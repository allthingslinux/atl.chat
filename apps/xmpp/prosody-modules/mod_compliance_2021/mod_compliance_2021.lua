-- Copyright (c) 2021 Kim Alvefur
--
-- This module is MIT licensed.

local hostmanager = require "core.hostmanager";

local array = require "util.array";
local set = require "util.set";

local modules_enabled = module:get_option_inherited_set("modules_enabled");

for host in pairs(hostmanager.get_children(module.host)) do
	local component = module:context(host):get_option_string("component_module");
	if component then
		modules_enabled:add(component);
		modules_enabled:include(module:context(host):get_option_set("modules_enabled", {}));
	end
end

local function check(suggested, alternate, ...)
	if set.intersection(modules_enabled, set.new({suggested; alternate; ...})):empty() then return suggested; end
	return false;
end

local compliance = {
	array {"Core Server"; check("tls"); check("disco")};

	array {"Advanced Server"; check("pep", "pep_simple")};

	array {"Core Web"; check("bosh"); check("websocket")};

	-- No Server requirements for Advanced Web

	array {"Core IM"; check("vcard_legacy", "vcard"); check("carbons"); check("http_file_share", "http_upload")};

	array {
		"Advanced IM";
		check("vcard_legacy", "vcard");
		check("blocklist");
		check("muc");
		check("private");
		check("smacks");
		check("mam");
		check("bookmarks");
	};

	array {"Core Mobile"; check("smacks"); check("csi_simple", "csi_battery_saver")};

	array {"Advanced Mobile"; check("cloud_notify")};

	array {"Core A/V Calling"; check("turn_external", "external_services", "turncredentials", "extdisco")};

};

function check_compliance()
	local compliant = true;
	for _, suite in ipairs(compliance) do
		local section = suite:pop(1);
		if module:get_option_boolean("compliance_" .. section:lower():gsub("%A", "_"), true) then
			local missing = set.new(suite:filter(function(m) return type(m) == "string" end):map(function(m) return "mod_" .. m end));
			if suite[1] then
				if compliant then
					compliant = false;
					module:log("warn", "Missing some modules for XMPP Compliance 2021");
				end
				module:log("info", "%s Compliance: %s", section, missing);
			end
		end
	end

	if compliant then module:log("info", "XMPP Compliance 2021: Compliant ✔️"); end
end

if prosody.start_time then
	check_compliance()
else
	module:hook_global("server-started", check_compliance);
end

