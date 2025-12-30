-- Publishes Twitter search results over pubsub
--
-- Config:
-- Component "pubsub.example.com" "pubsub"
-- modules_enabled = {
--   "pubsub_twitter";
-- }
-- twitter_searches = { -- node -> query
--   prosody = "prosody xmpp";
-- }
-- twitter_pull_interval = 20 -- minutes
--

local pubsub = module:depends"pubsub";

local json = require "util.json";
local http = require "net.http";
local set = require "util.set";
local it = require "util.iterators";
local array = require "util.array";

local st = require "util.stanza";
--local dump = require"util.serialization".serialize;

local xmlns_atom = "http://www.w3.org/2005/Atom";

local twitter_searches = module:get_option("twitter_searches", {});
local refresh_interval = module:get_option_number("twitter_pull_interval", 20) * 60;
local api_url = module:get_option_string("twitter_search_url", "http://search.twitter.com/search.json");

local month_number = {
	Jan = "01", Feb = "02", Mar = "03";
	Apr = "04", May = "05", Jun = "06";
	Jul = "07", Aug = "08", Sep = "09";
	Oct = "10", Nov = "11", Dec = "12";
};

local active_searches = {};

local function publish_result(search_name, result)
	local node, id = search_name, result.id_str;
	--"Tue, 02 Apr 2013 15:40:54 +0000"
	local timestamp_date, timestamp_month, timestamp_year, timestamp_time =
		result.created_at:match(" (%d+) (%a+) (%d+) (%d%d:%d%d:%d%d)");

	local timestamp = ("%s-%s-%sT%sZ"):format(timestamp_year, month_number[timestamp_month], timestamp_date, timestamp_time);

	local item = st.stanza("item", { xmlns = "http://jabber.org/protocol/pubsub", id = id })
		:tag("entry", { xmlns = xmlns_atom })
			:tag("id"):text(id):up()
			:tag("author")
				:tag("name"):text(result.from_user_name.." (@"..result.from_user..")"):up()
				:tag("uri"):text("http://twitter.com/"..result.from_user):up()
				:up()
			:tag("published"):text(timestamp):up()
			:tag("title"):text(result.text):up()
			:tag("link", { rel = "alternate" , href = "https://twitter.com/"..result.from_user.."/status/"..id}):up();

	module:log("debug", "Publishing Twitter result: %s", tostring(item));

	local ok, err = pubsub.service:publish(node, true, id, item);
	if not ok then
		if err == "item-not-found" then -- try again
			local ok, err = pubsub.service:create(node, true);
			if not ok then
				module:log("error", "could not create node %s: %s", node, err);
				return;
			end
			local ok, err = pubsub.service:publish(node, true, id, item);
			if not ok then
				module:log("error", "could not create or publish node %s: %s", node, err);
				return
			end
		else
			module:log("error", "publishing %s failed: %s", node, err);
		end
	end
end

local function is_retweet(tweet)
	return not not tweet.text:match("^RT ");
end

function update_all()
	module:log("debug", "Updating all searches");
	for name, search in pairs(active_searches) do
		module:log("debug", "Fetching new results for '%s'", name);
		http.request(search.refresh_url or search.url, nil, function (result_json, code)
			if code ~= 200 then
				module:log("warn", "Twitter search query '%s' failed with code %d", name, code);
				return;
			end
			local response = json.decode(result_json);
			module:log("debug", "Processing %d results for %s", #response.results, name);
			search.refresh_url = api_url..response.refresh_url;
			for _, result in ipairs(response.results) do
				if not is_retweet(result) then
					publish_result(name, result);
				end
			end
		end);
	end
	return refresh_interval;
end

function module.load()
	local config_searches = set.new(array.collect(it.keys(twitter_searches)));
	local current_searches = set.new(array.collect(it.keys(active_searches)));

	local disable_searches = current_searches - config_searches;
	local new_searches = config_searches - current_searches;

	for search_name in disable_searches do
		module:log("debug", "Disabled old Twitter search '%s'", search_name);
		active_searches[search_name] = nil;
	end

	for search_name in new_searches do
		module:log("debug", "Created new Twitter search '%s'", search_name);
		local query = twitter_searches[search_name];
		active_searches[search_name] = {
			url = api_url.."?q="..http.urlencode(query);
		};
	end
end

module:add_timer(5, update_all);
