module:depends("http");

local lom = require "lxp.lom";
local st = require "util.stanza";
local json = require "util.json";
local datetime = require "util.datetime".datetime;


local pubsub_service = module:depends("pubsub").service;
local node = module:get_option("pivotaltracker_node", "tracker");

local stanza_mt = require "util.stanza".stanza_mt;
local function stanza_from_lom(lom)
	if lom.tag then
		local child_tags, attr = {}, {};
		local stanza = setmetatable({ name = lom.tag, attr = attr, tags = child_tags }, stanza_mt);
		for i, attr_name in ipairs(lom.attr) do
			attr[attr_name] = lom.attr[attr_name]
		end
		for i, child in ipairs(lom) do
			if child.tag then
				child = stanza_from_lom(child);
				child_tags[#child_tags+1] = child;
			end
			stanza[i] = child;
		end
		return stanza;
	else
		return lom;
	end
end

function handle_POST(event)
	local data = lom.parse(event.request.body);

	if not data then
		return "Invalid XML. From you of all people...";
	end

	data = stanza_from_lom(data);

	if data.name ~= "activity" then
		return "Unrecognised XML element: "..data.name;
	end

	local activity_id = data:get_child("id"):get_text();
	local description = data:get_child("description"):get_text();
	local author_name = data:get_child("author"):get_text();
	local story = data:get_child("stories"):get_child("story");
	local story_link = story:get_child("url"):get_text();

	local ok, err = pubsub_service:publish(node, true, "activity", st.stanza("item", { id = "activity", xmlns = "http://jabber.org/protocol/pubsub" })
		:tag("entry", { xmlns = "http://www.w3.org/2005/Atom" })
			:tag("id"):text(activity_id):up()
			:tag("title"):text(description):up()
			:tag("link", { rel = "alternate", href = story_link }):up()
			:tag("published"):text(datetime()):up()
			:tag("author")
				:tag("name"):text(author_name):up()
				:up()
	);

	module:log("debug", "Handled POST: \n%s\n", tostring(event.request.body));
	return "Thank you Pivotal!";
end

module:provides("http", {
	route = {
		POST = handle_POST;
	};
});

function module.load()
	if not pubsub_service.nodes[node] then
		local ok, err = pubsub_service:create(node, true);
		if not ok then
			module:log("error", "Error creating node: %s", err);
		else
			module:log("debug", "Node %q created", node);
		end
	end
end
