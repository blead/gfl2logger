import csv
import logging
from datetime import datetime, timezone

from mitmproxy import flow, log, tcp
from mitmproxy.utils import asyncio_utils

from gfl2logger import decoder, version
from gfl2logger.parser import GuildMembersParser

logger = logging.getLogger(__name__)


class GFL2Logger:
    def __init__(self) -> None:
        self.active_flows: dict[flow.Flow, GuildMembersParser] = {}

    async def save_data(self, data: bytes) -> None:
        log_time = datetime.now(timezone.utc)
        members_data = decoder.format_guild_members_data(
            decoder.decode_guild_members_data(data), log_time
        )

        logger.debug(str(members_data))

        filename = f"gfl2logger_guildmembers_{log_time.strftime('%Y%m%dT%H%M%SZ')}.csv"
        try:
            with open(filename, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(
                    f, fieldnames=decoder.GUILD_MEMBERS_DATA_COLS, extrasaction="ignore"
                )
                writer.writeheader()
                writer.writerows(members_data)
            logger.log(log.ALERT, f"Guild members data written to {filename}")
        except OSError as e:
            logger.error(f"Failed to write to {filename}, error={e}")

    async def running(self) -> None:
        logger.log(
            log.ALERT, f"{self.__class__.__name__} v{version.get_version()} is running"
        )

    async def tcp_start(self, flow: tcp.TCPFlow) -> None:
        self.active_flows[flow] = GuildMembersParser(
            lambda data: asyncio_utils.create_task(
                self.save_data(data),
                name=f"{self.__class__.__name__}:{self.save_data.__name__}",
                keep_ref=True,
            )
        )

    async def tcp_message(self, flow: tcp.TCPFlow) -> None:
        parser = self.active_flows.get(flow)
        if parser is None:
            logger.warning("message not in active flow")
            return

        message = flow.messages[-1]
        if parser.is_from_client_expected() == message.from_client:
            parser.on_message(message.content)

    async def tcp_end(self, flow: tcp.TCPFlow) -> None:
        self.active_flows.pop(flow, None)

    async def tcp_error(self, flow: tcp.TCPFlow) -> None:
        await self.tcp_end(flow)

    async def done(self) -> None:
        self.active_flows.clear()
