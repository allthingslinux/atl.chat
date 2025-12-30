module:depends("muc");

local jid_resource = require "util.jid".resource;
local st = require "util.stanza";

local prefixes = module:get_option_set("muc_inject_mentions_prefixes", {})
local suffixes = module:get_option_set("muc_inject_mentions_suffixes", {})
local enabled_rooms = module:get_option("muc_inject_mentions_enabled_rooms", nil)
local disabled_rooms = module:get_option("muc_inject_mentions_disabled_rooms", nil)
local mention_delimiters = module:get_option_set("muc_inject_mentions_mention_delimiters",  {" ", "", "\n", "\t"})
local append_mentions = module:get_option("muc_inject_mentions_append_mentions", false)
local strip_out_prefixes = module:get_option("muc_inject_mentions_strip_out_prefixes", false)
local reserved_nicks = module:get_option("muc_inject_mentions_reserved_nicks", false)
local use_bare_jid = module:get_option("muc_inject_mentions_use_bare_jid", true)
local prefix_mandatory = module:get_option("muc_inject_mentions_prefix_mandatory", false)
local reserved_nicknames = {}

local reference_xmlns = "urn:xmpp:reference:0"

local function update_reserved_nicknames(event)
    local room, data, jid = event.room.jid, event.data, event.jid
    load_room_reserved_nicknames(event.room)
    local nickname = (data or {})["reserved_nickname"]

    if nickname then
        reserved_nicknames[room][nickname] = jid
    else
        local nickname_to_remove
        for _nickname, _jid in pairs(reserved_nicknames[room]) do
            if _jid == jid then
                nickname_to_remove = _nickname
                break
            end
        end
        if nickname_to_remove then
            reserved_nicknames[room][nickname_to_remove] = nil
        end
    end
end

function load_room_reserved_nicknames(room)
    if not reserved_nicknames[room.jid] then
        reserved_nicknames[room.jid] = {}
        for jid, data in pairs(room._affiliations_data or {}) do
            local reserved_nickname = data["reserved_nickname"]
            if reserved_nicknames then
                reserved_nicknames[room.jid][reserved_nickname] = jid
            end
        end
    end
end

local function get_jid(room, nickname)
    local bare_jid = reserved_nicknames[room.jid][nickname]
    if bare_jid and use_bare_jid then
        return bare_jid
    end

    if bare_jid and not use_bare_jid then
        return room.jid .. "/" .. nickname
    end
end

local function get_participants(room)
    if not reserved_nicks then
        local occupants = room._occupants
        local key, occupant = next(occupants)
        return function ()
            while occupant do -- luacheck: ignore
                local nick = jid_resource(occupant.nick);
                local bare_jid = occupant.bare_jid
                key, occupant = next(occupants, key)
                return bare_jid, nick
            end
        end
    else
        local generator = room:each_affiliation()
        local jid, _, affiliation_data = generator(nil, nil)
        return function ()
           while jid do
                local bare_jid, nick = jid, (affiliation_data or {})["reserved_nickname"]
                jid, _, affiliation_data = generator(nil, bare_jid)
                if nick then
                    return bare_jid, nick
                end
           end
        end
    end
end

local function add_mention(mentions, bare_jid, first, last, prefix_indices, has_prefix)
    if strip_out_prefixes then
        if has_prefix then
            table.insert(prefix_indices, first-1)
        end
        first = first - #prefix_indices
        last = last - #prefix_indices
    end
    mentions[first] = {bare_jid=bare_jid, first=first, last=last}
end

local function get_client_mentions(stanza)
    local has_mentions = false
    local client_mentions = {}

    for element in stanza:childtags("reference", reference_xmlns) do
        if element.attr.type == "mention" then
            local key = tonumber(element.attr.begin) + 1 -- count starts at 0
            client_mentions[key] = {bare_jid=element.attr.uri, first=element.attr.begin, last=element.attr["end"]}
            has_mentions = true
        end
    end

    return has_mentions, client_mentions
end

local function is_room_eligible(jid)
    if not enabled_rooms and not disabled_rooms then return true; end

    if enabled_rooms then
        for _, _jid in ipairs(enabled_rooms) do
            if _jid == jid then
                return true
            end
        end
        return false
    end

    if disabled_rooms then
        for _, _jid in ipairs(disabled_rooms) do
            if _jid == jid then
                return false
            end
        end
        return true
    end
