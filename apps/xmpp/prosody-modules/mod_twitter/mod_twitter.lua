-- for Prosody
-- via dersd

if module:get_host_type() ~= "component" then
	error(module.name.." should be loaded as a component, check out http://prosody.im/doc/components", 0);
end

local jid_split = require "util.jid".split;
local st = require "util.stanza";
local componentmanager = require "core.componentmanager";
local datamanager = require "util.datamanager";
local timer = require "util.timer";
local http = require "net.http";
local json = require "util.json";
local base64 = require "util.encodings".base64;

local component_host = module:get_host();
local component_name = module.name;
local data_cache = {};

function print_r(obj)
	return require("util.serialization").serialize(obj);
end

function dmsg(jid, msg)
	module:log("debug", msg or "nil");
	if jid ~= nil then
		module:send(st.message({to=jid, from=component_host, type='chat'}, msg or "nil"));
	end
end

function substring(string, start_string, ending_string)
	local s_value_start, s_value_finish = nil, nil;
	if start_string ~= nil then
		_, s_value_start = string:find(start_string);
		if s_value_start == nil then
			-- error
			return nil;
		end
	else
		return nil;
	end
	if ending_string ~= nil then
		_, s_value_finish = string:find(ending_string, s_value_start+1);
		if s_value_finish == nil then
			-- error
			return nil;
		end
	else
		s_value_finish = string:len()+1;
	end
	return string:sub(s_value_start+1, s_value_finish-1);
end

local http_timeout = 30;
local http_queue = setmetatable({}, { __mode = "k" }); -- auto-cleaning nil elements
data_cache['prosody_os'] = prosody.platform;
data_cache['prosody_version'] = prosody.version;
local http_headers = {
	["User-Agent"] = "Prosody ("..data_cache['prosody_version'].."; "..data_cache['prosody_os']..")" --"ELinks (0.4pre5; Linux 2.4.27 i686; 80x25)",
};

function http_action_callback(response, code, request, xcallback)
	if http_queue == nil or http_queue[request] == nil then return; end
	local id = http_queue[request];
	http_queue[request] = nil;
	if xcallback == nil then
		dmsg(nil, "http_action_callback reports that xcallback is nil");
	else
		xcallback(id, response, request);
	end
	return true;
end

function http_add_action(tid, url, method, post, fcallback)
	local request = http.request(url, { headers = http_headers or {}, body = http.formencode(post or {}), method = method or "GET" }, function(response_body, code, response, request) http_action_callback(response_body, code, request, fcallback) end);
	http_queue[request] = tid;
	timer.add_task(http_timeout, function() http.destroy_request(request); end);
	return true;
end

local users = setmetatable({}, {__mode="k"});
local user = {};
user.__index = user;
user.dosync = false;
user.valid = false;
user.data = {};

function user:login()
	userdata = datamanager.load(self.jid, component_host, "data");
	if userdata ~= nil then
		self.data = userdata;
		if self.data['_twitter_sess'] ~= nil then
			http_headers['Cookie'] = "_twitter_sess="..self.data['_twitter_sess']..";";
		end
		module:send(st.presence({to=self.jid, from=component_host}));
		self:twitterAction("VerifyCredentials");
		if self.data.dosync == 1 then
			self.dosync = true;
			timer.add_task(self.data.refreshrate, function() return users[self.jid]:sync(); end)
		end
	else
		module:send(st.message({to=self.jid, from=component_host, type='chat'}, "You are not signed in."));
	end
end

function user:logout()
	datamanager.store(self.jid, component_host, "data", self.data);
	self.dosync = false;
	module:send(st.presence({to=self.jid, from=component_host, type='unavailable'}));
end

function user:sync()
	if self.dosync then
		table.foreach(self.data.synclines, function(ind, line) self:twitterAction(line.name, {sinceid=line.sinceid}) end);
		return self.data.refreshrate;
	end
end

