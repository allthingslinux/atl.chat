from flask import Flask, Response, request, jsonify

app = Flask("echobot")


@app.route("/api", methods=["OPTIONS"])
def options():
    """
    Startup check. Return an appropriate Accept header to confirm the
    data type to use.
    """

    return Response(status=200, headers={"accept": "application/json"})


@app.route("/api", methods=["POST"])
def hello():
    """
    Example RESTful JSON format stanza handler.
    """

    print(request.data)
    if request.is_json:
        data = request.get_json()

        if "kind" not in data:
            return Response(status=400)

        if data["kind"] == "message" and "body" in data:
            # Reply to a message
            return jsonify({"body": "Yes this is flask app"})

        elif data["kind"] == "iq" and data["type"] == "get":
            if "disco" in data:
                # Return supported features
                return jsonify(
                    {
                        "disco": {
                            "identities": [
                                {
                                    "category": "component",
                                    "type": "generic",
                                    "name": "Flask app",
                                }
                            ],
                            "features": [
                                "http://jabber.org/protocol/disco#info",
                                "http://jabber.org/protocol/disco#items",
                                "jabber:iq:version",
                                "urn:xmpp:ping",
                            ],
                        }
                    }
                )

            elif "items" in data:
                # Disco items
                return jsonify(
                    {"items": [{"jid": "example.org", "name": "Example Dot Org"}]}
                )

            elif "version" in data:
                # Version info
                return jsonify({"version": {"name": "app.py", "version": "0"}})

            elif "ping" in data:
                # Respond to ping
                return Response(status=204)

    return Response(status=501)


if __name__ == "__main__":
    app.run()