end

local function has_nick_prefix(body, first)
    -- There are no configured prefixes
    if not prefixes or #prefixes < 1 then return false end

    -- Prefix must have a space before it,
    -- be the first character of the body
    -- or be the first character after a new line
    if not mention_delimiters:contains(body:sub(first - 2, first - 2)) then
        return false
    end

    local prefix = body:sub(first - 1, first - 1)
    for _, _prefix in ipairs(prefixes) do
        if prefix == _prefix then
            return true
        end
    end

    return false
end

local function has_nick_suffix(body, last)
    -- There are no configured suffixes
    if not suffixes or #suffixes < 1 then return false end

    -- Suffix must have a space after it,
    -- be the last character of the body
    -- or be the last character before a new line
    if not mention_delimiters:contains(body:sub(last + 2, last + 2)) then
        return false
    end

    local suffix = body:sub(last+1, last+1)
    for _, _suffix in ipairs(suffixes) do
        if suffix == _suffix then
            return true
        end
    end

    return false
end

local function search_mentions(room, body, client_mentions)
    load_room_reserved_nicknames(room)
    local mentions, prefix_indices = {}, {}
    local current_word = ""
    local current_word_start
    for i = 1, #body+1 do
        local char = body:sub(i,i)
        -- Mention delimiter found, current_word is completed now
        if mention_delimiters:contains(char) and current_word_start then
            -- Check for nickname without prefix
            local jid = get_jid(room, current_word)
            if jid then
                if not prefix_mandatory then
                    add_mention(mentions, jid, current_word_start, i - 1, prefix_indices, false)
                end
            else
                -- Check for nickname with affixes
                local prefix = prefixes:contains(current_word:sub(1,1))
                local suffix = suffixes:contains(current_word:sub(-1))
                if prefix and suffix then
                    jid = get_jid(room, current_word:sub(2, -2))
                    if jid then
                        add_mention(mentions, jid, current_word_start + 1, i - 2, prefix_indices, true)
                    end
                elseif prefix then
                    jid = get_jid(room, current_word:sub(2))
                    if jid then
                        add_mention(mentions, jid, current_word_start + 1, i - 1, prefix_indices, true)
                    end
                elseif suffix and not prefix_mandatory then
                    jid = get_jid(room, current_word:sub(1, -2))
                    if jid then
                        add_mention(mentions, jid, current_word_start, i - 2, prefix_indices, false)
                    end
                end
            end

            current_word = ""
            current_word_start = nil
        elseif not mention_delimiters:contains(char) then
            current_word_start = current_word_start or i
            current_word = current_word .. char
        end
    end

    return mentions, prefix_indices
end

local function muc_inject_mentions(event)
    local room, stanza = event.room, event.stanza;
    local body = stanza:get_child_text("body")

    if not body or #body < 1 then return; end

    -- Inject mentions only if the room is configured for them
    if not is_room_eligible(room.jid) then return; end

    -- Only act on messages that do not include mentions
    -- unless configuration states otherwise.
    local has_mentions, client_mentions = get_client_mentions(stanza)
    if has_mentions and not append_mentions then return; end

    local mentions, prefix_indices = search_mentions(room, body, client_mentions)
    for _, mention in pairs(mentions) do
        -- https://xmpp.org/extensions/xep-0372.html#usecase_mention
        stanza:tag(
            "reference", {
                xmlns=reference_xmlns,
                begin=tostring(mention.first - 1), -- count starts at 0
                ["end"]=tostring(mention.last),
                type="mention",
                uri="xmpp:" .. mention.bare_jid,
            }
        ):up()
    end

    if strip_out_prefixes then
        local body_without_prefixes = ""
        local from = 0
        if #prefix_indices > 0 then
            for _, prefix_index in ipairs(prefix_indices) do
                body_without_prefixes = body_without_prefixes .. body:sub(from, prefix_index-1)
                from = prefix_index + 1
            end
            body_without_prefixes = body_without_prefixes .. body:sub(from, #body)

            -- Replace original body containing prefixes
            stanza:maptags(
                function(tag)
                    if tag.name ~= "body" then
                        return tag
                    end
                    return st.stanza("body"):text(body_without_prefixes)
                end
            )
        end
    end
end

module:hook("muc-occupant-groupchat", muc_inject_mentions)
module:hook("muc-set-affiliation", update_reserved_nicknames)
