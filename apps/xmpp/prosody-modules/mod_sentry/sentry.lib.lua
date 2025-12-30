local array = require "util.array";
local hex = require "util.hex";
local random = require "util.random";
local url = require "socket.url";
local datetime = require "util.datetime".datetime;
local http = require 'net.http'
local json = require "util.json";
local errors = require "util.error";
local promise = require "util.promise";

local unpack = unpack or table.unpack -- luacheck: ignore

local user_agent = ("prosody-mod-%s/%s"):format((module.name:gsub("%W", "-")), (prosody.version:gsub("[^%w.-]", "-")));

local function generate_event_id()
	return hex.to(random.bytes(16));
end

local function get_endpoint(server, name)
	return ("%s/api/%d/%s/"):format(server.base_uri, server.project_id, name);
end

-- Parse a DSN string
-- https://develop.sentry.dev/sdk/overview/#parsing-the-dsn
local function parse_dsn(dsn_string)
	local parsed = url.parse(dsn_string);
	if not parsed then
		return nil, "unable to parse dsn (url)";
	end
	local path, project_id = parsed.path:match("^(.*)/(%d+)$");
	if not path then
		return nil, "unable to parse dsn (path)";
	end
	local base_uri = url.build({
		scheme = parsed.scheme;
		host = parsed.host;
		port = parsed.port;
		path = path;
	});
	return {
		base_uri = base_uri;
		public_key = parsed.user;
		project_id = project_id;
	};
end

local function get_error_data(instance_id, context)
	local data = {
		instance_id = instance_id;
	};
	for k, v in pairs(context) do
		if k ~= "traceback" then
			data[k] = tostring(v);
		end
	end
	return data;
end

local function error_to_sentry_exception(e)
	local exception = {
		type = e.condition or (e.code and tostring(e.code)) or nil;
		value = e.text or tostring(e);
		context = e.source;
		mechanism = {
			type = "generic";
			description = "Prosody error object";
			synthetic = not not e.context.wrapped_error;
			data = get_error_data(e.instance_id, e.context);
		};
	};
	local traceback = e.context.traceback;
	if traceback and type(traceback) == "table" then
		local frames = array();
		for i = #traceback, 1, -1 do
			local frame = traceback[i];
			table.insert(frames, {
				["function"] = frame.info.name;
				filename = frame.info.short_src;
				lineno = frame.info.currentline;
			});
		end
		exception.stacktrace = {
			frames = frames;
		};
	end
	return exception;
end

local sentry_event_methods = {};
local sentry_event_mt = { __index = sentry_event_methods };

function sentry_event_methods:set(key, value)
	self.event[key] = value;
	return self;
end

function sentry_event_methods:tag(tag_name, tag_value)
	local tags = self.event.tags;
	if not tags then
		tags = {};
		self.event.tags = tags;
	end
	if type(tag_name) == "string" then
		tags[tag_name] = tag_value;
	else
		for k, v in pairs(tag_name) do
			tags[k] = v;
		end
	end
	return self;
end

function sentry_event_methods:extra(key, value)
	local extra = self.event.extra;
	if not extra then
		extra = {};
		self.event.extra = extra;
	end
	if type(key) == "string" then
		extra[key] = tostring(value);
	else
		for k, v in pairs(key) do
			extra[k] = tostring(v);
		end
	end
	return self;
end

function sentry_event_methods:message(text)
	return self:set("message", { formatted = text });
end

function sentry_event_methods:add_exception(e)
	if errors.is_err(e) then
		if not self.event.message then
			if e.text then
				self:message(e.text);
			elseif type(e.context.wrapped_error) == "string" then
				self:message(e.context.wrapped_error);
			end
		end
		e = error_to_sentry_exception(e);
	elseif type(e) ~= "table" or not (e.type and e.value) then
		e = error_to_sentry_exception(errors.coerce(nil, e));
	end

	local exception = self.event.exception;
	if not exception or not exception.values then
		exception = { values = {} };
		self.event.exception = exception;
	end

	table.insert(exception.values, e);

	return self;
end

function sentry_event_methods:add_breadcrumb(crumb_timestamp, crumb_type, crumb_category, message, data)
	local crumbs = self.event.breadcrumbs;
	if not crumbs then
		crumbs = { values = {} };
		self.event.breadcrumbs = crumbs;
	end

	local crumb = {
		timestamp = crumb_timestamp and datetime(crumb_timestamp) or self.timestamp;
		type = crumb_type;
		category = crumb_category;
		message = message;
		data = data;
	};
	table.insert(crumbs.values, crumb);
	return self;
end

function sentry_event_methods:add_http_request_breadcrumb(http_request, message)
	local request_id_message = ("[Request %s]"):format(http_request.id);
	message = message and (request_id_message.." "..message) or request_id_message;
	return self:add_breadcrumb(http_request.time, "http", "net.http", message, {
		url = http_request.url;
		method = http_request.method or "GET";
		status_code = http_request.response and http_request.response.code or nil;
	});
end

function sentry_event_methods:set_request(http_request)
	return self:set("request", {
		method = http_request.method;
		url = url.build(http_request.url);
		headers = http_request.headers;
		env = {
			REMOTE_ADDR = http_request.ip;
		};
	});
end

function sentry_event_methods:send()
	return self.server:send(self.event);
end

local sentry_mt = { }
sentry_mt.__index = sentry_mt

local function new(conf)
	local server = assert(parse_dsn(conf.dsn));
	return setmetatable({
		server = server;
		endpoints = {
			store = get_endpoint(server, "store");
		};
		insecure = conf.insecure;
		tags = conf.tags or nil,
		extra = conf.extra or nil,
		server_name = conf.server_name or "undefined";
		logger = conf.logger;
	}, sentry_mt);
end

local function resolve_sentry_response(response)
	if response.code == 200 and response.body then
		local data = json.decode(response.body);
		return data;
	end
	module:log("warn", "Unexpected response from server: %d: %s", response.code, response.body);
	return promise.reject(response);
end

function sentry_mt:send(event)
	local json_payload = json.encode(event);
	local response_promise, err = self:_request(self.endpoints.store, "application/json", json_payload);

	if not response_promise then
		module:log("warn", "Failed to submit to Sentry: %s %s", err, json);
		return nil, err;
	end

	return response_promise:next(resolve_sentry_response), event.event_id;
end

function sentry_mt:_request(endpoint_url, body_type, body)
	local auth_header = ("Sentry sentry_version=7, sentry_client=%s, sentry_timestamp=%s, sentry_key=%s")
		:format(user_agent, datetime(), self.server.public_key);

	return http.request(endpoint_url, {
		headers = {
			["X-Sentry-Auth"] = auth_header;
			["Content-Type"] = body_type;
			["User-Agent"] = user_agent;
		};
		insecure = self.insecure;
		body = body;
	});
end

function sentry_mt:event(level, source)
	local event = setmetatable({
		server = self;
		event = {
			event_id = generate_event_id();
			timestamp = datetime();
			platform = "lua";
			server_name = self.server_name;
			logger = source or self.logger;
			level = level;
		};
	}, sentry_event_mt);
	if self.tags then
		event:tag(self.tags);
	end
	if self.extra then
		event:extra(self.extra);
	end
	return event;
end

return {
	new = new;
};
