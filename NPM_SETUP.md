# Nginx Proxy Manager (NPM) Setup for atl.chat

Since `atl.chat` now runs on a private Tailscale IP (`100.64.7.x`) and relies on `atl.network` (NPM) for public ingress, you must configure NPM to proxy traffic correctly.

## Prerequisites

1.  **Tailscale Reference**: Verify the `atl.chat` VPS is reachable from the NPM host.
    *   Target IP: `100.64.7.X` (Replace with actual `atl.chat` Tailscale IP)
2.  **DNS**: Ensure public DNS (Cloudflare) points `*.atl.chat` and `atl.chat` to your **NPM Host's Public IP**.

---

## 1. Web Configuration (Proxy Hosts)

Handles HTTPS traffic for Web Panel, BOSH, WebSocket, and Uploads.

### A. IRC Webpanel (`panel.irc.atl.chat`)
*   **Domain**: `panel.irc.atl.chat`
*   **Forward Host**: `100.64.7.X`
*   **Forward Port**: `8080`
*   **Scheme**: `http`
*   **SSL**: Request a new Let's Encrypt cert (or use wildcard). Force SSL.
*   **Advanced**: None needed. standard HTTP proxy.

### B. XMPP Web Services (`xmpp.atl.chat`)
Used for Web Clients (Converse.js), BOSH, and WebSockets.

*   **Domain**: `xmpp.atl.chat`
*   **Forward Host**: `100.64.7.X`
*   **Forward Port**: `5280`
*   **Scheme**: `http`
*   **SSL**: Request/Use Cert. Force SSL.
*   **Locations (Custom Locations Tab)**:
    *   `/xmpp-websocket` -> `http://100.64.7.X:5280/xmpp-websocket`
        *   *Upgrade Connection*: **enabled** (Crucial for WS)
    *   `/ws` -> `http://100.64.7.X:5280/xmpp-websocket` (Alias)
        *   *Upgrade Connection*: **enabled**
    *   `/http-bind` -> `http://100.64.7.X:5280/http-bind`
    *   `/bosh` -> `http://100.64.7.X:5280/http-bind` (Alias)

### C. XMPP Uploads (`upload.atl.chat`)
*   **Domain**: `upload.atl.chat`
*   **Forward Host**: `100.64.7.X`
*   **Forward Port**: `5280` (Prosody serves uploads on HTTP 5280 by default)
*   **Scheme**: `http`
*   **SSL**: Yes. Force SSL.
*   **Advanced Config**:
    ```nginx
    client_max_body_size 100m;
    proxy_request_buffering off;
    ```

---

## 2. Stream Configuration (TCP Streams)

Handles raw TCP traffic for IRC and XMPP Clients/Servers.
**Crucial**: You must enable **PROXY Protocol** on these streams so `atl.chat` sees the real client IP (since we configured `proxy` block in Unreal and `mod_net_proxy` in Prosody).

### A. IRC Secure (`6697`)
*   **Incoming Port**: `6697`
*   **Forward Host**: `100.64.7.X`
*   **Forward Port**: `6697`
*   **TCP/UDP**: TCP
*   **Advanced/Custom Conf**:
    *   If your NPM version controls `proxy_protocol`, enable **Send PROXY Protocol**.
    *   *Note*: UnrealIRCd expects TLS *and* PROXY protocol. Since NPM is just passing TCP (Stream), it doesn't terminate TLS. UnrealIRCd terminates TLS using its local certs (`atl-certs`).

### B. XMPP Client (`5222`)
*   **Incoming Port**: `5222`
*   **Forward Host**: `100.64.7.X`
*   **Forward Port**: `5222`
*   **TCP/UDP**: TCP
*   **PROXY Protocol**: Enable "Send PROXY Protocol".

### C. XMPP Server (`5269`)
*   **Incoming Port**: `5269`
*   **Forward Host**: `100.64.7.X`
*   **Forward Port**: `5269`
*   **TCP/UDP**: TCP
*   **PROXY Protocol**: Enable "Send PROXY Protocol".

---

## Summary of Port Forwarding

| Public Port | Service | Type | Target (100.64.7.X) | PROXY Protocol? |
| :--- | :--- | :--- | :--- | :--- |
| **80/443** | Web/BOSH/WS | HTTPS | `8080`, `5280` | No (Handled by HTTP Headers) |
| **6697** | IRC SSL | TCP | `6697` | **YES** |
| **5222** | XMPP C2S | TCP | `5222` | **YES** |
| **5269** | XMPP S2S | TCP | `5269` | **YES** |
