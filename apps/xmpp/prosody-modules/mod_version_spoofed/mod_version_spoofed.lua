-- Prosody IM
-- Copyright (C) 2025-2025 Nicholas George
-- Original mod_version copyright
-- Copyright (C) 2008-2010 Matthew Wild
-- Copyright (C) 2008-2010 Waqas Hussain
--
-- This project is MIT/X11 licensed. Please see the
-- COPYING file in the source package for more information.
--
-- This is a fork of mod_version that implements the ability to spoof server information.
-- This should replace mod_version in the modules_enabled list. Do not load both as they
-- will conflict.

local st = require "util.stanza";

module:add_feature("jabber:iq:version");

local query = st.stanza("query", {xmlns = "jabber:iq:version"})
	:text_tag("name", module:get_option_string("server_name", "Prosody"))
	:text_tag("version", module:get_option_string("server_version", prosody.version));

if not module:get_option_boolean("hide_os_type") then
	local platform;
	local spoofed_platform = module:get_option_string("server_platform", nil);
	if not spoofed_platform then
		if os.getenv("WINDIR") then
			platform = "Windows";
		else
			local os_version_command = module:get_option_string("os_version_command");
			local ok, pposix = pcall(require, "prosody.util.pposix");
			if not os_version_command and (ok and pposix and pposix.uname) then
				local uname, err = pposix.uname();
				if not uname then
					module:log("debug", "Could not retrieve OS name: %s", err);
				else
					platform = uname.sysname;
				end
			end
			if not platform then
				local uname = io.popen(os_version_command or "uname");
				if uname then
					platform = uname:read("*a");
				end
				uname:close();
			end
		end
		if platform then
			platform = platform:match("^%s*(.-)%s*$") or platform;
			query:text_tag("os", platform);
		end
	else
		query:text_tag("os", spoofed_platform);
	end
end

module:hook("iq-get/host/jabber:iq:version:query", function(event)
	local origin, stanza = event.origin, event.stanza;
	origin.send(st.reply(stanza):add_child(query));
	return true;
end);