-- XEP-0257: Client Certificates Management implementation for Prosody
-- Copyright (C) 2012 Thijs Alkemade
--
-- This file is MIT/X11 licensed.

local st = require "util.stanza";
local jid_bare = require "util.jid".bare;
local jid_split = require "util.jid".split;
local xmlns_saslcert = "urn:xmpp:saslcert:1";
local dm_load = require "util.datamanager".load;
local dm_store = require "util.datamanager".store;
local dm_table = "client_certs";
local ssl = require "ssl";
local util_x509 = require "util.x509";
local id_on_xmppAddr = "1.3.6.1.5.5.7.8.5";
local id_ce_subjectAltName = "2.5.29.17";
local digest_algo = "sha1";
local base64 = require "util.encodings".base64;

local function get_id_on_xmpp_addrs(cert)
	local id_on_xmppAddrs = {};
	for k,ext in pairs(cert:extensions()) do
		if k == id_ce_subjectAltName then
			for e,extv in pairs(ext) do
				if e == id_on_xmppAddr then
					for i,v in ipairs(extv) do
						id_on_xmppAddrs[#id_on_xmppAddrs+1] = v;
					end
				end
			end
		end
	end
	module:log("debug", "Found JIDs: (%d) %s", #id_on_xmppAddrs, table.concat(id_on_xmppAddrs, ", "));
	return id_on_xmppAddrs;
end

local function enable_cert(username, cert, info)
	-- Check the certificate. Is it not expired? Does it include id-on-xmppAddr?

	--[[ the method expired doesn't exist in luasec .. yet?
	if cert:expired() then
	module:log("debug", "This certificate is already expired.");
	return nil, "This certificate is expired.";
	end
	--]]

	if not cert:validat(os.time()) then
		module:log("debug", "This certificate is not valid at this moment.");
	end

	local valid_id_on_xmppAddrs;
	local require_id_on_xmppAddr = true;
	if require_id_on_xmppAddr then
		valid_id_on_xmppAddrs = get_id_on_xmpp_addrs(cert);

		local found = false;
		for i,k in pairs(valid_id_on_xmppAddrs) do
			if jid_bare(k) == (username .. "@" .. module.host) then
				found = true;
				break;
			end
		end

		if not found then
			return nil, "This certificate has no valid id-on-xmppAddr field.";
		end
	end

	local certs = dm_load(username, module.host, dm_table) or {};

	info.pem = cert:pem();
	local digest = cert:digest(digest_algo);
	info.digest = digest;
	certs[info.name] = info;

	dm_store(username, module.host, dm_table, certs);
	return true
end

local function disable_cert(username, name, disconnect)
	local certs = dm_load(username, module.host, dm_table) or {};

	local info = certs[name];

	if not info then
		return nil, "item-not-found"
	end

	certs[name] = nil;

	if disconnect then
		module:log("debug", "%s revoked a certificate! Disconnecting all clients that used it", username);
		local sessions = hosts[module.host].sessions[username].sessions;
		local disabled_cert_pem = info.pem;

		for _, session in pairs(sessions) do
			if session and session.conn and session.conn:socket().getpeercertificate then
				local cert = session.conn:socket():getpeercertificate();

				if cert and cert:pem() == disabled_cert_pem then
					module:log("debug", "Found a session that should be closed: %s", tostring(session));
					session:close{ condition = "not-authorized", text = "This client side certificate has been revoked."};
				end
			end
		end
	end

	dm_store(username, module.host, dm_table, certs);
	return info;
end

module:hook("iq-get/self/"..xmlns_saslcert..":items", function(event)
	local origin, stanza = event.origin, event.stanza;
	module:log("debug", "%s requested items", origin.full_jid);

	local reply = st.reply(stanza):tag("items", { xmlns = xmlns_saslcert });
	local certs = dm_load(origin.username, module.host, dm_table) or {};

	for digest,info in pairs(certs) do
		reply:tag("item")
			:tag("name"):text(info.name):up()
			:tag("x509cert"):text(info.x509cert):up()
		:up();
	end

	origin.send(reply);
	return true
end);

module:hook("iq-set/self/"..xmlns_saslcert..":append", function(event)
	local origin, stanza = event.origin, event.stanza;
	local append = stanza:get_child("append", xmlns_saslcert);
	local name = append:get_child_text("name", xmlns_saslcert);
	local x509cert = append:get_child_text("x509cert", xmlns_saslcert);

	if not x509cert or not name then
		origin.send(st.error_reply(stanza, "cancel", "bad-request", "Missing fields.")); -- cancel? not modify?
		return true
	end

	local can_manage = append:get_child("no-cert-management", xmlns_saslcert) ~= nil;
	x509cert = x509cert:gsub("^%s*(.-)%s*$", "%1");

	local cert = ssl.loadcertificate(util_x509.der2pem(base64.decode(x509cert)));

	if not cert then
		origin.send(st.error_reply(stanza, "modify", "not-acceptable", "Could not parse X.509 certificate"));
		return true;
	end

	local ok, err = enable_cert(origin.username, cert, {
		name = name,
		x509cert = x509cert,
		no_cert_management = can_manage,
	});

	if not ok then
		origin.send(st.error_reply(stanza, "cancel", "bad-request", err));
		return true -- REJECT?!
	end

	module:log("debug", "%s added certificate named %s", origin.full_jid, name);

	origin.send(st.reply(stanza));

	return true
end);


local function handle_disable(event)
	local origin, stanza = event.origin, event.stanza;
	local disable = stanza.tags[1];
	module:log("debug", "%s disabled a certificate", origin.full_jid);

	local name = disable:get_child_text("name");

	if not name then
		origin.send(st.error_reply(stanza, "cancel", "bad-request", "No key specified."));
		return true
	end

	disable_cert(origin.username, name, disable.name == "revoke");

	origin.send(st.reply(stanza));

	return true
end

module:hook("iq-set/self/"..xmlns_saslcert..":disable", handle_disable);
module:hook("iq-set/self/"..xmlns_saslcert..":revoke", handle_disable);

-- Ad-hoc command
local adhoc_new = module:require "adhoc".new;
local dataforms_new = require "util.dataforms".new;

local function generate_error_message(errors)
	local errmsg = {};
	for name, err in pairs(errors) do
		errmsg[#errmsg + 1] = name .. ": " .. err;
	end
	return table.concat(errmsg, "\n");
end

local choose_subcmd_layout = dataforms_new {
	title = "Certificate management";
	instructions = "What action do you want to perform?";

	{ name = "FORM_TYPE", type = "hidden", value = "http://prosody.im/protocol/certs#subcmd" };
	{ name = "subcmd", type = "list-single", label = "Actions", required = false,
		options = { {label = "Add certificate", value = "add"},
			  {label = "List certificates", value = "list"},
			  {label = "Disable certificate", value = "disable"},
			  {label = "Revoke certificate", value = "revoke"},
		};
	};
};

local add_layout = dataforms_new {
	title = "Adding a certificate";
	instructions = "Enter the certificate in PEM format";

	{ name = "FORM_TYPE", type = "hidden", value = "http://prosody.im/protocol/certs#add" };
	{ name = "name", type = "text-single", label = "Name", required = true };
	{ name = "cert", type = "text-multi", label = "PEM certificate", required = true };
	{ name = "manage", type = "boolean", label = "Can manage certificates", value = true };
};


local disable_layout_stub = dataforms_new { { name = "cert", type = "list-single", label = "Certificate", required = true } };


local function adhoc_handler(self, data, state)
	if data.action == "cancel" then return { status = "canceled" }; end

	if not state or data.action == "prev" then
		return { status = "executing", form = choose_subcmd_layout, actions = { "next" } }, {};
	end

	if not state.subcmd then
		local fields, errors = choose_subcmd_layout:data(data.form);
		if errors then
			return { status = "completed", error = { message = generate_error_message(errors) } };
		end
		local subcmd = fields.subcmd

		if subcmd == "add" then
			return { status = "executing", form = add_layout, actions = { "prev", "next", "complete" } }, { subcmd = "add" };
		elseif subcmd == "list" then
			local list_layout = dataforms_new {
				title = "List of certificates";
			};

			local certs = dm_load(jid_split(data.from), module.host, dm_table) or {};

			for digest, info in pairs(certs) do
				list_layout[#list_layout + 1] = { name = info.name, type = "text-multi", label = info.name, value = info.x509cert };
			end

			return { status = "completed", result = list_layout };
		else
			local layout = dataforms_new {
				{ name = "FORM_TYPE", type = "hidden", value = "http://prosody.im/protocol/certs#" .. subcmd };
				{ name = "cert", type = "list-single", label = "Certificate", required = true };
			};

			if subcmd == "disable" then
				layout.title = "Disabling a certificate";
				layout.instructions = "Select the certificate to disable";
			elseif subcmd == "revoke" then
				layout.title = "Revoking a certificate";
				layout.instructions = "Select the certificate to revoke";
			end

			local certs = dm_load(jid_split(data.from), module.host, dm_table) or {};

			local values = {};
			for digest, info in pairs(certs) do
				values[#values + 1] = { label = info.name, value = info.name };
			end

			return { status = "executing", form = { layout = layout, values = { cert = values } }, actions = { "prev", "next", "complete" } },
				{ subcmd = subcmd };
		end
	end

	if state.subcmd == "add" then
		local fields, errors = add_layout:data(data.form);
		if errors then
			return { status = "completed", error = { message = generate_error_message(errors) } };
		end

		local name = fields.name;
		local x509cert = fields.cert:gsub("^%s*(.-)%s*$", "%1");

		local cert = ssl.loadcertificate(x509cert);

		if not cert then
			return { status = "completed", error = { message = "Could not parse X.509 certificate" } };
		end

		local ok, err = enable_cert(jid_split(data.from), cert, {
			name = name,
			x509cert = x509cert,
			no_cert_management = not fields.manage
		});

		if not ok then
			return { status = "completed", error = { message = err } };
		end

		module:log("debug", "%s added certificate named %s", data.from, name);

		return { status = "completed", info = "Successfully added certificate " .. name .. "." };
	else
		local fields, errors = disable_layout_stub:data(data.form);
		if errors then
			return { status = "completed", error = { message = generate_error_message(errors) } };
		end

		local info = disable_cert(jid_split(data.from), fields.cert, state.subcmd == "revoke" );

		if state.subcmd == "revoke" then
			return { status = "completed", info = "Revoked certificate " .. info.name .. "."  };
		else
			return { status = "completed", info = "Disabled certificate " .. info.name .. "."  };
		end
	end
end

local cmd_desc = adhoc_new("Manage certificates", "http://prosody.im/protocol/certs", adhoc_handler, "any");
module:provides("adhoc", cmd_desc);

-- Here comes the SASL EXTERNAL stuff

local now = os.time;
module:hook("stream-features", function(event)
	local session, features = event.origin, event.features;
	if session.secure and session.type == "c2s_unauthed" then
		local socket = session.conn:socket();
		if not socket.getpeercertificate then
			module:log("debug", "Not a TLS socket");
			return
		end
		local cert = socket:getpeercertificate();
		if not cert then
			module:log("error", "No Client Certificate");
			return
		end
		module:log("info", "Client Certificate: %s", cert:digest(digest_algo));
		if not cert:validat(now()) then
			module:log("debug", "Client has an expired certificate", cert:digest(digest_algo));
			return
		end
		module:log("debug", "Stream features:\n%s", tostring(features));
		local mechs = features:get_child("mechanisms", "urn:ietf:params:xml:ns:xmpp-sasl");
		if mechs then
			mechs:tag("mechanism"):text("EXTERNAL");
		end
	end
end, -1);

local sm_make_authenticated = require "core.sessionmanager".make_authenticated;

module:hook("stanza/urn:ietf:params:xml:ns:xmpp-sasl:auth", function(event)
	local session, stanza = event.origin, event.stanza;
	if session.type == "c2s_unauthed" and stanza.attr.mechanism == "EXTERNAL" then
		if session.secure then
			local cert = session.conn:socket():getpeercertificate();
			local username_data = stanza:get_text();
			local username = nil;

			if username_data == "=" then
				-- Check for either an id_on_xmppAddr
				local jids = get_id_on_xmpp_addrs(cert);

				if not (#jids == 1) then
					module:log("debug", "Client tried to authenticate as =, but certificate has multiple JIDs.");
					module:fire_event("authentication-failure", { session = session, condition = "not-authorized" });
					session.send(st.stanza("failure", { xmlns="urn:ietf:params:xml:ns:xmpp-sasl"}):tag"not-authorized");
					return true;
				end

				username = jids[1];
			else
				-- Check the base64 encoded username
				username = base64.decode(username_data);
			end

			local user, host, resource = jid_split(username);

			module:log("debug", "Inferred username: %s", user or "nil");

			if (not username) or (not host == module.host) then
				module:log("debug", "No valid username found for %s", tostring(session));
				module:fire_event("authentication-failure", { session = session, condition = "not-authorized" });
				session.send(st.stanza("failure", { xmlns="urn:ietf:params:xml:ns:xmpp-sasl"}):tag"not-authorized");
				return true;
			end

			local certs = dm_load(user, module.host, dm_table) or {};
			local digest = cert:digest(digest_algo);
			local pem = cert:pem();

			for name,info in pairs(certs) do
				if info.digest == digest and info.pem == pem then
					sm_make_authenticated(session, user);
					module:fire_event("authentication-success", { session = session });
					session.send(st.stanza("success", { xmlns="urn:ietf:params:xml:ns:xmpp-sasl"}));
					session:reset_stream();
					return true;
				end
			end
			module:fire_event("authentication-failure", { session = session, condition = "not-authorized" });
			session.send(st.stanza("failure", { xmlns="urn:ietf:params:xml:ns:xmpp-sasl"}):tag"not-authorized");
		else
			session.send(st.stanza("failure", { xmlns="urn:ietf:params:xml:ns:xmpp-sasl"}):tag"encryption-required");
		end
		return true;
	end
end, 1);

module:add_feature(xmlns_saslcert);
