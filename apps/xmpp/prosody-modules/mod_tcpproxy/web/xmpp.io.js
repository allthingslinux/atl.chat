var xmlns_ibb = "http://jabber.org/protocol/ibb";
var xmlns_tcp = "http://prosody.im/protocol/tcpproxy";

function XMPPIO(xmppconn, xmpptcp_host)
{
	this.xmppconn = xmppconn;
	this.xmpphost = xmpptcp_host;
	this.sid = "FIXME";

	this.listeners = [];
	return this;
}

XMPPIO.prototype = {
	connect: function (host, port)
	{
		var conn = this;
		console.log("Connecting...");

		function onConnect()
		{
			this.xmppconn.addHandler(function (stanza)
			{
				var data = stanza.getElementsByTagName("data")[0];
				if(data)
					conn.emit("data", Strophe.Base64.decode(Strophe.getText(data)));
			}, null, "message", null, null, this.xmpphost, {});
			this.xmppconn.addHandler(function (stanza)
			{
				var data = stanza.getElementsByTagName("close")[0];
				if(close)
				{
					conn.write = function () { throw "Connection closed"; };
					conn.emit("end");
				}
			}, xmlns_ibb, "iq", "set", null, this.xmpphost, {});
			conn.emit("connect");
		}

		this.xmppconn.sendIQ($iq({to:this.xmpphost,type:"set"})
			.c("open", {
				"xmlns": xmlns_ibb,
				"xmlns:tcp": xmlns_tcp,
				"tcp:host": host,
				"tcp:port": port.toString(),
				"block-size": "4096",
				"sid": this.sid.toString(),
				"stanza": "message"
			}), onConnect,
			function () { conn.emit("error"); });
	},
	emit: function ()
	{
		console.log("xmpp.io: Emitting "+arguments[0]);
		var args = Array.prototype.slice.call(arguments, 1);
		var listeners = this.listeners[arguments[0]];
		if(listeners)
		{
			for(var i=0;i<listeners.length;i++)
			{
				listeners[i][1].apply(listeners[i][0], args);
			}
		}
	},
	addListener: function (event, method, obj)
	{
		if(typeof(obj)=="undefined")
			obj = this;
		if(!(event in this.listeners))
			this.listeners[event] = [];
		this.listeners[event].push([obj, method]);
	},
	write: function (data)
	{
		return this.xmppconn.send($msg({to:this.xmpphost})
			.c("data", {xmlns:xmlns_ibb, sid:this.sid.toString()})
				.t(Strophe.Base64.encode(data)));
	},
	end: function ()
	{
		return this.xmppconn.send($iq({to:this.xmpphost})
			.c("close", {xmlns:xmlns_ibb, sid:this.sid.toString()}));
	}
};
