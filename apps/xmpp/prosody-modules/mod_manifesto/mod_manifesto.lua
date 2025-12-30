-- mod_manifesto

local timer = require "util.timer";
local jid_split = require "util.jid".split;
local st = require "util.stanza";
local dm = require "util.datamanager";
local dataforms_new = require "util.dataforms".new;
local adhoc_initial = require "util.adhoc".new_initial_data_form;
local mm_reload = require "modulemanager".reload;
local s2s_destroy_session = require "core.s2smanager".destroy_session;
local config = require "core.configmanager";
local config_get = config.get;
local config_set = config.set;
local t_concat = table.concat;
local adhoc_new = module:require "adhoc".new;
local time = os.time;

local hosts = prosody.hosts;
local host = module.host;
local host_session = hosts[host];
local incoming_s2s = prosody.incoming_s2s;
local s2s_sessions = module:shared"/*/s2s/sessions";

local default_tpl = [[
Hello there.

This is a brief system message to let you know about some upcoming changes to the $HOST service.

Some of your contacts are on other Jabber/XMPP services that do not support encryption.  As part of an initiative to increase the security of the Jabber/XMPP network, this service ($HOST) will be participating in a series of tests to discover the impact of our planned changes, and you may lose the ability to communicate with some of your contacts.

The test days will be on the following dates: January 4, February 22, March 22 and April 19.  On these days we will require that all client and server connections are encrypted.  Unless they enable encryption before that, you will be unable to communicate with your contacts that use these services:

$SERVICES

Your affected contacts are:

$CONTACTS

What can you do?  You may tell your contacts to inform their service administrator about their lack of encryption.  Your contacts may also switch to a more secure service.  A list of public services can be found at https://xmpp.net/directory.php

For more information about the Jabber/XMPP security initiative that we are participating in, please read the announcement at https://stpeter.im/journal/1496.html

If you have any questions or concerns, you may contact us via $CONTACTVIA at $CONTACT
]];

local message = module:get_option_string("manifesto_contact_encryption_warning", default_tpl);
local contact = module:get_option_string("admin_contact_address", module:get_option_array("admins", {})[1]);
if not contact then
	error("mod_manifesto needs you to set 'admin_contact_address' in your config file.", 0);
end
local contact_method = "Jabber/XMPP";
if select(2, contact:gsub("^mailto:", "")) > 0 then
	contact_method = "email";
end

local notified;

module:hook("resource-bind", function (event)
	local session = event.session;

	local now = time();
	local last_notify = notified[session.username] or 0;
	if last_notify > ( now - 86400 * 7 ) then
		return
	end

	timer.add_task(15, function ()
		if session.type ~= "c2s" then return end -- user quit already
		local bad_contacts, bad_hosts = {}, {};
		for contact_jid, item in pairs(session.roster or {}) do
			local _, contact_host = jid_split(contact_jid);
			local bad = false;
			local remote_host_session = host_session.s2sout[contact_host];
			if remote_host_session and remote_host_session.type == "s2sout" then -- Only check remote hosts we have completed s2s connections to
				if not remote_host_session.secure then
					bad = true;
				end
			end
			for session in pairs(incoming_s2s) do
				if session.to_host == host and session.from_host == contact_host and session.type == "s2sin" then
					if not session.secure then
						bad = true;
					end
				end
			end
			if bad then
				local contact_name = item.name;
				if contact_name then
					table.insert(bad_contacts, contact_name.." <"..contact_jid..">");
				else
					table.insert(bad_contacts, contact_jid);
				end
				if not bad_hosts[contact_host] then
					bad_hosts[contact_host] = true;
					table.insert(bad_hosts, contact_host);
				end
			end
		end
		if #bad_contacts > 0 then
			local vars = {
				HOST = host;
				CONTACTS = "    "..table.concat(bad_contacts, "\n    ");
				SERVICES = "    "..table.concat(bad_hosts, "\n    ");
				CONTACTVIA = contact_method, CONTACT = contact;
			};
			session.send(st.message({ type = "headline", from = host }, message:gsub("$(%w+)", vars)));
			notified[session.username] = now;
		end
	end);
end);

function module.load()
	notified = dm.load(nil, host, module.name) or {};
end

function module.save()
	dm.store(nil, host, module.name, notified);
	return { notified = notified };
end

function module.restore(data)
	notified = data.notified;
end

function module.unload()
	dm.store(nil, host, module.name, notified);
end

function module.uninstall()
	dm.store(nil, host, module.name, nil);
end

-- Ad-hoc command for switching to/from "manifesto mode"
local layout = dataforms_new {
	title = "Configure manifesto mode";

	{ name = "FORM_TYPE", type = "hidden", value = "http://prosody.im/protocol/manifesto" };
	{ name = "state", type = "list-single", required = true, label = "Manifesto mode:"};
};

local adhoc_handler = adhoc_initial(layout, function()
	local enabled = config_get(host, "c2s_require_encryption") and config_get(host, "s2s_require_encryption");
	return { state = {
		{ label = "Enabled", value = "enabled", default = enabled },
		{ label = "Configuration settings", value = "config", default = not enabled },
	}};
end, function(fields, err)
	if err then
		local errmsg = {};
		for name, err in pairs(errors) do
			errmsg[#errmsg + 1] = name .. ": " .. err;
		end
		return { status = "completed", error = { message = t_concat(errmsg, "\n") } };
	end

	local info;
	if fields.state == "enabled" then
		config_set(host, "c2s_require_encryption", true);
		config_set(host, "s2s_require_encryption", true);

		for _, session in pairs(s2s_sessions) do
			if not session.secure then
				(session.close or s2s_destroy_session)(session);
			end
		end

		info = "Manifesto mode enabled";
	else
		local ok, err = prosody.reload_config();
		if not ok then
			return { status = "completed", error = { message = "Failed to reload config: " .. tostring(err) } };
		end
		info = "Reset to configuration settings";
	end

	local ok, err = mm_reload(host, "tls");
	if not ok then return { status = "completed", error = { message = "Failed to reload mod_tls: " .. tostring(err) } }; end
	ok, err = mm_reload(host, "s2s");
	if not ok then return { status = "completed", error = { message = "Failed to reload mod_s2s: " .. tostring(err) } }; end
	ok, err = mm_reload(host, "saslauth");
	if not ok then return { status = "completed", error = { message = "Failed to reload mod_saslauth: " .. tostring(err) } }; end

	return { status = "completed", info = info };
end);
module:provides("adhoc", adhoc_new("Configure manifesto mode", "http://prosody.im/protocol/manifesto", adhoc_handler, "admin"));
