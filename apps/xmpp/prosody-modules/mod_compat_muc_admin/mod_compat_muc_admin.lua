local st = require "util.stanza";
local jid_split = require "util.jid".split;
local jid_bare = require "util.jid".bare;
local jid_prep = require "util.jid".prep;
local log = require "util.logger".init("mod_muc");
local muc_host = module:get_host();

if not hosts[muc_host].modules.muc then -- Not a MUC host
	module:log("error", "this module can only be used on muc hosts."); return false;
end

-- Constants and imported functions from muc.lib.lua
local xmlns_ma, xmlns_mo = "http://jabber.org/protocol/muc#admin", "http://jabber.org/protocol/muc#owner";
local kickable_error_conditions = {
	["gone"] = true;
	["internal-server-error"] = true;
	["item-not-found"] = true;
	["jid-malformed"] = true;
	["recipient-unavailable"] = true;
	["redirect"] = true;
	["remote-server-not-found"] = true;
	["remote-server-timeout"] = true;
	["service-unavailable"] = true;
	["malformed error"] = true;
};
local function get_error_condition(stanza)
	local _, condition = stanza:get_error();
 	return condition or "malformed error";
end
local function is_kickable_error(stanza)
	local cond = get_error_condition(stanza);
	return kickable_error_conditions[cond] and cond;
end
local function build_unavailable_presence_from_error(stanza)
	local type, condition, text = stanza:get_error();
	local error_message = "Kicked: "..(condition and condition:gsub("%-", " ") or "presence error");
	if text then
		error_message = error_message..": "..text;
	end
	return st.presence({type='unavailable', from=stanza.attr.from, to=stanza.attr.to})
		:tag('status'):text(error_message);
end
local function getUsingPath(stanza, path, getText)
	local tag = stanza;
	for _, name in ipairs(path) do
		if type(tag) ~= 'table' then return; end
		tag = tag:child_with_name(name);
	end
	if tag and getText then tag = table.concat(tag); end
	return tag;
end
local function getText(stanza, path) return getUsingPath(stanza, path, true); end

-- COMPAT: iq condensed function
hosts[muc_host].modules.muc.stanza_handler.muc_new_room.room_mt["compat_iq"] = function (self, origin, stanza, xmlns)
	local actor = stanza.attr.from;
	local affiliation = self:get_affiliation(actor);
	local current_nick = self._jid_nick[actor];
	local role = current_nick and self._occupants[current_nick].role or self:get_default_role(affiliation);
	local item = stanza.tags[1].tags[1];
	if item and item.name == "item" then
		if stanza.attr.type == "set" then
			local callback = function() origin.send(st.reply(stanza)); end
			if item.attr.jid then -- Validate provided JID
				item.attr.jid = jid_prep(item.attr.jid);
				if not item.attr.jid then
					origin.send(st.error_reply(stanza, "modify", "jid-malformed"));
					return;
				end
			end
			if not item.attr.jid and item.attr.nick then -- COMPAT Workaround for Miranda sending 'nick' instead of 'jid' when changing affiliation
				local occupant = self._occupants[self.jid.."/"..item.attr.nick];
				if occupant then item.attr.jid = occupant.jid; end
			elseif not item.attr.nick and item.attr.jid then
				local nick = self._jid_nick[item.attr.jid];
				if nick then item.attr.nick = select(3, jid_split(nick)); end
			end
			local reason = item.tags[1] and item.tags[1].name == "reason" and #item.tags[1] == 1 and item.tags[1][1];
			if item.attr.affiliation and item.attr.jid and not item.attr.role then
				local success, errtype, err = self:set_affiliation(actor, item.attr.jid, item.attr.affiliation, callback, reason);
				if not success then origin.send(st.error_reply(stanza, errtype, err)); end
			elseif item.attr.role and item.attr.nick and not item.attr.affiliation then
				local success, errtype, err = self:set_role(actor, self.jid.."/"..item.attr.nick, item.attr.role, callback, reason);
				if not success then origin.send(st.error_reply(stanza, errtype, err)); end
			else
				origin.send(st.error_reply(stanza, "cancel", "bad-request"));
			end
		elseif stanza.attr.type == "get" then
			local _aff = item.attr.affiliation;
			local _rol = item.attr.role;
			if _aff and not _rol then
				if affiliation == "owner" or (affiliation == "admin" and _aff ~= "owner" and _aff ~= "admin") then
					local reply = st.reply(stanza):query(xmlns);
					for jid, affiliation in pairs(self._affiliations) do
						if affiliation == _aff then
							reply:tag("item", {affiliation = _aff, jid = jid}):up();
						end
					end
					origin.send(reply);
				else
					origin.send(st.error_reply(stanza, "auth", "forbidden"));
				end
			elseif _rol and not _aff then
				if role == "moderator" then
					-- TODO allow admins and owners not in room? Provide read-only access to everyone who can see the participants anyway?
					if _rol == "none" then _rol = nil; end
					local reply = st.reply(stanza):query(xmlns);
					for occupant_jid, occupant in pairs(self._occupants) do
						if occupant.role == _rol then
							reply:tag("item", {
								nick = select(3, jid_split(occupant_jid)),
								role = _rol or "none",
								affiliation = occupant.affiliation or "none",
								jid = occupant.jid
								}):up();
						end
					end
					origin.send(reply);
				else
					origin.send(st.error_reply(stanza, "auth", "forbidden"));
				end
			else
				origin.send(st.error_reply(stanza, "cancel", "bad-request"));
			end
		end
	elseif stanza.attr.type == "set" or stanza.attr.type == "get" then
		origin.send(st.error_reply(stanza, "cancel", "bad-request"));
	end
