local id = require "util.id";
local st = require "util.stanza";
local uuid = require "util.uuid";
local mt = require "util.multitable";
local cache = require "util.cache";

local xmlns_pubsub = "http://jabber.org/protocol/pubsub";
local xmlns_pubsub_event = "http://jabber.org/protocol/pubsub#event";

-- TODO persist
-- TODO query known pubsub nodes to sync current subscriptions
-- TODO subscription ids per 'item' would be handy

local pending_subscription = cache.new(256); -- uuid → node
local pending_unsubscription = cache.new(256); -- uuid → node
local active_subscriptions = mt.new() -- service | node | subscriber | uuid | { item }
function module.save()
	return { active_subscriptions = active_subscriptions.data }
end
function module.restore(data)
	if data and data.active_subscriptions then
		active_subscriptions.data = data.active_subscriptions
	end
end

local valid_events = {"subscribed"; "unsubscribed"; "error"; "item"; "retract"; "purge"; "delete"}

local function subscription_added(item_event)
	local item = item_event.item;
	assert(item.service, "pubsub subscription item MUST have a 'service' field.");
	assert(item.node, "pubsub subscription item MUST have a 'node' field.");
	item.from = item.from or module.host;

	local already_subscribed = false;
	for _ in active_subscriptions:iter(item.service, item.node, item.from, nil) do -- luacheck: ignore 512
		already_subscribed = true;
		break
	end

	item._id = uuid.generate();
	local iq_id = "pubsub-sub-"..id.short();
	pending_subscription:set(iq_id, item._id);
	active_subscriptions:set(item.service, item.node, item.from, item._id, item);

	if not already_subscribed then
		local function send_subscribe()
			module:log("debug", "%s is subscribing to %s:%s", item.from, item.service, item.node);
			module:send(st.iq({ type = "set", id = iq_id, from = item.from, to = item.service })
				:tag("pubsub", { xmlns = xmlns_pubsub })
					:tag("subscribe", { jid = item.from, node = item.node }));
		end

		if prosody.start_time then
			send_subscribe();
		else
			module:log("debug", "%s will subscribe to %s:%s after server startup", item.from, item.service, item.node);
			module:hook_global("server-started", send_subscribe);
		end
	else
		module:log("debug", "%s is already subscribed to %s:%s", item.from, item.service, item.node);
	end
end

for _, event_name in ipairs(valid_events) do
	module:hook("pubsub-event/host/"..event_name, function (event)
		for _, _, _, _, _, cb in active_subscriptions:iter(event.service, event.node, event.stanza.attr.to, nil, "on_"..event_name) do
			event.handled = true;
			pcall(cb, event);
		end
	end);

	module:hook("pubsub-event/bare/"..event_name, function (event)
		for _, _, _, _, _, cb in active_subscriptions:iter(event.service, event.node, event.stanza.attr.to, nil, "on_"..event_name) do
			event.handled = true;
			pcall(cb, event);
		end
	end);
end

function handle_iq(context, event) --luacheck: ignore 212/context
	local stanza = event.stanza;
	local service = stanza.attr.from;

	if not stanza.attr.id then return end -- shouldn't be possible
	if not stanza.attr.id:match("^pubsub%-sub%-") then return end

	local subscribed_node = pending_subscription:get(stanza.attr.id);
	pending_subscription:set(stanza.attr.id, nil);
	local unsubscribed_node = pending_unsubscription:get(stanza.attr.id);
	pending_unsubscription:set(stanza.attr.id, nil);

	if stanza.attr.type == "result" then
		local pubsub_wrapper = stanza:get_child("pubsub", xmlns_pubsub);
		local subscription = pubsub_wrapper and pubsub_wrapper:get_child("subscription");
		if not subscription then return end
		local node = subscription.attr.node;

		local what;
		if subscription.attr.subscription == "subscribed" then
			what = "on_subscribed";
		elseif subscription.attr.subscription == "none" then
			what = "on_unsubscribed";
		end
		if not what then return end -- there are other states but we don't handle them
		for _, _, _, _, _, cb in active_subscriptions:iter(service, node, stanza.attr.to, nil, what) do
			cb(event);
		end
		return true;

	elseif stanza.attr.type == "error" then
		local node = subscribed_node or unsubscribed_node;
		local error_type, error_condition, reason, pubsub_error = stanza:get_error();
		local err = { type = error_type, condition = error_condition, text = reason, extra = pubsub_error };
		if active_subscriptions:get(service) then
			for _, _, _, _, _, cb in active_subscriptions:iter(service, node, stanza.attr.to, nil, "on_error") do
				cb(err);
			end
			return true;
		end
	end
end

module:hook("iq/host", function (event)
	handle_iq("host", event);
end, 1);

module:hook("iq/bare", function (event)
	handle_iq("bare", event);
end, 1);

local function subscription_removed(item_event)
	local item = item_event.item;
	active_subscriptions:set(item.service, item.node, item.from, item._id, nil);
	local node_subs = active_subscriptions:get(item.service, item.node, item.from);
	if node_subs and next(node_subs) then return end

	local iq_id = "pubsub-sub-"..id.short();
	pending_unsubscription:set(iq_id, item._id);

	module:send(st.iq({ type = "set", id = iq_id, from = item.from, to = item.service })
		:tag("pubsub", { xmlns = xmlns_pubsub })
			:tag("unsubscribe", { jid = item.from, node = item.node }))
end

module:handle_items("pubsub-subscription", subscription_added, subscription_removed, true);

function handle_message(context, event)
	local origin, stanza = event.origin, event.stanza;
	local handled = nil;
	local service = stanza.attr.from;
	module:log("debug", "Got message/%s: %s", context, stanza:top_tag());
	for event_container in stanza:childtags("event", xmlns_pubsub_event) do
		for pubsub_event in event_container:childtags() do
			module:log("debug", "Got pubsub event %s", pubsub_event:top_tag());
			local node = pubsub_event.attr.node;
			local event_data = {
				stanza = stanza;
				origin = origin;
				event = pubsub_event;
				service = service;
				node = node;
				handled = false;
			};
			module:fire_event("pubsub-event/" .. context .. "/"..pubsub_event.name, event_data);
			if not handled and event_data.handled then
				handled = true;
			end
		end
	end
	-- If not addressed to the host, let it fall through to normal handling
	-- (it may be on its way to a local client), otherwise, we'll mark the
	-- event as handled to suppress an error response if we handled it.
	if context == "host" and handled then
		return true;
	end
end

module:hook("message/host", function(event)
	return handle_message("host", event);
end);

module:hook("message/bare", function(event)
	return handle_message("bare", event);
end);


function handle_items(context, event)
	for item in event.event:childtags() do
		module:log("debug", "Got pubsub item event %s", item:top_tag());
		event.item = item;
		event.payload = item.tags[1];
		module:fire_event("pubsub-event/" .. context .. "/"..item.name, event);
	end
end

module:hook("pubsub-event/host/items", function (event)
	handle_items("host", event);
end);

module:hook("pubsub-event/bare/items", function (event)
	handle_items("bare", event);
end);
