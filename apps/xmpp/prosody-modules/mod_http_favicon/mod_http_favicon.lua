module:depends("http");

local favicon = require"util.encodings".base64.decode[[
AAABAAEAEBAAAAEAIABoBAAAFgAAACgAAAAQAAAAIAAAAAEAIAAAAAAAAAQAAAAAAAAAAAAAAAAA
AAAAAAD///8AsuD6TGrE95RiwfabYsH2m2TB9pmU1Phq+vz9A/38+wPx07xq67+emeq+nZvqvp2b
68GilPTfz0z///8AsuD6TACb8v8Am/L/AJvy/wCb8v8Am/L/AJvy/3TI94ntxqiJ35dh/9+XYf/f
l2H/35dh/9+XYf/fl2H/9N/PTGrE95QAm/L/AJvy/wCb8v8Am/L/AJvy/wCb8v8qq/PU5Kh61N+X
Yf/fl2H/35dh/9+XYf/fl2H/35dh/+vBopRiwfabAJvy/wCb8v8Am/L/AJvy/wCb8v8Am/L/Iqjz
3OOkdtzfl2H/35dh/9+XYf/fl2H/35dh/9+XYf/qvp2bYsH2mwCb8v8Am/L/AJvy/wCb8v8Am/L/
AJvy/yKo89zjpHbc35dh/9+XYf/fl2H/35dh/9+XYf/fl2H/6r6dm2TB9pkAm/L/AJvy/wCb8v8A
m/L/AJvy/wCb8v8kqfPa46V32t+XYf/fl2H/35dh/9+XYf/fl2H/35dh/+u/npmU1PhqAJvy/wCb
8v8Am/L/AJvy/wCb8v8Am/L/Vrz2p+m5lqffl2H/35dh/9+XYf/fl2H/35dh/9+XYf/x07xq+vz9
A3TI94kqq/PUIqjz3CKo89wkqfPaVrz2p+b0/Bf79O8X6bmWp+Old9rjpHbc46R23OSoetTtxqiJ
/fz7A/38+wPtxqiJ5Kh61OOkdtzjpHbc46V32um5lqf79O8X5vT8F1a89qckqfPaIqjz3CKo89wq
q/PUdMj3ifr8/QPx07xq35dh/9+XYf/fl2H/35dh/9+XYf/fl2H/6bmWp1a89qcAm/L/AJvy/wCb
8v8Am/L/AJvy/wCb8v+U1Phq67+emd+XYf/fl2H/35dh/9+XYf/fl2H/35dh/+Old9okqfPaAJvy
/wCb8v8Am/L/AJvy/wCb8v8Am/L/ZMH2meq+nZvfl2H/35dh/9+XYf/fl2H/35dh/9+XYf/jpHbc
Iqjz3ACb8v8Am/L/AJvy/wCb8v8Am/L/AJvy/2LB9pvqvp2b35dh/9+XYf/fl2H/35dh/9+XYf/f
l2H/46R23CKo89wAm/L/AJvy/wCb8v8Am/L/AJvy/wCb8v9iwfab68GilN+XYf/fl2H/35dh/9+X
Yf/fl2H/35dh/+SoetQqq/PUAJvy/wCb8v8Am/L/AJvy/wCb8v8Am/L/asT3lPTfz0zfl2H/35dh
/9+XYf/fl2H/35dh/9+XYf/txqiJdMj3iQCb8v8Am/L/AJvy/wCb8v8Am/L/AJvy/7Lg+kz///8A
9N/PTOvBopTqvp2b6r6dm+u/npnx07xq/fz7A/r8/QOU1PhqZMH2mWLB9ptiwfabasT3lLLg+kz/
//8Aw8MAAIABAAAAAAAAAAAAAAAAAAAAAAAAgAEAAIGBAACBgQAAgAEAAAAAAAAAAAAAAAAAAAAA
AACAAQAAw8MAAA==]];

local filename = module:get_option_string("favicon");
if filename then
	local fd = assert(module:load_resource(filename));
	favicon = assert(fd:read("*a"));
end

module:provides("http", {
	default_path = "/favicon.ico";
	route = {
		GET = {
			headers = {
				content_type = "image/x-icon";
			};
			body = favicon;
		}
	}
});
