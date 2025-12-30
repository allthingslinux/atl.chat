-- MIT License
--
-- Copyright (c) 2018 Kim Alvefur
--
-- Permission is hereby granted, free of charge, to any person obtaining a copy
-- of this software and associated documentation files (the "Software"), to deal
-- in the Software without restriction, including without limitation the rights
-- to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
-- copies of the Software, and to permit persons to whom the Software is
-- furnished to do so, subject to the following conditions:
--
-- The above copyright notice and this permission notice shall be included in
-- all copies or substantial portions of the Software.
--
-- THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
-- EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
-- MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
-- IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
-- CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
-- TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
-- SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

module:depends"http";

local jid_prep = require "util.jid".prep;
local jid_split = require "util.jid".split;

-- Support both old and new MUC code
local mod_muc = module:depends"muc";
local rooms = rawget(mod_muc, "rooms");
local get_room_from_jid = rawget(mod_muc, "get_room_from_jid") or
	function (jid)
		return rooms[jid];
	end

-- I believe the origins of this template to be in the public domain as per
-- https://github.com/badges/shields/blob/master/LICENSE.md
local template = module:get_option_string("badge_template", [[
<?xml version="1.0"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="20">
  <linearGradient id="b" x2="0" y2="100%">
    <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
    <stop offset="1" stop-opacity=".1"/>
  </linearGradient>
  <clipPath id="a">
    <rect width="{width}" height="20" rx="3" fill="#fff"/>
  </clipPath>
  <g clip-path="url(#a)">
    <path fill="#555" d="M0 0h{labelwidth}v20H0z"/>
    <path fill="#fe7d37" d="M{labelwidth} 0h{countwidth}v20H{labelwidth}z"/>
    <path fill="url(#b)" d="M0 0h{width}v20H0z"/>
  </g>
  <g fill="#fff" font-family="DejaVu Sans,Verdana,Geneva,sans-serif" font-size="11" xml:space="preserve">
    <text fill="#010101" fill-opacity=".3" y="14" x="0" textLength="{labelwidth}">{label}</text>
    <text y="13" x="0" textLength="{labelwidth}">{label}</text>
    <text fill="#010101" fill-opacity=".3" y="14" x="{labelwidth}" textLength="{countwidth}">{number}</text>
    <text y="13" x="{labelwidth}" textLength="{countwidth}">{number}</text>
  </g>
</svg>
]]);
template = assert(require "util.template"(template));

local number = module:get_option_string("badge_count", "%d online");
local charwidth = 7;

module:provides("http", {
	route = {
		["GET /*"] = function (event, path)
			local jid = jid_prep(path);
			if not jid then return end

			local room = get_room_from_jid(jid);
			if not room then return end
			if (room.get_hidden or room.is_hidden)(room) then return end

			local count = 0;
			for _ in pairs(room._occupants) do
				count = count + 1;
			end
			local badge_label = (" %s "):format(room:get_name() or jid_split(jid));
			local badge_count = (" %s "):format(string.format(number, count));

			local response = event.response;
			response.headers.content_type = "image/svg+xml";
			local svg = [[<?xml version="1.0"?>]] ..
				tostring(template.apply({
					label = badge_label;
					number = badge_count;
					width = ("%d"):format( (#badge_label + #badge_count) * charwidth );
					labelwidth = ("%d"):format( #badge_label * charwidth );
					countwidth = ("%d"):format( #badge_count * charwidth );
				}));
			return svg;
		end;
	}
});
