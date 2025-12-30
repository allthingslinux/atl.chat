local st = require "util.stanza";
local datetime = require "util.datetime";

local function shorten(x) return string.sub(x, 1, -32) end

local function firstline(x) return x:match("^[^\r\n]*") end

local function branch(x) return string.sub(x, 12) end

local function tag(x) return string.sub(x, 11) end

local function noop(x) return x end

local filters = {
	shorten = shorten,
	firstline = firstline,
	branch = branch,
	tag = tag
}

local render = require"util.interpolation".new("%b{}", noop, filters);

local function get_item(data, templates)
	local function render_tpl(name) return render(templates[name], {data = data}) end

	local now = datetime.datetime()
	local id = render(templates["id"], {data = data})
	-- LuaFormatter off
	return st.stanza("item", {id = id, xmlns = "http://jabber.org/protocol/pubsub"})
		:tag("entry", {xmlns = "http://www.w3.org/2005/Atom"})
			:tag("id"):text(id):up()
			:tag("title"):text(render_tpl("title")):up()
			:tag("content", {type = "text"}):text(render_tpl("content")):up()
			:tag("link", {rel = "alternate", href = render_tpl("link")}):up()
			:tag("published"):text(now):up()
			:tag("updated"):text(now):up()
			:tag("author")
			:tag("name")
				:text(data.sender.username):up()
				:tag("email"):text(data.sender.email)
    -- LuaFormatter on
end

return get_item
