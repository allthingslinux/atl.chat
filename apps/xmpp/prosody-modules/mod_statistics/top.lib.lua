local array = require "util.array";
local it = require "util.iterators";
local curses = require "curses";
local stats = module:require "stats".stats;
local time = require "socket".gettime;

local sessions_idle_after = 60;
local stanza_names = {"message", "presence", "iq"};

local top = {};
top.__index = top;

local status_lines = {
	"Prosody $version - $time up $up_since, $total_users users, $cpu busy";
	"Connections: $total_c2s c2s, $total_s2sout s2sout, $total_s2sin s2sin, $total_component component";
	"Memory: $memory_lua lua, $memory_allocated process ($memory_used in use)";
	"Stanzas in: $message_in_per_second message/s, $presence_in_per_second presence/s, $iq_in_per_second iq/s";
	"Stanzas out: $message_out_per_second message/s, $presence_out_per_second presence/s, $iq_out_per_second iq/s";
};

function top:draw()
	self:draw_status();
	self:draw_column_titles();
	self:draw_conn_list();
	self.statuswin:refresh();
	self.listwin:refresh();
	--self.infowin:refresh()
	self.stdscr:move(#status_lines,0)
end

-- Width specified as cols or % of unused space, defaults to
-- title width if not specified
local conn_list_columns = {
	{ title = "ID", key = "id", width = "8" };
	{ title = "JID", key = "jid", width = "100%" };
	{ title = "STANZAS IN>", key = "total_stanzas_in", align = "right" };
	{ title = "MSG", key = "message_in", align = "right", width = "4" };
	{ title = "PRES", key = "presence_in", align = "right", width = "4" };
	{ title = "IQ", key = "iq_in", align = "right", width = "4" };
	{ title = "STANZAS OUT>", key = "total_stanzas_out", align = "right" };
	{ title = "MSG", key = "message_out", align = "right", width = "4" };
	{ title = "PRES", key = "presence_out", align = "right", width = "4" };
	{ title = "IQ", key = "iq_out", align = "right", width = "4" };
	{ title = "BYTES IN", key = "bytes_in", align = "right" };
	{ title = "BYTES OUT", key = "bytes_out", align = "right" };

};

function top:draw_status()
	for row, line in ipairs(status_lines) do
		self.statuswin:mvaddstr(row-1, 0, (line:gsub("%$([%w_]+)", self.data)));
		self.statuswin:clrtoeol();
	end
	-- Clear stanza counts
	for _, stanza_type in ipairs(stanza_names) do
		self.prosody[stanza_type.."_in_per_second"] = 0;
		self.prosody[stanza_type.."_out_per_second"] = 0;
	end
end

local function padright(s, width)
	return s..string.rep(" ", width-#s);
end

local function padleft(s, width)
	return string.rep(" ", width-#s)..s;
end

function top:resized()
	self:recalc_column_widths();
	--self.stdscr:clear();
	self:draw();
end

function top:recalc_column_widths()
	local widths = {};
	self.column_widths = widths;
	local total_width = curses.cols()-4;
	local free_width = total_width;
	for i = 1, #conn_list_columns do
		local width = conn_list_columns[i].width or "0";
		if not(type(width) == "string" and width:sub(-1) == "%") then
			width = math.max(tonumber(width), #conn_list_columns[i].title+1);
			widths[i] = width;
			free_width = free_width - width;
		end
	end
	for i = 1, #conn_list_columns do
		if not widths[i] then
			local pc_width = tonumber((conn_list_columns[i].width:gsub("%%$", "")));
			widths[i] = math.floor(free_width*(pc_width/100));
		end
	end
	return widths;
end

function top:draw_column_titles()
	local widths = self.column_widths;
	self.listwin:attron(curses.A_REVERSE);
	self.listwin:mvaddstr(0, 0, "  ");
	for i, column in ipairs(conn_list_columns) do
		self.listwin:addstr(padright(column.title, widths[i]));
	end
	self.listwin:addstr("  ");
	self.listwin:attroff(curses.A_REVERSE);
end

local function session_compare(session1, session2)
	local stats1, stats2 = session1.stats, session2.stats;
	return (stats1.total_stanzas_in + stats1.total_stanzas_out) >
		(stats2.total_stanzas_in + stats2.total_stanzas_out);
end

function top:draw_conn_list()
	local rows = curses.lines()-(#status_lines+2)-5;
	local cutoff_time = time() - sessions_idle_after;
	local widths = self.column_widths;
	local top_sessions = array.collect(it.values(self.active_sessions)):sort(session_compare);
	for index = 1, rows do
		local session = top_sessions[index];
		if session then
			if session.last_update < cutoff_time then
				self.active_sessions[session.id] = nil;
			else
				local row = {};
				for i, column in ipairs(conn_list_columns) do
					local width = widths[i];
					local v = tostring(session[column.key] or ""):sub(1, width);
					if #v < width then
						if column.align == "right" then
							v = padleft(v, width-1).." ";
						else
							v = padright(v, width);
						end
					end
					table.insert(row, v);
				end
				if session.updated then
					self.listwin:attron(curses.A_BOLD);
				end
				self.listwin:mvaddstr(index, 0, "  "..table.concat(row));
				if session.updated then
					session.updated = false;
					self.listwin:attroff(curses.A_BOLD);
				end
			end
		else
			-- FIXME: How to clear a line? It's 5am and I don't feel like reading docs.
			self.listwin:move(index, 0);
			self.listwin:clrtoeol();
		end
	end
end

function top:update_stat(name, value)
	self.prosody[name] = value;
end

function top:update_session(id, jid, stats)
	self.active_sessions[id] = stats;
	stats.id, stats.jid, stats.stats = id, jid, stats;
	stats.total_bytes = stats.bytes_in + stats.bytes_out;
	for _, stanza_type in ipairs(stanza_names) do
		self.prosody[stanza_type.."_in_per_second"] = (self.prosody[stanza_type.."_in_per_second"] or 0) + stats[stanza_type.."_in"];
		self.prosody[stanza_type.."_out_per_second"] = (self.prosody[stanza_type.."_out_per_second"] or 0) + stats[stanza_type.."_out"];
	end
	stats.total_stanzas_in = stats.message_in + stats.presence_in + stats.iq_in;
	stats.total_stanzas_out = stats.message_out + stats.presence_out + stats.iq_out;
	stats.last_update = time();
	stats.updated = true;
end

local function new(base)
	setmetatable(base, top);
	base.data = setmetatable({}, {
		__index = function (t, k)
			local stat = stats[k];
			if stat and stat.tostring then
				if type(stat.tostring) == "function" then
					return stat.tostring(base.prosody[k]);
				elseif type(stat.tostring) == "string" then
					local v = base.prosody[k];
					if v == nil then
						return "?";
					end
					return (stat.tostring):format(v);
				end
			end
			return base.prosody[k];
		end;
	});

	base.active_sessions = {};

	base.statuswin = curses.newwin(#status_lines, 0, 0, 0);

	base.promptwin = curses.newwin(1, 0, #status_lines, 0);
	base.promptwin:addstr("");
	base.promptwin:refresh();

	base.listwin = curses.newwin(curses.lines()-(#status_lines+2)-5, 0, #status_lines+1, 0);
	base.listwin:syncok();

	base.infowin = curses.newwin(5, 0, curses.lines()-5, 0);
	base.infowin:mvaddstr(1, 1, "Hello world");
	base.infowin:border(0,0,0,0);
	base.infowin:syncok();
	base.infowin:refresh();

	base:resized();

	return base;
end

return { new = new };
