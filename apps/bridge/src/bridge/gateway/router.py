"""Channel router — mapping Discord channel <-> IRC <-> XMPP MUC (AUDIT §1)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from loguru import logger


@dataclass
class IrcTarget:
    """IRC channel target for a mapping."""

    server: str
    port: int
    tls: bool
    channel: str


@dataclass
class XmppTarget:
    """XMPP MUC target for a mapping."""

    muc_jid: str


@dataclass
class ChannelMapping:
    """One channel mapping: Discord <-> IRC <-> XMPP."""

    discord_channel_id: str
    irc: IrcTarget | None
    xmpp: XmppTarget | None


class ChannelRouter:
    """Routes events by channel mapping. Uses config mappings."""

    def __init__(self) -> None:
        self._mappings: list[ChannelMapping] = []

    def load_from_config(self, config: dict[str, Any]) -> None:
        """Load mappings from config dict (from config.mappings)."""
        raw = config.get("mappings")
        if not isinstance(raw, list):
            logger.warning("Router: no mappings list in config; using empty mappings")
            self._mappings = []
            return

        mappings: list[ChannelMapping] = []
        skipped = 0
        for item in raw:
            if not isinstance(item, dict):
                skipped += 1
                continue
            dc_id = str(item.get("discord_channel_id", ""))
            if not dc_id:
                skipped += 1
                continue

            irc_cfg = item.get("irc")
            irc_target: IrcTarget | None = None
            if isinstance(irc_cfg, dict):
                irc_target = IrcTarget(
                    server=str(irc_cfg.get("server", "")),
                    port=int(irc_cfg.get("port", 6667)),
                    tls=bool(irc_cfg.get("tls", False)),
                    channel=str(irc_cfg.get("channel", "")),
                )

            xmpp_cfg = item.get("xmpp")
            xmpp_target: XmppTarget | None = None
            if isinstance(xmpp_cfg, dict):
                muc = xmpp_cfg.get("muc_jid")
                if muc:
                    xmpp_target = XmppTarget(muc_jid=str(muc))

            mappings.append(
                ChannelMapping(
                    discord_channel_id=dc_id,
                    irc=irc_target,
                    xmpp=xmpp_target,
                )
            )
        self._mappings = mappings
        irc_count = sum(1 for m in mappings if m.irc)
        xmpp_count = sum(1 for m in mappings if m.xmpp)
        logger.info(
            "Router: loaded {} mappings ({} IRC, {} XMPP){}",
            len(mappings),
            irc_count,
            xmpp_count,
            f", skipped {skipped}" if skipped else "",
        )

    def get_mapping_for_discord(self, discord_channel_id: str) -> ChannelMapping | None:
        """Get mapping for a Discord channel ID."""
        for m in self._mappings:
            if m.discord_channel_id == discord_channel_id:
                return m
        return None

    def get_mapping_for_irc(self, server: str, channel: str) -> ChannelMapping | None:
        """Get mapping for an IRC server/channel."""
        for m in self._mappings:
            if m.irc and m.irc.server == server and m.irc.channel == channel:
                return m
        return None

    def get_mapping_for_xmpp(self, muc_jid: str) -> ChannelMapping | None:
        """Get mapping for an XMPP MUC JID."""
        for m in self._mappings:
            if m.xmpp and m.xmpp.muc_jid == muc_jid:
                return m
        return None

    def all_mappings(self) -> list[ChannelMapping]:
        """Return all channel mappings."""
        return list(self._mappings)
