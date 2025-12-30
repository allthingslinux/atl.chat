local array = require "util.array";
local jid = require "util.jid";
local json = require "util.json";
local st = require "util.stanza";
local xml = require "util.xml";
local map = require "util.datamapper";

local schema do
	local f = assert(module:load_resource("res/schema-xmpp.json"));
	schema = json.decode(f:read("*a"))
	f:close();
	-- Copy common properties to all stanza kinds
	if schema._common then
		for key, prop in pairs(schema._common) do
			for _, copyto in pairs(schema.properties) do
				copyto.properties[key] = prop;
			end
		end
	end
end

-- Some mappings that are still hard to do in a nice way with util.datamapper
local field_mappings; -- in scope for "func" mappings
field_mappings = {
	-- XEP-0071
	html = {
		type = "func", xmlns = "http://jabber.org/protocol/xhtml-im", tagname = "html",
		st2json = function (s) --> json string
			return (tostring(s:get_child("body", "http://www.w3.org/1999/xhtml")):gsub(" xmlns='[^']*'", "", 1));
		end;
		json2st = function (s) --> xml
			if type(s) == "string" then
				return assert(xml.parse("<x:html xmlns:x='http://jabber.org/protocol/xhtml-im' xmlns='http://www.w3.org/1999/xhtml'>" .. s .. "</x:html>"));
			end
		end;
	};

	-- XEP-0030
	disco = {
		type = "func", xmlns = "http://jabber.org/protocol/disco#info", tagname = "query",
		st2json = function (s) --> array of features
			if s.tags[1] == nil then
				return s.attr.node or true;
			end
			local identities, features, extensions = array(), array(), {};

			-- features and identities could be done with util.datamapper
			for tag in s:childtags() do
				if tag.name == "identity" and tag.attr.category and tag.attr.type then
					identities:push({ category = tag.attr.category, type = tag.attr.type, name = tag.attr.name });
				elseif tag.name == "feature" and tag.attr.var then
					features:push(tag.attr.var);
				end
			end

			-- Especially this would be hard to do with util.datamapper
			for form in s:childtags("x", "jabber:x:data") do
				local jform = field_mappings.formdata.st2json(form);
				local form_type = jform["FORM_TYPE"];
				if jform then
					jform["FORM_TYPE"] = nil;
					extensions[form_type] = jform;
				end
			end

			if next(extensions) == nil then extensions = nil; end
			return { node = s.attr.node, identities = identities, features = features, extensions = extensions };
		end;
		json2st = function (s)
			if type(s) == "table" and s ~= json.null then
				local disco = st.stanza("query", { xmlns = "http://jabber.org/protocol/disco#info", node = s.node });
				if s.identities then
					for _, identity in ipairs(s.identities) do
						disco:tag("identity", { category = identity.category, type = identity.type, name = identity.name }):up();
					end
				end
				if s.features then
					for _, feature in ipairs(s.features) do
						disco:tag("feature", { var = feature }):up();
					end
				end
				if s.extensions then
					for form_type, extension in pairs(s.extensions) do
						extension["FORM_TYPE"] = form_type;
						disco:add_child(field_mappings.formdata.json2st(extension));
					end
				end
				return disco;
			elseif type(s) == "string" then
				return st.stanza("query", { xmlns = "http://jabber.org/protocol/disco#info", node = s });
			else
				return st.stanza("query", { xmlns = "http://jabber.org/protocol/disco#info", });
			end
		end;
	};

	items = {
		type = "func", xmlns = "http://jabber.org/protocol/disco#items", tagname = "query",
		st2json = function (s) --> array of features | map with node
			if s.tags[1] == nil then
				return s.attr.node or true;
			end

			local items = array();
			for item in s:childtags("item") do
				items:push({ jid = item.attr.jid, node = item.attr.node, name = item.attr.name });
			end
			return items;
		end;
		json2st = function (s)
			if type(s) == "table" and s ~= json.null then
				local disco = st.stanza("query", { xmlns = "http://jabber.org/protocol/disco#items", node = s.node });
				for _, item in ipairs(s) do
					if type(item) == "string" then
						disco:tag("item", { jid = item });
					elseif type(item) == "table" then
						disco:tag("item", { jid = item.jid, node = item.node, name = item.name });
					end
				end
				return disco;
			elseif type(s) == "string" then
				return st.stanza("query", { xmlns = "http://jabber.org/protocol/disco#items", node = s });
			else
				return st.stanza("query", { xmlns = "http://jabber.org/protocol/disco#items", });
			end
		end;
	};

	-- XEP-0050: Ad-Hoc Commands
	command = { type = "func", xmlns = "http://jabber.org/protocol/commands", tagname = "command",
		st2json = function (s)
			local cmd = {
				action = s.attr.action,
				node = s.attr.node,
				sessionid = s.attr.sessionid,
				status = s.attr.status,
			};
			local actions = s:get_child("actions");
			local note = s:get_child("note");
			local form = s:get_child("x", "jabber:x:data");
			if actions then
				cmd.actions = {
					execute = actions.attr.execute,
				};
				for action in actions:childtags() do
					cmd.actions[action.name] = true
				end
			elseif note then
				cmd.note = {
					type = note.attr.type;
					text = note:get_text();
				};
			end
			if form then
				cmd.form = field_mappings.dataform.st2json(form);
			end
			return cmd;
		end;
		json2st = function (s)
			if type(s) == "table" and s ~= json.null then
				local cmd = st.stanza("command", {
					xmlns = "http://jabber.org/protocol/commands",
					action = s.action,
					node = s.node,
					sessionid = s.sessionid,
					status = s.status,
				});
				if type(s.actions) == "table" then
					cmd:tag("actions", { execute = s.actions.execute });
					do
						if s.actions.next == true then
							cmd:tag("next"):up();
						end
						if s.actions.prev == true then
							cmd:tag("prev"):up();
						end
						if s.actions.complete == true then
							cmd:tag("complete"):up();
						end
					end
					cmd:up();
				elseif type(s.note) == "table" then
					cmd:text_tag("note", s.note.text, { type = s.note.type });
				end
				if s.form then
					cmd:add_child(field_mappings.dataform.json2st(s.form));
				elseif s.data then
					cmd:add_child(field_mappings.formdata.json2st(s.data));
				end
				return cmd;
			elseif type(s) == "string" then -- assume node
				return st.stanza("command", { xmlns = "http://jabber.org/protocol/commands", node = s });
			end
			-- else .. missing required attribute
		end;
	};

	-- XEP-0066: Out of Band Data
	-- TODO Replace by oob.url in datamapper schema
	oob_url = { type = "func", xmlns = "jabber:x:oob", tagname = "x",
		-- XXX namespace depends on whether it's in an iq or message stanza
		st2json = function (s)
			return s:get_child_text("url");
		end;
		json2st = function (s)
			if type(s) == "string" then
				return st.stanza("x", { xmlns = "jabber:x:oob" }):text_tag("url", s);
			end
		end;
	};

	-- XEP-0004: Data Forms
	dataform = {
		-- Generic and complete dataforms mapping
		type = "func", xmlns = "jabber:x:data", tagname = "x",
		st2json = function (s)
			local fields = array();
			local form = {
				type = s.attr.type;
				title = s:get_child_text("title");
				instructions = s:get_child_text("instructions");
				fields = fields;
			};
			for field in s:childtags("field") do
				local i = {
					var = field.attr.var;
					type = field.attr.type;
					label = field.attr.label;
					desc = field:get_child_text("desc");
					required = field:get_child("required") and true or nil;
					value = field:get_child_text("value");
				};
				if field.attr.type == "jid-multi" or field.attr.type == "list-multi" or field.attr.type == "text-multi" then
					local value = array();
					for v in field:childtags("value") do
						value:push(v:get_text());
					end
					if field.attr.type == "text-multi" then
						i.value = value:concat("\n");
					else
						i.value = value;
					end
				end
				if field.attr.type == "list-single" or field.attr.type == "list-multi" then
					local options = array();
					for o in field:childtags("option") do
						options:push({ label = o.attr.label, value = o:get_child_text("value") });
					end
					i.options = options;
				end
				fields:push(i);
			end
			return form;
		end;
		json2st = function (x)
			if type(x) == "table" and x ~= json.null then
				local form = st.stanza("x", { xmlns = "jabber:x:data", type = x.type });
				if x.title then
					form:text_tag("title", x.title);
				end
				if x.instructions then
					form:text_tag("instructions", x.instructions);
				end
				if type(x.fields) == "table" then
					for _, f in ipairs(x.fields) do
						if type(f) == "table" then
							form:tag("field", { var = f.var, type = f.type, label = f.label });
							if f.desc then
								form:text_tag("desc", f.desc);
							end
							if f.required == true then
								form:tag("required"):up();
							end
							if type(f.value) == "string" then
								form:text_tag("value", f.value);
							elseif type(f.value) == "table" then
								for _, v in ipairs(f.value) do
									form:text_tag("value", v);
								end
							end
							if type(f.options) == "table" then
								for _, o in ipairs(f.value) do
									if type(o) == "table" then
										form:tag("option", { label = o.label });
										form:text_tag("value", o.value);
										form:up();
									end
								end
							end
						end
					end
				end
				return form;
			end
		end;
	};

	-- Simpler mapping of dataform from JSON map
	formdata = { type = "func", xmlns = "jabber:x:data", tagname = "",
		st2json = function (s)
			local r = {};
			for field in s:childtags("field") do
				if field.attr.var then
					local values = array();
					for value in field:childtags("value") do
						values:push(value:get_text());
					end
					if field.attr.type == "list-single" or field.attr.type == "list-multi" then
						r[field.attr.var] = values;
					elseif field.attr.type == "text-multi" then
						r[field.attr.var] = values:concat("\n");
					elseif field.attr.type == "boolean" then
						r[field.attr.var] = values[1] == "1" or values[1] == "true";
					elseif field.attr.type then
						r[field.attr.var] = values[1] or json.null;
					else -- type is optional, no way to know if multiple or single value is expected
						r[field.attr.var] = values;
					end
				end
			end
			return r;
		end,
		json2st = function (s, t)
			local form = st.stanza("x", { xmlns = "jabber:x:data", type = t });
			for k, v in pairs(s) do
				form:tag("field", { var = k });
				if type(v) == "string" then
					form:text_tag("value", v);
				elseif type(v) == "table" then
					for _, v_ in ipairs(v) do
						form:text_tag("value", v_);
					end
				end
				form:up();
			end
			return form;
		end
	};

};

