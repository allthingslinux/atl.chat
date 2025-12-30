local st = require "util.stanza";
local json = require "util.json";
local filters = { --[[ TODO what's useful? ]] };
local render = require "util.interpolation".new("%b{}", tostring, filters);
local uuid_generate = require "util.uuid".generate;

-- TODO alertmanager supports inclusion of HTTP auth and OAuth, worth looking
-- into for using instead of request IP

module:depends("http");

local pubsub_service = module:depends("pubsub").service;

local error_mapping = {
	["forbidden"] = 403;
	["item-not-found"] = 404;
	["internal-server-error"] = 500;
	["conflict"] = 409;
};

local function publish_payload(node, actor, item_id, payload)
	local post_item = st.stanza("item", { xmlns = "http://jabber.org/protocol/pubsub", id = item_id, })
		:add_child(payload);
	local ok, err = pubsub_service:publish(node, actor, item_id, post_item);
	module:log("debug", ":publish(%q, true, %q, %s) -> %q", node, item_id, payload:top_tag(), err or "");
	if not ok then
		return error_mapping[err] or 500;
	end
	return 202;
end

local global_node_template = module:get_option_string("alertmanager_node_template", "{path?alerts}");
local path_configs = module:get_option("alertmanager_path_configs", {});

function handle_POST(event, path)
	local request = event.request;

	local config = path_configs[path] or {};
	local node_template = config.node_template or global_node_template;
	local publisher = config.publisher or request.ip;

	local payload = json.decode(event.request.body);
	if type(payload) ~= "table" then return 400; end
	if payload.version ~= "4" then return 501; end

	for _, alert in ipairs(payload.alerts) do
		local item = st.stanza("alerts", {xmlns = "urn:uuid:e3bec775-c607-4e9b-9a3f-94de1316d861:v4", status=alert.status});
		for k, v in pairs(alert.annotations) do
			item:text_tag("annotation", v, { name=k });
		end
		for k, v in pairs(alert.labels) do
			item:text_tag("label", v, { name=k });
		end
		item:tag("starts", { at = alert.startsAt}):up();
		if alert.endsAt and alert.status == "resolved" then
			item:tag("ends", { at = alert.endsAt }):up();
		end
		if alert.generatorURL then
			item:tag("link", { href=alert.generatorURL }):up();
		end

		local node = render(node_template, {alert = alert, path = path, payload = payload, request = request});
		local ret = publish_payload(node, publisher, uuid_generate(), item);
		if ret ~= 202 then
			return ret
		end
	end
	return 202;
end

local template = module:get_option_string("alertmanager_body_template", [[
*ALARM!*
Status: {status}
Starts at: {startsAt}{endsAt&
Ends at: {endsAt}}
Labels: {labels%
  {idx}: {item}}
Annotations: {annotations%
  {idx}: {item}}
]]);

module:hook("pubsub-summary/urn:uuid:e3bec775-c607-4e9b-9a3f-94de1316d861:v4", function(event)
	local payload = event.payload;

	local data = {
		status = payload.attr.status,
		firing = "firing" == payload.attr.status,
		resolved = "resolved" == payload.attr.status,
		annotations = {},
		labels = {},
		endsAt = payload:find("ends/@at"),
		startsAt = payload:find("starts/@at"),
	};
	for label in payload:childtags("label") do
		data.labels[tostring(label.attr.name)] = label:get_text();
	end
	for annotation in payload:childtags("annotation") do
		data.annotations[tostring(annotation.attr.name)] = annotation:get_text();
	end

	return render(template, data);
end);

module:provides("http", {
	route = {
		["POST /*"] = handle_POST;
		["POST"] = handle_POST;
	};
});
