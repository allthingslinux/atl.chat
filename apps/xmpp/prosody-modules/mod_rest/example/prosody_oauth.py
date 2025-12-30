from requests_oauthlib import OAuth2Session
import requests


class ProsodyRestSession(OAuth2Session):
    def __init__(
        self, base_url, client_name, client_uri, redirect_uri, *args, **kwargs
    ):
        self.base_url = base_url
        discovery_url = base_url + "/.well-known/oauth-authorization-server"

        meta = requests.get(discovery_url).json()
        reg = requests.post(
            meta["registration_endpoint"],
            json={
                "client_name": client_name,
                "client_uri": client_uri,
                "redirect_uris": [redirect_uri],
                "application_type": redirect_uri[:8] == "https://"
                and "web"
                or "native",
            },
        ).json()

        super().__init__(client_id=reg["client_id"], *args, **kwargs)

        self.meta = meta
        self.client_secret = reg["client_secret"]
        self.client_id = reg["client_id"]

    def authorization_url(self, *args, **kwargs):
        return super().authorization_url(
            self.meta["authorization_endpoint"], *args, **kwargs
        )

    def fetch_token(self, *args, **kwargs):
        return super().fetch_token(
            token_url=self.meta["token_endpoint"],
            client_secret=self.client_secret,
            *args,
            **kwargs
        )

    def xmpp(self, json=None, *args, **kwargs):
        return self.post(self.base_url + "/rest", json=json, *args, **kwargs)


if __name__ == "__main__":
    # Example usage

    # from prosody_oauth import ProsodyRestSession
    from getpass import getpass

    p = ProsodyRestSession(
        input("Base URL: "),
        "Prosody mod_rest OAuth 2 example",
        "https://modules.prosody.im/mod_rest",
        "urn:ietf:wg:oauth:2.0:oob",
    )

    print("Open the following URL in a browser and login:")
    print(p.authorization_url()[0])

    p.fetch_token(code=getpass("Paste Authorization code: "))

    print(p.xmpp(json={"disco": True, "to": "jabber.org"}).json())
