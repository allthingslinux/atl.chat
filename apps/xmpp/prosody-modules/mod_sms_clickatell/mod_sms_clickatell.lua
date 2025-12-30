-- mod_sms_clickatell
--
-- A Prosody module for sending SMS text messages from XMPP using the
-- Clickatell gateway's HTTP API
--
-- Hacked from mod_twitter by Phil Stewart, March 2011. Anything from
-- mod_twitter copyright The Guy Who Wrote mod_twitter. Everything else
-- copyright 2011 Phil Stewart. Licensed under the same terms as Prosody
-- (MIT license, as per below)
--
--[[
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
--]]

-- Raise an error if the modules hasn't been loaded as a component in prosody's config
if module:get_host_type() ~= "component" then
	error(module.name.." should be loaded as a component, check out http://prosody.im/doc/components", 0);
end

local jid_split = require "util.jid".split;
local st = require "util.stanza";
local datamanager = require "util.datamanager";
local timer = require "util.timer";
local config_get = require "core.configmanager".get;
local http = require "net.http";
local base64 = require "util.encodings".base64;
local serialize = require "util.serialization".serialize;
local pairs, ipairs = pairs, ipairs;
local setmetatable = setmetatable;

local component_host = module:get_host();
local component_name = module.name;
local data_cache = {};

--local clickatell_api_id = module:get_option_string("clickatell_api_id");
local sms_message_prefix = module:get_option_string("sms_message_prefix") or "";
--local sms_source_number = module:get_option_string("sms_source_number") or "";

--local users = setmetatable({}, {__mode="k"});

-- User data is held in smsuser objects
local smsuser = {};
smsuser.__index = smsuser;

-- Users table is used to store user data in the form of smsuser objects.
-- It is indexed by the base jid of the user, so when a non-extant entry in the
-- table is referenced, we pass the jid to smsuser:register to load the user
local users = {};
setmetatable(users, { __index =	function (table, key)
					return smsuser:register(key);
				end });

-- Create a new smsuser object
function smsuser:new()
	newuser = {};
	setmetatable(newuser, self);
	return newuser;
end

-- Store (save) the user object
function smsuser:store()
	datamanager.store(self.jid, component_host, "data", self.data);
end

-- For debug
function smsuser:logjid()
	module:log("logjid: ", self.jid);
end

-- Register a user against the base jid of the client. If a user entry for the
-- bjid is already stored in the Prosody data manager, retrieve its data
function smsuser:register(bjid)
	reguser = smsuser:new();
	reguser.jid = bjid;
	reguser.data = datamanager.load(bjid, component_host, "data") or {};
	return reguser;
end

-- Add a roster entry for the user
-- SMS users must me of the form number@component_host
function smsuser:roster_add(sms_number)
	if self.data.roster == nil then
		self.data.roster = {}
	end
	if self.data.roster[sms_number] == nil then
		self.data.roster[sms_number] = {screen_name=sms_number, subscription=nil};
	end
	self:store();
end

-- Update the roster entry of sms_number with new screen name
function smsuser:roster_update_screen_name(sms_number, screen_name)
	if self.data.roster[sms_number] == nil then
		smsuser:roster_add(sms_number);
	end
	self.data.roster[sms_number].screen_name = screen_name;
	self:store();
end

-- Update the roster entry of sms_number with new subscription detail
function smsuser:roster_update_subscription(sms_number, subscription)
	if self.data.roster[sms_number] == nil then
		smsuser:roster_add(sms_number);
	end
	self.data.roster[sms_number].subscription = subscription;
	self:store();
end

-- Delete an entry from the roster
function smsuser:roster_delete(sms_number)
	self.data.roster[sms_number] = nil;
	self:store();
end

--
function smsuser:roster_stanza_args(sms_number)
	if self.data.roster[sms_number] == nil then
		return nil
	end
	local args = {jid=sms_number.."@"..component_host, name=self.data.roster[sms_number].screen_name}
	if self.data.roster[sms_number].subscription ~= nil then
		args.subscription = self.data.roster[sms_number].subscription
	end
	return args
end

--[[ From mod_twitter, keeping 'cos I might use it later :-)
function send_stanza(stanza)
	if stanza ~= nil then
		core_route_stanza(prosody.hosts[component_host], stanza)
	end
end

function dmsg(jid, msg)
	module:log("debug", msg or "nil");
	if jid ~= nil then
		send_stanza(st.message({to=jid, from=component_host, type='chat'}, msg or "nil"));
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
--]]

