local st = require "util.stanza";
local xml = require "util.xml";

local xmlns_label = "urn:xmpp:sec-label:0";
local xmlns_label_catalog = "urn:xmpp:sec-label:catalog:2";
local xmlns_label_catalog_old = "urn:xmpp:sec-label:catalog:0"; -- COMPAT

module:add_feature(xmlns_label);
module:add_feature(xmlns_label_catalog);
module:add_feature(xmlns_label_catalog_old);

module:hook("account-disco-info", function(event) -- COMPAT
	local stanza = event.stanza;
	if stanza then
		stanza:tag('feature', {var=xmlns_label}):up();
		stanza:tag('feature', {var=xmlns_label_catalog}):up();
	end;
end);

local default_labels = {
	{
		name = "Unclassified",
		label = true,
		default = true,
	},
	Classified = {
		SECRET = { color = "black", bgcolor = "aqua", label = "THISISSECRET" };
		PUBLIC = { label = "THISISPUBLIC" };
	};
};
local catalog_name = module:get_option_string("security_catalog_name", "Default");
local catalog_desc = module:get_option_string("security_catalog_desc", "My labels");
local labels = module:get_option("security_labels", default_labels);

function handle_catalog_request(request)
	local catalog_request = request.stanza.tags[1];
	local reply = st.reply(request.stanza)
		:tag("catalog", {
			xmlns = catalog_request.attr.xmlns,
			to = catalog_request.attr.to,
			name = catalog_name,
			desc = catalog_desc
		});

	local function add_labels(catalog, labels, selector)
		local function add_item(item, name)
			local name = name or item.name;
			if item.label then
				if catalog_request.attr.xmlns == xmlns_label_catalog then
					catalog:tag("item", {
						selector = selector..name,
						default = item.default and "true" or nil,
					}):tag("securitylabel", { xmlns = xmlns_label })
				else -- COMPAT
					catalog:tag("securitylabel", {
						xmlns = xmlns_label,
						selector = selector..name,
						default = item.default and "true" or nil,
					})
				end
				if item.display or item.color or item.bgcolor then
					catalog:tag("displaymarking", {
						fgcolor = item.color,
						bgcolor = item.bgcolor,
					}):text(item.display or name):up();
				end
				if item.label == true then
					catalog:tag("label"):text(name):up();
				elseif type(item.label) == "string" then
					-- TODO Do we need anything other than XML parsing?
					if item.label:sub(1,1) == "<" then
						catalog:tag("label"):add_child(xml.parse(item.label)):up();
					else
						catalog:tag("label"):text(item.label):up();
					end
				elseif type(item.label) == "table" then
					catalog:tag("label"):add_child(item.label):up();
				end
				catalog:up();
				if catalog_request.attr.xmlns == xmlns_label_catalog then
					catalog:up();
				end
			else
				add_labels(catalog, item, (selector or "")..name.."|");
			end
		end
		for i = 1,#labels do
			add_item(labels[i])
		end
		for name, child in pairs(labels) do
			if type(name) == "string" then
				add_item(child, name)
			end
		end
	end
	-- TODO query remote servers
	--[[ FIXME later
	labels = module:fire_event("sec-label-catalog", {
			to = catalog_request.attr.to,
			request = request; -- or just origin?
			labels = labels;
		}) or labels;
		--]]
	add_labels(reply, labels, "");
	request.origin.send(reply);
	return true;
end
module:hook("iq/host/"..xmlns_label_catalog..":catalog", handle_catalog_request);
module:hook("iq/self/"..xmlns_label_catalog..":catalog", handle_catalog_request); -- COMPAT
module:hook("iq/self/"..xmlns_label_catalog_old..":catalog", handle_catalog_request); -- COMPAT
