-- Prosody IM
--
-- This project is MIT/X11 licensed. Please see the
-- COPYING file in the source package for more information.
--
local get_prefs = module:require"mod_mam/mamprefs".get;
local set_prefs = module:require"mod_mam/mamprefs".set;
local rsm = require "util.rsm";
local jid_bare = require "util.jid".bare;
local jid_prep = require "util.jid".prep;
local date_parse = require "util.datetime".parse;
local date_format = require "util.datetime".datetime;

local st = require "util.stanza";
local archive_store = "archive2";
local archive = module:open_store(archive_store, "archive");
local global_default_policy = module:get_option("default_archive_policy", false);
local default_max_items, max_max_items = 20, module:get_option_number("max_archive_query_results", 50);
local conversation_interval = tonumber(module:get_option_number("archive_conversation_interval", 86400));
local resolve_relative_path = require "core.configmanager".resolve_relative_path;

-- Feature discovery
module:add_feature("urn:xmpp:archive:auto");
module:add_feature("urn:xmpp:archive:manage");
module:add_feature("urn:xmpp:archive:pref");
module:add_feature("http://jabber.org/protocol/rsm");
-- --------------------------------------------------

local function prefs_to_stanza(prefs)
    local prefstanza = st.stanza("pref", { xmlns="urn:xmpp:archive" });
    local default = prefs[false] ~= nil and prefs[false] or global_default_policy;

    prefstanza:tag("default", {otr="oppose", save=default and "true" or "false"}):up();
    prefstanza:tag("method", {type="auto", use="concede"}):up();
    prefstanza:tag("method", {type="local", use="concede"}):up();
    prefstanza:tag("method", {type="manual", use="concede"}):up();

    for jid, choice in pairs(prefs) do
        if jid then
            prefstanza:tag("item", {jid=jid, otr="prefer", save=choice and "message" or "false" }):up()
        end
    end

    return prefstanza;
end
local function prefs_from_stanza(stanza, username)
    local current_prefs = get_prefs(username);

    -- "default" | "item" | "session" | "method"
    for elem in stanza:children() do
        if elem.name == "default" then
            current_prefs[false] = elem.attr["save"] == "true";
        elseif elem.name == "item" then
            current_prefs[elem.attr["jid"]] = not elem.attr["save"] == "false";
        elseif elem.name == "session" then
            module:log("info", "element is not supported: " .. tostring(elem));
--            local found = false;
--            for child in data:children() do
--                if child.name == elem.name and child.attr["thread"] == elem.attr["thread"] then
--                    for k, v in pairs(elem.attr) do
--                        child.attr[k] = v;
--                    end
--                    found = true;
--                    break;
--                end
--            end
--            if not found then
--                data:tag(elem.name, elem.attr):up();
--            end
        elseif elem.name == "method" then
            module:log("info", "element is not supported: " .. tostring(elem));
--            local newpref = stanza.tags[1]; -- iq:pref
--            for _, e in ipairs(newpref.tags) do
--                -- if e.name ~= "method" then continue end
--                local found = false;
--                for child in data:children() do
--                    if child.name == "method" and child.attr["type"] == e.attr["type"] then
--                        child.attr["use"] = e.attr["use"];
--                        found = true;
--                        break;
--                    end
--                end
--                if not found then
--                    data:tag(e.name, e.attr):up();
--                end
--            end
        end
    end
end

------------------------------------------------------------
-- Preferences
------------------------------------------------------------
local function preferences_handler(event)
    local origin, stanza = event.origin, event.stanza;
    local user = origin.username;
    local reply = st.reply(stanza);

    if stanza.attr.type == "get" then
        reply:add_child(prefs_to_stanza(get_prefs(user)));
    end
    if stanza.attr.type == "set" then
        local new_prefs = stanza:get_child("pref", xmlns_archive);
        if not new_prefs then return false; end

        local prefs = prefs_from_stanza(stanza, origin.username);
        local ok, err = set_prefs(user, prefs);

        if not ok then
            return origin.send(st.error_reply(stanza, "cancel", "internal-server-error", "Error storing preferences: "..tostring(err)));
        end
    end
    return origin.send(reply);
end
local function auto_handler(event)
    local origin, stanza = event.origin, event.stanza;
    if not stanza.attr["type"] == "set" then return false; end

    local user = origin.username;
    local prefs = get_prefs(user);
    local auto = stanza:get_child("auto", xmlns_archive);

    prefs[false] = auto.attr["save"] ~= nil and auto.attr["save"] == "true" or false;
    set_prefs(user, prefs);

    return origin.send(st.reply(stanza));
end

-- excerpt from mod_storage_sql2
local function get_db()
    local mod_sql = module:require("sql");
    local params = module:get_option("sql");
    local engine;

    params = params or { driver = "SQLite3" };
    if params.driver == "SQLite3" then
        params.database = resolve_relative_path(prosody.paths.data or ".", params.database or "prosody.sqlite");
    end

    assert(params.driver and params.database, "Both the SQL driver and the database need to be specified");
    engine = mod_sql:create_engine(params);
    engine:set_encoding();

    return engine;
end