local http_timeout = 30;
local http_queue = setmetatable({}, { __mode = "k" }); -- auto-cleaning nil elements
data_cache['prosody_os'] = prosody.platform;
data_cache['prosody_version'] = prosody.version;
local http_headers = {
	["user-Agent"] = "Prosody ("..data_cache['prosody_version'].."; "..data_cache['prosody_os']..")" --"ELinks (0.4pre5; Linux 2.4.27 i686; 80x25)",
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
	local request = http.request(url, { headers = http_headers or {}, body = "", method = method or "GET" }, function(response_body, code, response, request) http_action_callback(response_body, code, request, fcallback) end);
	http_queue[request] = tid;
	timer.add_task(http_timeout, function() http.destroy_request(request); end);
	return true;
end

-- Clickatell SMS HTTP API interaction function
function clickatell_send_sms(user, number, message)
	module.log("info", "Clickatell API interaction function triggered");
	-- Don't attempt to send an SMS with a null or empty message
	if message == nil or message == "" then
		return false;
	end

	local sms_message = sms_message_prefix..message;
	local clickatell_base_url = "https://api.clickatell.com/http/sendmsg";
	local params = {user=user.data.username, password=user.data.password, api_id=user.data.api_id, from=user.data.source_number, to=number, text=sms_message};
	local query_string = "";

	for param, data in pairs(params) do
		--module:log("info", "Inside query constructor: "..param..data);
		if query_string ~= "" then
			query_string = query_string.."&";
		end
		query_string = query_string..param.."="..http.urlencode(data);
	end
	local url = clickatell_base_url.."?"..query_string;
	module:log("info", "Clickatell SMS URL: "..url);
	http_add_action(message, url, "GET", params, nil);
	return true;
end

function iq_success(origin, stanza)
	local reply = data_cache.success;
	if reply == nil then
		reply = st.reply(stanza);
		data_cache.success = reply;
	end
	reply.attr.id = stanza.attr.id;
	reply.attr.to = stanza.attr.from;
	origin.send(reply);
	return true;
end

-- XMPP Service Discovery (disco) info callback
-- When a disco info query comes in, returns the identity and feature
-- information as per XEP-0030
function iq_disco_info(stanza)
	module:log("info", "Disco info triggered");
	local from = {};
	from.node, from.host, from.resource = jid_split(stanza.attr.from);
	local bjid = from.node.."@"..from.host;
	local reply = data_cache.disco_info;
	if reply == nil then
		--reply = st.iq({type='result', from=stanza.attr.to or component_host}):query("http://jabber.org/protocol/disco#info");
		reply = st.reply(stanza):query("http://jabber.org/protocol/disco#info");
		reply:tag("identity", {category='gateway', type='sms', name=component_name}):up();
		reply:tag("feature", {var="urn:xmpp:receipts"}):up();
		reply:tag("feature", {var="jabber:iq:register"}):up();
		reply:tag("feature", {var="http://jabber.org/protocol/rosterx"}):up();
		--reply = reply:tag("feature", {var="http://jabber.org/protocol/commands"}):up();
 		--reply = reply:tag("feature", {var="jabber:iq:time"}):up();
		--reply = reply:tag("feature", {var="jabber:iq:version"}):up();
		data_cache.disco_info = reply;
	end
	reply.attr.id = stanza.attr.id;
	reply.attr.to = stanza.attr.from;
	return reply;
end

-- XMPP Service Discovery (disco) items callback
-- When a disco info query comes in, returns the items
-- information as per XEP-0030
-- (Nothing much happening here at the moment)
--[[
function iq_disco_items(stanza)
	module:log("info", "Disco items triggered");
	local reply = data_cache.disco_items;
 	if reply == nil then
		reply = st.iq({type='result', from=stanza.attr.to or component_host}):query("http://jabber.org/protocol/disco#items")
			:tag("item", {jid='testuser'..'@'..component_host, name='SMS Test Target'}):up();
		data_cache.disco_items = reply;
	end
	reply.attr.id = stanza.attr.id;
	reply.attr.to = stanza.attr.from;
	return reply;
end
--]]

-- XMPP Register callback
-- The client must register with the gateway. In this case, the gateway is
-- Clickatell's http api, so we
function iq_register(origin, stanza)
	module:log("info", "Register event triggered");
	if stanza.attr.type == "get" then
		local reply = data_cache.registration_form;
		if reply == nil then
			reply = st.iq({type='result', from=stanza.attr.to or component_host})
				:tag("query", {xmlns="jabber:iq:register"})
				:tag("instructions"):text("Use the enclosed form to register."):up();
			reply:tag("x", {xmlns="jabber:x:data", type='form'});
			reply:tag("title"):text('SMS Gateway Registration: Clickatell'):up();
			reply:tag("instructions"):text("Enter your Clickatell username, password, API ID, and a source number for your text messages in international format (phone field)"):up();
			reply:tag("field", {type='hidden', var='FORM_TYPE'})
				:tag("value"):text('jabber:iq:register'):up():up();
			reply:tag("field", {type='text-single', label='Username', var='username'})
				:tag("required"):up():up();
			reply:tag("field", {type='text-private', label='Password', var='password'})
				:tag("required"):up():up();
			reply:tag("field", {type='text-single', label='API ID', var='api_id'})
				:tag("required"):up():up();
			reply:tag("field", {type='text-single', label='Source Number', var='source_number'})
				:tag("required"):up():up();
			data_cache.registration_form = reply;
			--module:log("info", "Register stanza to go: "..reply:pretty_print());
		end
		reply.attr.id = stanza.attr.id;
		reply.attr.to = stanza.attr.from;
		origin.send(reply);
	elseif stanza.attr.type == "set" then
		local from = {};
		from.node, from.host, from.resource = jid_split(stanza.attr.from);
		local bjid = from.node.."@"..from.host;
		local username, password, api_id, source_number = "", "", "", "";
		local reply;
		for tag in stanza.tags[1].tags[1]:childtags() do
--			if tag.name == "remove" then
--				iq_success(origin, stanza);
--				return true;
--			end
			if tag.attr.var == "username" then
				username = tag.tags[1][1];
			end
			if tag.attr.var == "password" then
				password = tag.tags[1][1];
			end
			if tag.attr.var == "api_id" then
				api_id = tag.tags[1][1];
			end
			if tag.attr.var == "source_number" then
				source_number = tag.tags[1][1];
			end
		end
		if username ~= nil and password ~= nil and api_id ~= nil then
			users[bjid] = smsuser:register(bjid);
			users[bjid].data.username = username;
			users[bjid].data.password = password;
			users[bjid].data.api_id = api_id;
			users[bjid].data.source_number = source_number;
			users[bjid]:store();
		end
		iq_success(origin, stanza);
		return true;
	end
end

-- XMPP Roster callback
-- When the client requests the roster associated with the gateway, returns
-- the users accessible via text to the client's roster
function iq_roster(stanza)
	module:log("info", "Roster request triggered");
	local from = {}
	from.node, from.host, from.resource = jid_split(stanza.attr.from);
	local from_bjid = nil;
	if from.node ~= nil and from.host ~= nil then
		from_bjid = from.node.."@"..from.host;
	elseif from.host ~= nil then
		from_bjid = from.host;
	end
	local reply = st.iq({type='result', from=stanza.attr.to or component_host}):query("")
	if users[from_bjid].data.roster ~= nil then
		for sms_number, sms_data in pairs(users[from_bjid].data.roster) do
			reply:tag("item", users[from_bjid]:roster_stanza_args(sms_number)):up();
		end
	end
	reply.attr.id = stanza.attr.id;
	reply.attr.to = stanza.attr.from;
	return reply;
end

-- Roster Exchange: iq variant
-- Sends sms targets to client's roster
function iq_roster_push(origin, stanza)
	module:log("info", "Sending Roster iq");
	local from = {}
	from.node, from.host, from.resource = jid_split(stanza.attr.from);
	local from_bjid = nil;
	if from.node ~= nil and from.host ~= nil then
		from_bjid = from.node.."@"..from.host;
	elseif from.host ~= nil then
		from_bjid = from.host;
	end
	reply = st.iq({to=stanza.attr.from, type='set'});
	reply:tag("query", {xmlns="jabber:iq:roster"});
	if users[from_bjid].data.roster ~= nil then
		for sms_number, sms_data in pairs(users[from_bjid].data.roster) do
			reply:tag("item", users[from_bjid]:roster_stanza_args(sms_number)):up();
		end
	end
	origin.send(reply);
end

-- XMPP Presence handling
function presence_stanza_handler(origin, stanza)
	module:log("info", "Presence handler triggered");
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
	local to_bjid = nil
	if to.node ~= nil and to.host ~= nil then
		to_bjid = to.node.."@"..to.host
	end

	if to.node == nil then
		-- Component presence
		-- If the client is subscribing, send a 'subscribed' presence
		if pres.type == 'subscribe' then
			origin.send(st.presence({to=from_bjid, from=component_host, type='subscribed'}));
			--origin.send(st.presence{to=from_bjid, type='subscribed'});
		end

		-- The component itself is online, so send component's presence
		origin.send(st.presence({to=from_bjid, from=component_host}));

		-- Do roster item exchange: send roster items to client
		iq_roster_push(origin, stanza);
	else
		-- SMS user presence
		if pres.type == 'subscribe' then
			users[from_bjid]:roster_add(to.node);
			origin.send(st.presence({to=from_bjid, from=to_bjid, type='subscribed'}));
		end
		if pres.type == 'unsubscribe' then
			users[from_bjid]:roster_update_subscription(to.node, 'none');
			iq_roster_push(origin, stanza);
			origin.send(st.presence({to=from_bjid, from=to_bjid, type='unsubscribed'}));
			users[from_bjid]:roster_delete(to.node)
		end
		if users[from_bjid].data.roster[to.node] ~= nil then
			origin.send(st.presence({to=from_bjid, from=to_bjid}));
		end
	end


	return true;
end

--[[ Not using this ATM
function confirm_message_delivery(event)
	local reply = st.message({id=event.stanza.attr.id, to=event.stanza.attr.from, from=event.stanza.attr.to or component_host}):tag("received", {xmlns = "urn:xmpp:receipts"});
	origin.send(reply);
	return true;
end
--]]

-- XMPP Message handler - this is the bit that Actually Does Things (TM)
-- bjid = base JID i.e. without resource identifier
function message_stanza_handler(origin, stanza)
	module:log("info", "Message handler triggered");
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

        -- This bit looks like it confirms message receipts to the client
	for _, tag in ipairs(stanza.tags) do
		msg[tag.name] = tag[1];
		if tag.attr.xmlns == "urn:xmpp:receipts" then
			confirm_message_delivery({origin=origin, stanza=stanza});
		end
		-- can handle more xmlns
	end

	-- Now parse the message
	if stanza.attr.to == component_host then
		-- Messages directly to the component jget echoed
		origin.send(st.message({to=stanza.attr.from, from=component_host, type='chat'}, msg.body));
	elseif users[from_bjid].data.roster[to.node] ~= nil then
		-- If message contains a body, send message to SMS Test User
		if msg.body ~= nil then
			clickatell_send_sms(users[from_bjid], to.node, msg.body);
		end
	end
	return true;
end
--]]

