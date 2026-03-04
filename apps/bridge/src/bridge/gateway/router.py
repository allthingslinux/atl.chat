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
        self._by_discord: dict[str, ChannelMapping] = {}
        self._by_irc: dict[tuple[str, str], ChannelMapping] = {}
        self._by_xmpp: dict[str, ChannelMapping] = {}

    def load_from_config(self, config: dict[str, Any]) -> None:
        """Load mappings from config dict (from config.mappings)."""
        raw = config.get("mappings")
        if not isinstance(raw, list):
            logger.warning("Router: no mappings list in config; using empty mappings")
            self._mappings = []
            self._by_discord = {}
            self._by_irc = {}
            self._by_xmpp = {}
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

        # Build O(1) lookup indexes
        by_discord: dict[str, ChannelMapping] = {}
        by_irc: dict[tuple[str, str], ChannelMapping] = {}
        by_xmpp: dict[str, ChannelMapping] = {}

        for m in mappings:
            if m.discord_channel_id in by_discord:
                logger.warning("Duplicate discord_channel_id: {}", m.discord_channel_id)
            by_discord[m.discord_channel_id] = m

            if m.irc:
                key = (m.irc.server, m.irc.channel)
                if key in by_irc:
                    logger.warning("Duplicate IRC key: {}", key)
                by_irc[key] = m

            if m.xmpp:
                if m.xmpp.muc_jid in by_xmpp:
                    logger.warning("Duplicate XMPP MUC JID: {}", m.xmpp.muc_jid)
                by_xmpp[m.xmpp.muc_jid] = m

        self._by_discord = by_discord
        self._by_irc = by_irc
        self._by_xmpp = by_xmpp

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
        return self._by_discord.get(discord_channel_id)

    def get_mapping_for_irc(self, server: str, channel: str) -> ChannelMapping | None:
        """Get mapping for an IRC server/channel."""
        return self._by_irc.get((server, channel))

    def get_mapping_for_xmpp(self, muc_jid: str) -> ChannelMapping | None:
        """Get mapping for an XMPP MUC JID."""
        return self._by_xmpp.get(muc_jid)

    def all_mappings(self) -> list[ChannelMapping]:
        """Return all channel mappings."""
        return list(self._mappings)
