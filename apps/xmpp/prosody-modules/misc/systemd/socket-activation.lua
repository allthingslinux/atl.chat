-- Monkeypatch to support socket activation
--
-- Requires LuaSocket after "agnostic" changes merged
--
-- To enable:
-- RunScript "socket-activation.lua"

local socket = require"socket";
local tcp_serv_mt = debug.getregistry()["tcp{server}"];
local socket_bind = socket.bind;

local SD_LISTEN_FDS_START = 3;

local fds = tonumber(os.getenv"LISTEN_FDS") or 0;

if fds < SD_LISTEN_FDS_START then return; end

local servs = {};

for i = 1, fds do
	local serv = socket.tcp();
	if serv:getfd() >= 0 then
		return; -- This won't work, we will leak the old FD
	end
	debug.setmetatable(serv, tcp_serv_mt);
	serv:setfd(SD_LISTEN_FDS_START + i - 1);
	local ip, port = serv:getsockname();
	servs [ ip .. ":" .. port ] = serv;
end

function socket.bind( ip, port, backlog )
	local sock = servs [ ip .. ":" .. port ];
	if sock then
		servs [ ip .. ":" .. port ] = nil;
		return sock;
	end
	if next(servs) == nil then
		-- my work here is done
		socket.bind = socket_bind;
	end
	return socket_bind( ip, port, backlog );
end