-- Component event handler
function sms_event_handler(event)
	local origin, stanza = event.origin, event.stanza;
	module:log("debug", "Received stanza: "..stanza:pretty_print());
	local to_node, to_host, to_resource = jid_split(stanza.attr.to);

	-- Handle component internals (stanzas directed to component host, mainly iq stanzas)
	if to_node == nil then
		local type = stanza.attr.type;
		if type == "error" or type == "result" then return; end
		if stanza.name == "presence" then
			presence_stanza_handler(origin, stanza);
		end
		if stanza.name == "iq" and type == "get" then
			local xmlns = stanza.tags[1].attr.xmlns
			if xmlns == "http://jabber.org/protocol/disco#info" then
				origin.send(iq_disco_info(stanza));
				return true;
			--[[
			elseif xmlns == "http://jabber.org/protocol/disco#items" then
				origin.send(iq_disco_items(stanza));
				return true;
			--]]
			elseif xmlns == "jabber:iq:register" then
				iq_register(origin, stanza);
				return true;
			end
		elseif stanza.name == "iq" and type == "set" then
			local xmlns = stanza.tags[1].attr.xmlns
			if xmlns == "jabber:iq:roster" then
				origin.send(iq_roster(stanza));
			elseif xmlns == "jabber:iq:register" then
				iq_register(origin, stanza);
				return true;
			end
		end
	end

	-- Handle presence (both component and SMS users)
	if stanza.name == "presence" then
		presence_stanza_handler(origin, stanza);
	end

	-- Handle messages (both component and SMS users)
	if stanza.name == "message" then
		message_stanza_handler(origin, stanza);
	end