local byxmlname = {};
for k, spec in pairs(field_mappings) do
	for _, replace in pairs(schema.properties) do
		replace.properties[k] = nil
	end

	if type(spec) == "table" then
		spec.key = k;
		if spec.xmlns and spec.tagname then
			byxmlname["{" .. spec.xmlns .. "}" .. spec.tagname] = spec;
		elseif spec.type == "name" then
			byxmlname["{" .. spec.xmlns .. "}"] = spec;
		end
	elseif type(spec) == "string" then
		byxmlname["{jabber:client}" .. k] = {key = k; type = spec};
	end
end

local implied_kinds = {
	disco = "iq",
	items = "iq",
	ping = "iq",
	version = "iq",
	command = "iq",
	archive = "iq",

	body = "message",
	html = "message",
	replace = "message",
	state = "message",
	subject = "message",
	thread = "message",

	join = "presence",
	priority = "presence",
	show = "presence",
	status = "presence",
}

local implied_types = {
	command = "set",
	archive = "set",
}

local kind_by_type = {
	get = "iq", set = "iq", result = "iq",
	normal = "message", chat = "message", headline = "message", groupchat = "message",
	available = "presence", unavailable = "presence",
	subscribe = "presence", unsubscribe = "presence",
	subscribed = "presence", unsubscribed = "presence",
}