function user:signin()
	if datamanager.load(self.jid, component_host, "data") == nil then
		datamanager.store(self.jid, component_host, "data", {login=self.data.login, password=self.data.password, refreshrate=60, dosync=1, synclines={{name='HomeTimeline', sinceid=0}}, syncstatus=0})
		module:send(st.presence{to=self.jid, from=component_host, type='subscribe'});
		module:send(st.presence{to=self.jid, from=component_host, type='subscribed'});
	end
end

function user:signout()
	if datamanager.load(self.jid, component_host, "data") ~= nil then
		datamanager.store(self.jid, component_host, "data", nil);
		module:send(st.presence({to=self.jid, from=component_host, type='unavailable'}));
		module:send(st.presence({to=self.jid, from=component_host, type='unsubscribe'}));
		module:send(st.presence({to=self.jid, from=component_host, type='unsubscribed'}));
	end
end

local twitterApiUrl = "http://api.twitter.com";
local twitterApiVersion = "1";
local twitterApiDataType = "json";
local twitterActionUrl = function(action) return twitterApiUrl.."/"..twitterApiVersion.."/"..action.."."..twitterApiDataType end;
local twitterActionMap = {
	PublicTimeline = {
		url = twitterActionUrl("statuses/public_timeline"),
		method = "GET",
		needauth = false,
	},
	HomeTimeline = {
		url = twitterActionUrl("statuses/home_timeline"),
		method = "GET",
		needauth = true,
	},
	FriendsTimeline = {
		url = twitterActionUrl("statuses/friends_timeline"),
		method = "GET",
		needauth = true,
	},
	UserTimeline = {
		url = twitterActionUrl("statuses/friends_timeline"),
		method = "GET",
		needauth = true,
	},
	VerifyCredentials = {
		url = twitterActionUrl("account/verify_credentials"),
		method = "GET",
		needauth = true,
	},
	UpdateStatus = {
		url = twitterActionUrl("statuses/update"),
		method = "POST",
		needauth = true,
	},
	Retweet = {
		url = twitterActionUrl("statuses/retweet/%tweetid"),
		method = "POST",
		needauth = true,
	}
}

function user:twitterAction(line, params)
	local action = twitterActionMap[line];
	if action then
		local url = action.url;
		local post = {};
		--if action.needauth and not self.valid and line ~= "VerifyCredentials" then
		--	return
		--end
		if action.needauth then
			http_headers['Authorization'] = "Basic "..base64.encode(self.data.login..":"..self.data.password);
			--url = string.gsub(url, "http\:\/\/", string.format("http://%s:%s@", self.data.login, self.data.password));
		end
		if params and type(params) == "table" then
			post = params;
		end
		if action.method == "GET" and post ~= {} then
			url = url.."?"..http.formencode(post);
		end
		http_add_action(line, url, action.method, post, function(...) self:twitterActionResult(...) end);
	else
		module:send(st.message({to=self.jid, from=component_host, type='chat'}, "Wrong twitter action!"));
	end
end

local twitterActionResultMap = {
	PublicTimeline = {exec=function(jid, response)
		--module:send(st.message({to=jid, from=component_host, type='chat'}, print_r(response)));
		return
	end},
	HomeTimeline = {exec=function(jid, response)
		--module:send(st.message({to=jid, from=component_host, type='chat'}, print_r(response)));
		return
	end},
	FriendsTimeline = {function(jid, response)
		return
	end},
	UserTimeline = {exec=function(jid, response)
		return
	end},
	VerifyCredentials = {exec=function(jid, response)
		if response ~= nil and response.id ~= nil then
			users[jid].valid = true;
			users[jid].id = response.id;
		end
		return
	end},
	UpdateStatus = {exec=function(jid, response)
		return
	end},
	Retweet = {exec=function(jid, response)
		return
	end}
}

function user:twitterActionResult(id, response, request)
	if request ~= nil and request.responseheaders['set-cookie'] ~= nil and request.responseheaders['location'] ~= nil then
		--self.data['_twitter_sess'] = substring(request.responseheaders['set-cookie'], "_twitter_sess=", ";");
		--http_add_action(id, request.responseheaders['location'], "GET", {}, function(...) self:twitterActionResult(...) end);
		return true;
	end
	local result, tmp_json = pcall(function() json.decode(response or "{}") end);
	if result and id ~= nil then
		twitterActionResultMap[id]:exec(self.jid, tmp_json);
	end
	return true;