end

-- Prosody hooks: links our handler functions with the relevant events
--module:hook("presence/host", presence_stanza_handler);
--module:hook("message/host", message_stanza_handler);

--module:hook("iq/host/jabber:iq:register:query", iq_register);
module:add_feature("http://jabber.org/protocol/disco#info");
module:add_feature("http://jabber.org/protocol/disco#items");
--module:hook("iq/self/http://jabber.org/protocol/disco#info:query", iq_disco_info);
--module:hook("iq/host/http://jabber.org/protocol/disco#items:query", iq_disco_items);
--module:hook("account-disco-info", iq_disco_info);
--module:hook("account-disco-items", iq_disco_items);
--[[
module:hook("iq/host", function(data)
	-- IQ to a local host received
	local origin, stanza = data.origin, data.stanza;
	if stanza.attr.type == "get" or stanza.attr.type == "set" then
		return module:fire_event("iq/host/"..stanza.tags[1].attr.xmlns..":"..stanza.tags[1].name, data);
	else
		module:fire_event("iq/host/"..stanza.attr.id, data);
		return true;
	end
end);
--]]

-- Component registration hooks: these hook in with the Prosody component
-- manager
module:hook("iq/bare", sms_event_handler);
module:hook("message/bare", sms_event_handler);
module:hook("presence/bare", sms_event_handler);
module:hook("iq/full", sms_event_handler);
module:hook("message/full", sms_event_handler);
module:hook("presence/full", sms_event_handler);
module:hook("iq/host", sms_event_handler);
module:hook("message/host", sms_event_handler);
module:hook("presence/host", sms_event_handler);
