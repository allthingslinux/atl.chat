local array = require "util.array";
local id = require "util.id";
local it = require "util.iterators";
local set = require "util.set";
local st = require "util.stanza";

module:depends("pubsub_subscription");

local function new_rtbl_subscription(rtbl_service_jid, rtbl_node, handlers)
	local items = {};

	local function notify(event_type, hash)
		local handler = handlers[event_type];
		if not handler then return; end
		handler(hash);
	end

	module:add_item("pubsub-subscription", {
		service = rtbl_service_jid;
		node = rtbl_node;

		-- Callbacks:
		on_subscribed = function()
			module:log("info", "RTBL active: %s:%s", rtbl_service_jid, rtbl_node);
		end;

		on_error = function(err)
			module:log(
				"error",
				"Failed to subscribe to RTBL: %s:%s %s::%s:  %s",
				rtbl_service_jid,
				rtbl_node,
				err.type,
				err.condition,
				err.text
			);
		end;

		on_item = function(event)
			local hash = event.item.attr.id;
			if not hash then return; end
			module:log("debug", "Received new hash from %s:%s: %s", rtbl_service_jid, rtbl_node, hash);
			items[hash] = true;
			notify("added", hash);
		end;

		on_retract = function (event)
			local hash = event.item.attr.id;
			if not hash then return; end
			module:log("debug", "Retracted hash from %s:%s: %s", rtbl_service_jid, rtbl_node, hash);
			items[hash] = nil;
			notify("removed", hash);
		end;

		purge = function()
			module:log("debug", "Purge all hashes from %s:%s", rtbl_service_jid, rtbl_node);
			for hash in pairs(items) do
				items[hash] = nil;
				notify("removed", hash);
			end
		end;
	});

	local request_id = "rtbl-request-"..id.short();

	local function request_list()
		local items_request = st.iq({ to = rtbl_service_jid, from = module.host, type = "get", id = request_id })
			:tag("pubsub", { xmlns = "http://jabber.org/protocol/pubsub" })
				:tag("items", { node = rtbl_node }):up()
			:up();
		module:send(items_request);
	end

	local function update_list(event)
		local from_jid = event.stanza.attr.from;
		if from_jid ~= rtbl_service_jid then
			module:log("debug", "Ignoring RTBL response from unknown sender: %s", from_jid);
			return;
		end
		local items_el = event.stanza:find("{http://jabber.org/protocol/pubsub}pubsub/items");
		if not items_el then
			module:log("warn", "Invalid items response from RTBL service %s:%s", rtbl_service_jid, rtbl_node);
			return;
		end

		local old_entries = set.new(array.collect(it.keys(items)));

		local n_added, n_removed, n_total = 0, 0, 0;
		for item in items_el:childtags("item") do
			local hash = item.attr.id;
			if hash then
				n_total = n_total + 1;
				if not old_entries:contains(hash) then
					-- New entry
					n_added = n_added + 1;
					items[hash] = true;
					notify("added", hash);
				else
					-- Entry already existed
					old_entries:remove(hash);
				end
			end
		end

		-- Remove old entries that weren't in the received list
		for hash in old_entries do
			n_removed = n_removed + 1;
			items[hash] = nil;
			notify("removed", hash);
		end

		module:log("info", "%d RTBL entries received from %s:%s (%d added, %d removed)", n_total, from_jid, rtbl_node, n_added, n_removed);
		return true;
	end

	module:hook("iq-result/host/"..request_id, update_list);
	module:add_timer(0, request_list);
end

return {
	new_rtbl_subscription = new_rtbl_subscription;
}
