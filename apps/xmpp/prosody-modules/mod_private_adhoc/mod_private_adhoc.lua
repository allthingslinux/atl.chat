-- Prosody IM
-- Copyright (C) 2008-2010 Matthew Wild
-- Copyright (C) 2008-2010 Waqas Hussain
--
-- This project is MIT/X11 licensed. Please see the
-- COPYING file in the source package for more information.
--

-- Module by Thomas Raschbacher 2014
-- lordvan@lordvan.com

module:depends"adhoc";
local dataforms_new = require "util.dataforms".new;
local st = require "util.stanza";
local jid_split = require "util.jid".split;

local private_storage = module:open_store("private");

local private_adhoc_result_layout = dataforms_new{
   { name = "FORM_TYPE", type = "hidden", value = "http://jabber.org/protocol/admin" };
   { name = "privatexmldata", type = "text-multi", label = "Private XML data" };
};


function private_adhoc_command_handler (self, data, state)
   local username, hostname = jid_split(data.from);
   local data, err = private_storage:get(username);
   local dataString = "";
   if not data then
      dataString = "No data found.";
      if err then dataString = dataString..err end;
   else
      for key,value in pairs(data) do
	 dataString = dataString..tostring(st.deserialize(value)):gsub("><",">\n<")
	 dataString = dataString.."\n\n";
      end
   end
   return { status = "completed", result= { layout = private_adhoc_result_layout, values = {privatexmldata=dataString.."\n"}} };
end

local adhoc_new = module:require "adhoc".new;
local descriptor = adhoc_new("Query private data", "private_adhoc", private_adhoc_command_handler, "local_user");
module:add_item ("adhoc", descriptor);

