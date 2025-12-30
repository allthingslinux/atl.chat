local id = require "util.id";
local jid = require "util.jid";
local promise = require "util.promise";
local rm = require "core.rostermanager";
local st = require "util.stanza";

local errors = require "util.error".init(module.name, {
	["statement-not-found"] = { type = "cancel", condition = "item-not-found" };
	["statement-mismatch"] = { type = "cancel", condition = "conlict" };
});

module:hook("presence/bare", function (event)
	local origin, stanza = event.origin, event.stanza;
	if stanza.attr.type ~= "subscribe" then
		return; -- We're only interested in subscription requests
	end
	local moved = stanza:get_child("moved", "urn:xmpp:moved:1");
	if not moved then
		return; -- We're only interested in stanzas with a moved notification
	end

	local verification = stanza:get_child("moved-verification", "https://prosody.im/protocol/moved");
	if verification then
		return; -- We already attempted to verify this stanza
	end

	module:log("debug", "Received moved notification from %s", stanza.attr.from);

	local old_jid = moved:get_child_text("old-jid");
	if not old_jid then
		return; -- Failed to read old JID
	end

	local to_user = jid.node(stanza.attr.to);
	local new_jid_unverified = jid.bare(stanza.attr.from);

	if not rm.is_contact_subscribed(to_user, module.host, old_jid) then
		return; -- Old JID was not an existing contact, ignore
	end

	if rm.is_contact_pending_in(to_user, module.host, new_jid_unverified)
	or rm.is_contact_subscribed(to_user, module.host, new_jid_unverified) then
		return; -- New JID already subscribed or pending, ignore
	end

	local moved_statement_query = st.iq({ to = old_jid, type = "get", id = id.short() })
		:tag("pubsub", { xmlns = "http://jabber.org/protocol/pubsub" })
			:tag("items", { node = "urn:xmpp:moved:1" })
				:tag("item", { id = "current" }):up()
			:up()
		:up();
	-- TODO: Catch and handle <gone/> errors per note in XEP-0283.
	module:send_iq(moved_statement_query):next(function (reply)
		module:log("debug", "Statement reply: %s", reply.stanza);
		local moved_statement = reply.stanza:find("{http://jabber.org/protocol/pubsub}pubsub/items/{http://jabber.org/protocol/pubsub}item/{urn:xmpp:moved:1}moved");
		if not moved_statement then
			return promise.reject(errors.new("statement-not-found")); -- No statement found
		end

		local new_jid = jid.prep(moved_statement:get_child_text("new-jid"));
		if new_jid ~= new_jid_unverified then
			return promise.reject(errors.new("statement-mismatch")); -- Verification failed; JIDs do not match
		end

		-- Verified!
		module:log("info", "Verified moved notification <%s> -> <%s>", old_jid, new_jid);

		-- Add incoming subscription and respond
		rm.set_contact_pending_in(to_user, module.host, new_jid);
		rm.subscribed(to_user, module.host, new_jid);
		module:send(st.presence({ to = new_jid, from = to_user.."@"..module.host, type = "subscribed" }));
		rm.roster_push(to_user, module.host, new_jid);

		-- Request outgoing subscription if old JID had one
		if rm.is_user_subscribed(to_user, module.host, old_jid) then
			module:log("debug", "Requesting subscription to new JID");
			rm.set_contact_pending_out(to_user, module.host, new_jid);
			module:send(st.presence({ to = new_jid, from = to_user.."@"..module.host, type = "subscribe" }));
		end
	end):catch(function (err)
		module:log("debug", "Failed to verify moved statement for <%s> -> <%s>: %s", old_jid, new_jid_unverified, require "util.serialization".serialize(err, "debug"));
		stanza:reset()
			:tag("moved-verification", { xmlns = "https://prosody.im/protocol/moved", status = "failed" })
			:up();
		module:send(stanza, origin);
	end);

	-- Halt processing of the stanza, for now
	return true;
end, 1);