end

function iq_success(event)
	local origin, stanza = event.origin, event.stanza;
	local reply = data_cache.success;
	if reply == nil then
		reply = st.iq({type='result', from=stanza.attr.to or component_host});
		data_cache.success = reply;
	end
	reply.attr.id = stanza.attr.id;
	reply.attr.to = stanza.attr.from;
	origin.send(reply);
	return true;
end

function iq_disco_info(event)
	local origin, stanza = event.origin, event.stanza;
	local from = {};
	from.node, from.host, from.resource = jid_split(stanza.attr.from);
	local bjid = from.node.."@"..from.host;
	local reply = data_cache.disco_info;
	if reply == nil then
		reply = st.iq({type='result', from=stanza.attr.to or component_host}):query("http://jabber.org/protocol/disco#info")
				:tag("identity", {category='gateway', type='chat', name=component_name}):up();
		reply = reply:tag("feature", {var="urn:xmpp:receipts"}):up();
        reply = reply:tag("feature", {var="http://jabber.org/protocol/commands"}):up();
        reply = reply:tag("feature", {var="jabber:iq:register"}):up();
 		--reply = reply:tag("feature", {var="jabber:iq:time"}):up();
		--reply = reply:tag("feature", {var="jabber:iq:version"}):up();
        --reply = reply:tag("feature", {var="http://jabber.org/protocol/stats"}):up();
		data_cache.disco_info = reply;
	end
	reply.attr.id = stanza.attr.id;
	reply.attr.to = stanza.attr.from;
	origin.send(reply);
	return true;
end

function iq_disco_items(event)
	local origin, stanza = event.origin, event.stanza;
	local reply = data_cache.disco_items;
 	if reply == nil then
		reply = st.iq({type='result', from=stanza.attr.to or component_host}):query("http://jabber.org/protocol/disco#items");
		data_cache.disco_items = reply;
	end
	reply.attr.id = stanza.attr.id;
	reply.attr.to = stanza.attr.from;
	origin.send(reply);
	return true;
end

function iq_register(event)
	local origin, stanza = event.origin, event.stanza;
	if stanza.attr.type == "get" then
		local reply = data_cache.registration_form;
		if reply == nil then
			reply = st.iq({type='result', from=stanza.attr.to or component_host})
					:tag("query", { xmlns="jabber:iq:register" })
					:tag("instructions"):text("Enter your twitter data"):up()
					:tag("username"):up()
					:tag("password"):up();
			data_cache.registration_form = reply
		end
		reply.attr.id = stanza.attr.id;
		reply.attr.to = stanza.attr.from;
		origin.send(reply);
	elseif stanza.attr.type == "set" then
		local from = {};
		from.node, from.host, from.resource = jid_split(stanza.attr.from);
		local bjid = from.node.."@"..from.host;
		local username, password = "", "";
		local reply;
		for _, tag in ipairs(stanza.tags[1].tags) do
			if tag.name == "remove" then
				users[bjid]:signout();
				iq_success(event);
				return true;
			end
			if tag.name == "username" then
				username = tag[1];
			end
			if tag.name == "password" then
				password = tag[1];
			end
		end
		if username ~= nil and password ~= nil then
			users[bjid] = setmetatable({}, user);
			users[bjid].jid = bjid;
			users[bjid].data.login = username;
			users[bjid].data.password = password;
			users[bjid]:signin();
			users[bjid]:login();
		end
		iq_success(event);
		return true;
	end
end