------------------------------------------------------------
-- Collections. In our case there is one conversation with each contact for the whole day for simplicity
------------------------------------------------------------
local function list_stanza_to_query(origin, list_el)
    local sql = "SELECT `with`, `when` / ".. conversation_interval .." as `day`, COUNT(0) FROM `prosodyarchive` WHERE `host`=? AND `user`=? AND `store`=? ";
    local args = {origin.host, origin.username, archive_store};

    local with = list_el.attr["with"];
    if with ~= nil then
        sql = sql .. "AND `with` = ? ";
        table.insert(args, jid_bare(with));
    end

    local after = list_el.attr["start"];
    if after ~= nil then
        sql = sql .. "AND `when` >= ? ";
        table.insert(args, date_parse(after));
    end

    local before = list_el.attr["end"];
    if before ~= nil then
        sql = sql .. "AND `when` <= ? ";
        table.insert(args, date_parse(before));
    end

    sql = sql .. "GROUP BY `with`, `when` / ".. conversation_interval .." ORDER BY `when` / ".. conversation_interval .." ASC ";

    local qset = rsm.get(list_el);
    local limit = math.min(qset and qset.max or default_max_items, max_max_items);
    sql = sql.."LIMIT ?";
    table.insert(args, limit);

    table.insert(args, 1, sql);
    return args;
end
local function list_handler(event)
    local db = get_db();
    local origin, stanza = event.origin, event.stanza;
    local reply = st.reply(stanza);

    local query = list_stanza_to_query(origin, stanza.tags[1]);
    local list = reply:tag("list", {xmlns=xmlns_archive});

    for row in db:select(unpack(query)) do
        list:tag("chat", {
            xmlns=xmlns_archive,
            with=row[1],
            start=date_format(row[2] * conversation_interval),
            version=row[3]
        }):up();
    end

    origin.send(reply);
    return true;
end

------------------------------------------------------------
-- Message archive retrieval
------------------------------------------------------------

local function retrieve_handler(event)
    local origin, stanza = event.origin, event.stanza;
    local reply = st.reply(stanza);

    local retrieve = stanza:get_child("retrieve", xmlns_archive);

    local qwith = retrieve.attr["with"];
    local qstart = retrieve.attr["start"];

    module:log("debug", "Archive query, with %s from %s)",
        qwith or "anyone", qstart or "the dawn of time");

    if qstart then -- Validate timestamps
        local vstart = (qstart and date_parse(qstart));
        if (qstart and not vstart) then
            origin.send(st.error_reply(stanza, "modify", "bad-request", "Invalid timestamp"))
            return true
        end
        qstart = vstart;
    end

    if qwith then -- Validate the "with" jid
        local pwith = qwith and jid_prep(qwith);
        if pwith and not qwith then -- it failed prepping
            origin.send(st.error_reply(stanza, "modify", "bad-request", "Invalid JID"))
            return true
        end
        qwith = jid_bare(pwith);
    end

    -- RSM stuff
    local qset = rsm.get(retrieve);
    local qmax = math.min(qset and qset.max or default_max_items, max_max_items);
    local reverse = qset and qset.before or false;
    local before, after = qset and qset.before, qset and qset.after;
    if type(before) ~= "string" then before = nil; end

    -- Load all the data!
    local data, err = archive:find(origin.username, {
        start = qstart; ["end"] = qstart + conversation_interval;
        with = qwith;
        limit = qmax;
        before = before; after = after;
        reverse = reverse;
        total = true;
    });

    if not data then
        return origin.send(st.error_reply(stanza, "cancel", "internal-server-error", err));
    end
    local count = err;

    local chat = reply:tag("chat", {xmlns=xmlns_archive, with=qwith, start=date_format(qstart), version=count});
    local first, last;

    module:log("debug", "Count "..count);
    for id, item, when in data do
        if not getmetatable(item) == st.stanza_mt then
            item = st.deserialize(item);
        end
        module:log("debug", tostring(item));

        local tag = jid_bare(item.attr["from"]) == jid_bare(origin.full_jid) and "to" or "from";
        tag = chat:tag(tag, {secs = when - qstart});
        tag:add_child(item:get_child("body")):up();
        if not first then first = id; end
        last = id;
    end
    reply:add_child(rsm.generate{ first = first, last = last, count = count })

    origin.send(reply);
    return true;
end

local function not_implemented(event)
    local origin, stanza = event.origin, event.stanza;
    local reply = st.reply(stanza):tag("error", {type="cancel"});
    reply:tag("feature-not-implemented", {xmlns="urn:ietf:params:xml:ns:xmpp-stanzas"}):up();
    origin.send(reply);
end

-- Preferences
module:hook("iq/self/urn:xmpp:archive:pref", preferences_handler);
module:hook("iq/self/urn:xmpp:archive:auto", auto_handler);
module:hook("iq/self/urn:xmpp:archive:itemremove", not_implemented);
module:hook("iq/self/urn:xmpp:archive:sessionremove", not_implemented);

-- Message Archive Management
module:hook("iq/self/urn:xmpp:archive:list", list_handler);
module:hook("iq/self/urn:xmpp:archive:retrieve", retrieve_handler);
module:hook("iq/self/urn:xmpp:archive:remove", not_implemented);

-- manual archiving
module:hook("iq/self/urn:xmpp:archive:save", not_implemented);
-- replication
module:hook("iq/self/urn:xmpp:archive:modified", not_implemented);