end

-- COMPAT: reworked handle_to_room function
hosts[muc_host].modules.muc.stanza_handler.muc_new_room.room_mt["handle_to_room"] = function (self, origin, stanza)
	local type = stanza.attr.type;
	local xmlns = stanza.tags[1] and stanza.tags[1].attr.xmlns;
	if stanza.name == "iq" then
		if xmlns == "http://jabber.org/protocol/disco#info" and type == "get" then
			origin.send(self:get_disco_info(stanza));
		elseif xmlns == "http://jabber.org/protocol/disco#items" and type == "get" then
			origin.send(self:get_disco_items(stanza));
		elseif xmlns == xmlns_ma or xmlns == xmlns_mo then
			if xmlns == xmlns_ma then
				self:compat_iq(origin, stanza, xmlns);
			elseif xmlns == xmlns_mo and (type == "set" or type == "get") and stanza.tags[1].name == "query" then
				local owner_err = st.error_reply(stanza, "auth", "forbidden", "Only owners can configure rooms");
				if #stanza.tags[1].tags == 0 and stanza.attr.type == "get" then
					if self:get_affiliation(stanza.attr.from) ~= "owner" then
						origin.send(owner_err);
					else self:send_form(origin, stanza); end
				elseif stanza.attr.type == "set" and stanza.tags[1]:get_child("x", "jabber:x:data") then
					if self:get_affiliation(stanza.attr.from) ~= "owner" then
						origin.send(owner_err);
					else self:process_form(origin, stanza); end
				elseif stanza.tags[1].tags[1].name == "destroy" then
					if self:get_affiliation(stanza.attr.from) == "owner" then
						local newjid = stanza.tags[1].tags[1].attr.jid;
						local reason, password;
						for _,tag in ipairs(stanza.tags[1].tags[1].tags) do
							if tag.name == "reason" then
								reason = #tag.tags == 0 and tag[1];
							elseif tag.name == "password" then
								password = #tag.tags == 0 and tag[1];
							end
						end
						self:destroy(newjid, reason, password);
						origin.send(st.reply(stanza));
					else origin.send(owner_err); end
				else
					self:compat_iq(origin, stanza, xmlns);
				end
			else
				origin.send(st.error_reply(stanza, "modify", "bad-request"));
			end
		elseif type == "set" or type == "get" then
			origin.send(st.error_reply(stanza, "cancel", "service-unavailable"));
		end
	elseif stanza.name == "message" and type == "groupchat" then
		local from, to = stanza.attr.from, stanza.attr.to;
		local room = jid_bare(to);
		local current_nick = self._jid_nick[from];
		local occupant = self._occupants[current_nick];
		if not occupant then -- not in room
			origin.send(st.error_reply(stanza, "cancel", "not-acceptable"));
		elseif occupant.role == "visitor" then
			origin.send(st.error_reply(stanza, "cancel", "forbidden"));
		else
			local from = stanza.attr.from;
			stanza.attr.from = current_nick;
			local subject = getText(stanza, {"subject"});
			if subject then
				if occupant.role == "moderator" or
					( self._data.changesubject and occupant.role == "participant" ) then -- and participant
					self:set_subject(current_nick, subject); -- TODO use broadcast_message_stanza
				else
					stanza.attr.from = from;
					origin.send(st.error_reply(stanza, "cancel", "forbidden"));
				end
			else
				self:broadcast_message(stanza, true);
			end
			stanza.attr.from = from;
		end
	elseif stanza.name == "message" and type == "error" and is_kickable_error(stanza) then
		local current_nick = self._jid_nick[stanza.attr.from];
		log("debug", "%s kicked from %s for sending an error message", current_nick, self.jid);
		self:handle_to_occupant(origin, build_unavailable_presence_from_error(stanza)); -- send unavailable
	elseif stanza.name == "presence" then -- hack - some buggy clients send presence updates to the room rather than their nick
		local to = stanza.attr.to;
		local current_nick = self._jid_nick[stanza.attr.from];
		if current_nick then
			stanza.attr.to = current_nick;
			self:handle_to_occupant(origin, stanza);
			stanza.attr.to = to;
		elseif type ~= "error" and type ~= "result" then
			origin.send(st.error_reply(stanza, "cancel", "service-unavailable"));
		end
	elseif stanza.name == "message" and not stanza.attr.type and #stanza.tags == 1 and self._jid_nick[stanza.attr.from]
		and stanza.tags[1].name == "x" and stanza.tags[1].attr.xmlns == "http://jabber.org/protocol/muc#user" then
		local x = stanza.tags[1];
		local payload = (#x.tags == 1 and x.tags[1]);
		if payload and payload.name == "invite" and payload.attr.to then
			local _from, _to = stanza.attr.from, stanza.attr.to;
			local _invitee = jid_prep(payload.attr.to);
			if _invitee then
				local _reason = payload.tags[1] and payload.tags[1].name == 'reason' and #payload.tags[1].tags == 0 and payload.tags[1][1];
				local invite = st.message({from = _to, to = _invitee, id = stanza.attr.id})
					:tag('x', {xmlns='http://jabber.org/protocol/muc#user'})
						:tag('invite', {from=_from})
							:tag('reason'):text(_reason or ""):up()
						:up();
						if self:get_password() then
							invite:tag("password"):text(self:get_password()):up();
						end
					invite:up()
					:tag('x', {xmlns="jabber:x:conference", jid=_to}) -- COMPAT: Some older clients expect this
						:text(_reason or "")
					:up()
					:tag('body') -- Add a plain message for clients which don't support invites
						:text(_from..' invited you to the room '.._to..(_reason and (' ('.._reason..')') or ""))
					:up();
				if self:is_members_only() and not self:get_affiliation(_invitee) then
					log("debug", "%s invited %s into members only room %s, granting membership", _from, _invitee, _to);
					self:set_affiliation(_from, _invitee, "member", nil, "Invited by " .. self._jid_nick[_from])
				end
				self:_route_stanza(invite);
			else
				origin.send(st.error_reply(stanza, "cancel", "jid-malformed"));
			end
		else
			origin.send(st.error_reply(stanza, "cancel", "bad-request"));
		end
	else
		if type == "error" or type == "result" then return; end
		origin.send(st.error_reply(stanza, "cancel", "service-unavailable"));
	end
end