local function st2json(s)
	if s.name == "xmpp" then
		local result = array();
		for child in s:childtags() do
			result:push(st2json(child));
		end
		return { xmpp = result };
	end

	local t;
	do
		local wrap_s = st.stanza("xmpp", { xmlns = "jabber:client" }):add_child(s);
		local wrap_t = map.parse(schema, wrap_s);
		if not wrap_t then
			return nil, "parse";
		end
		local kind;
		kind, t = next(wrap_t);
		if kind == nil then
			return nil, "parse";
		end
		t.kind = kind;
	end

	if s.name == "presence" and not s.attr.type then
		t.type = "available";
	end

	if t.to then
		t.to = jid.prep(t.to);
		if not t.to then return nil, "invalid-jid-to"; end
	end
	if t.from then
		t.from = jid.prep(t.from);
		if not t.from then return nil, "invalid-jid-from"; end
	end

	if t.type == "error" then
		local error = s:get_child("error");
		local err_typ, err_condition, err_text = s:get_error();
		t.error = {
			type = err_typ,
			condition = err_condition,
			text = err_text,
			by = error and error.attr.by or nil,
		};
		return t;
	end

	if type(t.payload) == "table" then
		if type(t.payload.data) == "string" then
			local data, err = json.decode(t.payload.data);
			if err then
				return nil, err;
			else
				t.payload.data = data;
			end
		else
			return nil, "invalid payload.data";
		end
	end

	for _, tag in ipairs(s.tags) do
		local prefix = "{" .. (tag.attr.xmlns or "jabber:client") .. "}";
		local mapping = byxmlname[prefix .. tag.name];
		if not mapping then
			mapping = byxmlname[prefix];
		end

		if mapping and mapping.type == "func" and mapping.st2json then
			t[mapping.key] = mapping.st2json(tag);
		end
	end

	return t;
