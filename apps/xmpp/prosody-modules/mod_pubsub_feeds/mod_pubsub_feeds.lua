-- Fetches Atom feeds and publishes to PubSub nodes

local pubsub = module:depends"pubsub";

local time = os.time;
local dt_parse, dt_datetime = require "util.datetime".parse, require "util.datetime".datetime;
local uuid = require "util.uuid".generate;
local hmac_sha1 = require "util.hashes".hmac_sha1;
local parse_xml = require "util.xml".parse;
local st = require "util.stanza";
local translate_rss = module:require("feeds").translate_rss;

local xmlns_atom = "http://www.w3.org/2005/Atom";

local function parse_feed(data)
	local feed, err = parse_xml(data, { allow_processing_instructions = true; allow_comments = true });
	if not feed then return feed, err; end
	if feed.attr.xmlns == xmlns_atom then
		return feed;
	elseif feed.attr.xmlns == nil and feed.name == "rss" then
		return translate_rss(feed);
	end
	return nil, "unsupported-format";
end

local use_pubsubhubub = module:get_option_boolean("use_pubsubhubub", false);
if use_pubsubhubub then
	module:depends"http";
end

local http = require "net.http";
local formdecode = http.formdecode;
local formencode = http.formencode;

local feed_list = module:shared("feed_list");
local legacy_refresh_interval = module:get_option_number("feed_pull_interval", 15);
local refresh_interval = module:get_option_number("feed_pull_interval_seconds", legacy_refresh_interval*60);
local lease_length = tostring(math.floor(module:get_option_number("feed_lease_length", 86400)));

function module.load()
	local config = module:get_option("feeds", { });
	local ok, nodes = pubsub.service:get_nodes(true);
	if not ok then nodes = {}; end
	local new_feed_list = {};
	for node, url in pairs(config) do
		if type(node) == "number" then
			node = url;
		end
		new_feed_list[node] = true;
		if not feed_list[node] then
			local ok, err = pubsub.service:create(node, true);
			if ok or err == "conflict" then
				feed_list[node] = { url = url; node = node; last_update = 0 };
			else
				module:log("error", "Could not create node %s: %s", node, err);
			end
		else
			feed_list[node].url = url;
		end
		if not nodes[node] then
			feed_list[node].last_update = 0;
		end
	end
	for node in pairs(feed_list) do
		if not new_feed_list[node] then
			feed_list[node] = nil;
		end
	end
end

