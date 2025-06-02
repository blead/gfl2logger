import logging

from mitmproxy import addonmanager, flow, log, tcp

from gfl2logger.gfl2 import data
from gfl2logger.gfl2.parser import GFL2Parser
from gfl2logger.utils import version

logger = logging.getLogger(__name__)


class GFL2Logger:
    def __init__(self) -> None:
        self.active_flows: dict[flow.Flow, GFL2Parser] = {}

    def load(self, loader: addonmanager.Loader) -> None:
        data.add_options(loader)

    async def running(self) -> None:
        logger.log(
            log.ALERT, f"{self.__class__.__name__} v{version.get_version()} is running"
        )

    async def tcp_start(self, flow: tcp.TCPFlow) -> None:
        self.active_flows[flow] = GFL2Parser()

    async def tcp_message(self, flow: tcp.TCPFlow) -> None:
        parser = self.active_flows.get(flow)
        if parser is None:
            logger.warning("Message not in active flow")
            return

        message = flow.messages[-1]

        # TODO: parse client/server messages separately; currently we just ignore client
        if not message.from_client:
            await parser.on_message(message.content)

    async def tcp_end(self, flow: tcp.TCPFlow) -> None:
        if flow in self.active_flows:
            self.active_flows[flow].stop()
        self.active_flows.pop(flow, None)

    async def tcp_error(self, flow: tcp.TCPFlow) -> None:
        await self.tcp_end(flow)

    async def done(self) -> None:
        for parser in self.active_flows.values():
            parser.stop()
        self.active_flows.clear()