end

local function str(s)
	if type(s) == "string" then
		return s;
	end
end

local function json2st(t)
	if type(t) ~= "table" or not str(next(t)) then
		return nil, "invalid-json";
	end
	local t_type = str(t.type);
	if t_type == nil then
		for k, implied in pairs(implied_types) do
			if t[k] then
				t_type = implied;
				break;
			end
		end
	end
	local kind = str(t.kind) or kind_by_type[t_type];
	if not kind then
		for k, implied in pairs(implied_kinds) do
			if t[k] then
				kind = implied;
				break
			end
		end
	end

	if kind == "presence" and t_type == "available" then
		t_type = nil;
	elseif kind == "iq" and not t_type then
		t_type = "get";
	end
	if not schema.properties[kind or "message"] then
		return nil, "unknown-kind";
	end

	-- XEP-0313 conveninece mapping
	if kind == "iq" and t_type == "set" and type(t.archive) == "table" and not t.archive.form then
		local archive = t.archive;
		if archive["with"] or archive["start"] or archive["end"] or archive["before-id"] or archive["after-id"]
			or archive["ids"] then
			if type(archive["ids"]) == "string" then
				local ids = {};
				for id in archive["ids"]:gmatch("[^,]+") do
					table.insert(ids, id);
				end
				archive["ids"] = ids;
			end
			archive.form = {
				type = "submit";
				fields = {
					{ var = "FORM_TYPE"; values = { "urn:xmpp:mam:2" } };
					{ var = "with"; values = { archive["with"] } };
					{ var = "start"; values = { archive["start"] } };
					{ var = "end"; values = { archive["end"] } };
					{ var = "before-id"; values = { archive["before-id"] } };
					{ var = "after-id"; values = { archive["after-id"] } };
					{ var = "ids"; values = archive["ids"] };
				};
			};
			archive["with"] = nil;
			archive["start"] = nil;
			archive["end"] = nil;
			archive["before-id"] = nil;
			archive["after-id"] = nil;
			archive["ids"] = nil;
		end

		if archive["after"] or archive["before"] or archive["max"] then
			archive.page = { after = archive["after"]; before = archive["before"]; max = tonumber(archive["max"]) }
			archive["after"] = nil;
			archive["before"] = nil;
			archive["max"] = nil;
		end
	end

	if type(t.payload) == "table" then
		t.payload.data = json.encode(t.payload.data);
	end

	if type(t.upload_request) == "table" and type(t.upload_request.size) == "string" then
		-- When using GET /rest/upload_request then the arguments from the query are all strings
		t.upload_request.size = tonumber(t.upload_request.size);
	end


	if kind == "presence" and t.join == true and t.muc == nil then
		-- COMPAT Older boolean 'join' property used with XEP-0045
		t.muc = {};
	end

	local s = map.unparse(schema, { [kind or "message"] = t }).tags[1];

	s.attr.type = t_type;
	s.attr.to = str(t.to) and jid.prep(t.to);
	s.attr.from = str(t.to) and jid.prep(t.from);

	if type(t.error) == "table" then
		return st.error_reply(st.reply(s), str(t.error.type), str(t.error.condition), str(t.error.text), str(t.error.by));
	elseif t.type == "error" then
		s:text_tag("error", t.body, { code = t.error_code and tostring(t.error_code) });
		return s;
	end

	for k, v in pairs(t) do
		local mapping = field_mappings[k];
		if mapping and mapping.type == "func" and mapping.json2st then
			s:add_child(mapping.json2st(v)):up();
		end
	end

	s:reset();

	return s;
end

return {
	st2json = st2json;
	json2st = json2st;
};