function update_entry(item, data)
	local node = item.node;
	module:log("debug", "parsing %d bytes of data in node %s", #data or 0, node)
	local feed, err = parse_feed(data);
	if not feed then
		module:log("error", "Could not parse feed %q: %s", item.url, err);
		module:log("debug", "Feed data:\n%s\n.", data);
		return;
	end
	local entries = {};
	for entry in feed:childtags("entry") do
		table.insert(entries, entry);
	end
	local ok, last_id = pubsub.service:get_last_item(node, true);
	if not ok then
		module:log("error", "PubSub node %q missing: %s", node, last_id);
		return
	end

	local start_from = #entries;
	for i, entry in ipairs(entries) do
		local id = entry:get_child_text("id");
		if not id then
			local link = entry:get_child("link");
			if link then
				module:log("debug", "Feed %q item %s is missing an id, using <link> instead", item.url, entry:top_tag());
				id = link and link.attr.href;
			else
				module:log("error", "Feed %q item %s is missing both id and link, this feed is unusable", item.url, entry:top_tag());
				return;
			end
			entry:text_tag("id", id);
		end

		if last_id == id then
			-- This should be the first item that we already have.
			start_from = i-1;
			break
		end
	end

	for i = start_from, 1, -1 do -- Feeds are usually in reverse order
		local entry = entries[i];
		entry.attr.xmlns = xmlns_atom;

		local id = entry:get_child_text("id");

		local timestamp = dt_parse(entry:get_child_text("published"));
		if not timestamp then
			timestamp = time();
			entry:text_tag("published", dt_datetime(timestamp));
		end

		if not timestamp or not item.last_update or timestamp > item.last_update then
			local xitem = st.stanza("item", { id = id, xmlns = "http://jabber.org/protocol/pubsub" }):add_child(entry);
			-- TODO Put data from /feed into item/source

			local ok, err = pubsub.service:publish(node, true, id, xitem);
			if not ok then
				module:log("error", "Publishing to node %s failed: %s", node, err);
			elseif timestamp then
				item.last_update = timestamp;
			end
		end
	end

	if item.lease_expires and item.lease_expires > time() then
		item.subscription = nil;
		item.lease_expires = nil;
	end
	if use_pubsubhubub and not item.subscription then
		--module:log("debug", "check if %s has a hub", item.node);
		for link in feed:childtags("link") do
			if link.attr.rel == "hub" then
				item.hub = link.attr.href;
				module:log("debug", "Node %s has a hub: %s", item.node, item.hub);
				return subscribe(item);
			end
		end
	end
end

function fetch(item, callback) -- HTTP Pull
	local headers = {
		["If-None-Match"] = item.etag;
		["Accept"] = "application/atom+xml, application/x-rss+xml, application/xml";
	};
	http.request(item.url, { headers = headers }, function(data, code, resp)
		if code == 200 then
			if callback then callback(item, data) end
			if resp.headers then
				item.etag = resp.headers.etag
			end
		elseif code == 304 then
			module:log("debug", "No updates to %q", item.url);
		elseif code == 301 and resp.headers.location then
			module:log("info", "Feed %q has moved to %q", item.url, resp.headers.location);
		elseif code <= 100 then
			module:log("error", "Error fetching %q: %q[%d]", item.url, data, code);
		else
			module:log("debug", "Unhandled status code %d when fetching %q", code, item.url);
		end
	end);
end

function refresh_feeds(now)
	--module:log("debug", "Refreshing feeds");
	for _, item in pairs(feed_list) do
		if item.subscription ~= "subscribe" and item.last_update + refresh_interval < now then
			--module:log("debug", "checking %s", item.node);
			fetch(item, update_entry);
		end
	end
	return refresh_interval;
end

local function format_url(node)
	return module:http_url(nil, "/callback") .. "?" .. formencode({ node = node });
end

function subscribe(feed, want)
	want = want or "subscribe";
	feed.secret = feed.secret or uuid();
	local body = formencode{
		["hub.callback"] = format_url(feed.node);
		["hub.mode"] = want;
		["hub.topic"] = feed.url;
		["hub.verify"] = "async"; -- COMPAT this is REQUIRED in the 0.3 draft but removed in 0.4
		["hub.secret"] = feed.secret;
		["hub.lease_seconds"] = lease_length;
	};

	--module:log("debug", "subscription request, body: %s", body);

	--FIXME The subscription states and related stuff
	feed.subscription = want;
	http.request(feed.hub, { body = body }, function(data, code)
		module:log("debug", "subscription to %s submitted, status %s", feed.node, tostring(code));
		if code >= 400 then
			module:log("error", "There was something wrong with our subscription request, body: %s", tostring(data));
			feed.subscription = "failed";
		end
	end);
end

function handle_http_request(event)
	local request = event.request;
	local method = request.method;
	local body = request.body;

	local query = request.url.query or {}; --FIXME
	if query and type(query) == "string" then
		query = formdecode(query);
	end

	local feed = feed_list[query.node];
	if not feed then
		if query["hub.mode"] == "unsubscribe" then
			-- Unsubscribe from unknown feed
			module:log("debug", "Unsubscribe from unknown feed %s -- %s", query["hub.topic"], formencode(query));
			return { headers = { content_type = "text/plain" }; body = query["hub.challenge"] };
		end
		module:log("debug", "Push for unknown feed %s -- %s", query["hub.topic"], formencode(query));
		return 404;
	end

	if method == "GET" then
		if query.node then
			if query["hub.topic"] ~= feed.url then
				module:log("debug", "Invalid topic: %s", tostring(query["hub.topic"]))
				return 404
			end
			if query["hub.mode"] == "denied" then
				module:log("info", "Subscription denied: %s", tostring(query["hub.reason"] or "No reason given"))
				feed.subscription = "denied";
				return "Ok then :(";
			elseif query["hub.mode"] == feed.subscription then
				module:log("debug", "Confirming %s request to %s", feed.subscription, feed.url)
			else
				module:log("debug", "Invalid mode: %s", tostring(query["hub.mode"]))
				return 400
			end
			local lease_seconds = tonumber(query["hub.lease_seconds"]);
			if lease_seconds then
				feed.lease_expires = time() + lease_seconds - refresh_interval * 2;
			end
			return { headers = { content_type = "text/plain" }; body = query["hub.challenge"] };
		end
		return 400;
	elseif method == "POST" then
		if #body > 0 then
			module:log("debug", "got %d bytes PuSHed for %s", #body, query.node);
			local signature = request.headers.x_hub_signature;
			if feed.secret then
				local localsig = "sha1=" .. hmac_sha1(feed.secret, body, true);
				if localsig ~= signature then
					module:log("debug", "Invalid signature, got %s but wanted %s", tostring(signature), tostring(localsig));
					return 401;
				end
				module:log("debug", "Valid signature");
			end
			update_entry(feed, body);
			return 202;
		end
		return 400;
	end
	return 501;
end

if use_pubsubhubub then
	module:provides("http", {
		default_path = "/callback";
		route = {
			GET = handle_http_request;
			POST = handle_http_request;
			-- This all?
		};
	});
end

module:add_timer(1, refresh_feeds);