function presence_stanza_handler(event)
	local origin, stanza = event.origin, event.stanza;
	local to = {};
	local from = {};
	local pres = {};
	to.node, to.host, to.resource = jid_split(stanza.attr.to);
	from.node, from.host, from.resource = jid_split(stanza.attr.from);
	pres.type = stanza.attr.type;
	for _, tag in ipairs(stanza.tags) do pres[tag.name] = tag[1]; end
	local from_bjid = nil;
	if from.node ~= nil and from.host ~= nil then
		from_bjid = from.node.."@"..from.host;
	elseif from.host ~= nil then
		from_bjid = from.host;
	end
	if pres.type == nil then
		if users[from_bjid] ~= nil then
			-- Status change
			if pres['status'] ~= nil and users[from_bjid]['data']['sync_status'] then
				users[from_bjid]:twitterAction("UpdateStatus", {status=pres['status']});
			end
		else
			-- User login request
			users[from_bjid] = setmetatable({}, user);
			users[from_bjid].jid = from_bjid;
			users[from_bjid]:login();
		end
		origin.send(st.presence({to=from_bjid, from=component_host}));
	elseif pres.type == 'subscribe' and users[from_bjid] ~= nil then
		origin.send(st.presence{to=from_bjid, from=component_host, type='subscribed'});
	elseif pres.type == 'unsubscribed' and users[from_bjid] ~= nil then
		users[from_bjid]:logout();
		users[from_bjid]:signout();
		users[from_bjid] = nil;
	elseif pres.type == 'unavailable' and users[from_bjid] ~= nil then
		users[from_bjid]:logout();
		users[from_bjid] = nil;
	end
	return true;
end

function confirm_message_delivery(event)
	local reply = st.message({id=event.stanza.attr.id, to=event.stanza.attr.from, from=event.stanza.attr.to or component_host}):tag("received", {xmlns = "urn:xmpp:receipts"});
	origin.send(reply);
	return true;
end

function message_stanza_handler(event)
	local origin, stanza = event.origin, event.stanza;
	local to = {};
	local from = {};
	local msg = {};
	to.node, to.host, to.resource = jid_split(stanza.attr.to);
	from.node, from.host, from.resource = jid_split(stanza.attr.from);
	local bjid = nil;
	if from.node ~= nil and from.host ~= nil then
		from_bjid = from.node.."@"..from.host;
	elseif from.host ~= nil then
		from_bjid = from.host;
	end
	local to_bjid = nil;
	if to.node ~= nil and to.host ~= nil then
		to_bjid = to.node.."@"..to.host;
	elseif to.host ~= nil then
		to_bjid = to.host;
	end
	for _, tag in ipairs(stanza.tags) do
		msg[tag.name] = tag[1];
		if tag.attr.xmlns == "urn:xmpp:receipts" then
			confirm_message_delivery({origin=origin, stanza=stanza});
		end
		-- can handle more xmlns
	end
	-- Now parse the message
	if stanza.attr.to == component_host then
		if msg.body == "!myinfo" then
			if users[from_bjid] ~= nil then
				origin.send(st.message({to=stanza.attr.from, from=component_host, type='chat'}, print_r(users[from_bjid])));
			end
		end
		-- Other messages go to twitter
		user:twitterAction("UpdateStatus", {status=msg.body});
	else
		-- Message to uid@host/resource
	end
	return true;
end

module:hook("presence/host", presence_stanza_handler);
module:hook("message/host", message_stanza_handler);

module:hook("iq/host/jabber:iq:register:query", iq_register);
module:hook("iq/host/http://jabber.org/protocol/disco#info:query", iq_disco_info);
module:hook("iq/host/http://jabber.org/protocol/disco#items:query", iq_disco_items);
module:hook("iq/host", function(data)
	-- IQ to a local host recieved
	local origin, stanza = data.origin, data.stanza;
	if stanza.attr.type == "get" or stanza.attr.type == "set" then
		return module:fire_event("iq/host/"..stanza.tags[1].attr.xmlns..":"..stanza.tags[1].name, data);
	else
		module:fire_event("iq/host/"..stanza.attr.id, data);
		return true;
	end
end);

module.unload = function()
	componentmanager.deregister_component(component_host);
end
component = componentmanager.register_component(component_host, function() return; end);
