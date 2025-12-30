local curses = require "curses";
local server = require "net.server_select";
local timer = require "util.timer";
local envload = require "util.envload".envload;

assert(curses.timeout, "Incorrect version of curses library. Try 'sudo luarocks install luaposix'");

local top = module:require "top";

function main()
	local stdscr = curses.stdscr()  -- it's a userdatum
	--stdscr:clear();
	local view = top.new({
		stdscr = stdscr;
		prosody = { up_since = os.time() };
		conn_list = {};
	});

	timer.add_task(0.01, function ()
		local ch = stdscr:getch();
		if ch then
			if stdscr:getch() == 410 then
				view:resized();
			else
				curses.ungetch(ch);
			end
		end
		return 0.2;
	end);

	timer.add_task(0, function ()
		view:draw();
		return 1;
	end);

	--[[
	posix.signal(28, function ()
		table.insert(view.conn_list, { jid = "WINCH" });
		--view:draw();
	end);
	]]

	-- Fake socket object around stdin
	local stdin = {
        	getfd = function () return 0; end;
        	dirty = function (self) return false; end;
        	settimeout = function () end;
        	send = function (_, d) return #d, 0; end;
        	close = function () end;
        	receive = function (_, patt)
        		local ch = stdscr:getch();
        		if ch >= 0 and ch <=255 then
        			return string.char(ch);
        		elseif ch == 410 then
        			view:resized();
        		else
        			table.insert(view.conn_list, { jid = tostring(ch) }); --FIXME
        		end
        		return "";
        	end
	};
	local function on_incoming(stdin, text)
		-- TODO: Handle keypresses
		if text:lower() == "q" then os.exit(); end
	end
	stdin = server.wrapclient(stdin, "stdin", 0, {
		onincoming = on_incoming, ondisconnect = function () end
	}, "*a");

	local function handle_line(line)
		local e = {
			STAT = function (name) return function (value)
				view:update_stat(name, value);
			end end;
			SESS = function (id) return function (jid) return function (stats)
				view:update_session(id, jid, stats);
			end end end;
		};
		local chunk = assert(envload(line, "=prosodytop", e));
		chunk();
	end

	local stats_listener = {};

	function stats_listener.onconnect(conn)
		--stdscr:mvaddstr(6, 0, "CONNECTED");
	end

	local partial = "";
	function stats_listener.onincoming(conn, data)
		--print("DATA", data)
		data = partial..data;
		local lastpos = 1;
		for line, pos in data:gmatch("([^\n]+)\n()") do
			lastpos = pos;
			handle_line(line);
		end
		partial = data:sub(lastpos);
	end

	function stats_listener.ondisconnect(conn, err)
		stdscr:mvaddstr(6, 0, "DISCONNECTED: "..(err or "unknown"));
	end

	local conn = require "socket".tcp();
	assert(conn:connect("localhost", 5782));
	handler = server.wrapclient(conn, "localhost", 5782, stats_listener, "*a");
end

return {
	run = function ()
		--os.setlocale("UTF-8", "all")

		curses.initscr()
		curses.cbreak()
		curses.echo(false)  -- not noecho !
		curses.nl(false)    -- not nonl !
		curses.timeout(0);

		local ok, err = pcall(main);

		--while true do stdscr:getch() end
		--stdscr:endwin()

		if ok then
			ok, err = xpcall(server.loop, debug.traceback);
		end

		curses.endwin();

		--stdscr:refresh();
		if not ok then
			print(err);
		end

		print"DONE"
	end;
};
