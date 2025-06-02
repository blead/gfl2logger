import asyncio
import logging
import multiprocessing
import signal
import sys

from mitmproxy import log

from gfl2logger.proxy.master import ProxyMaster


async def run() -> None:
    logging.getLogger().setLevel(log.ALERT)
    m = ProxyMaster()
    loop = asyncio.get_running_loop()

    def _sigint(*_):
        loop.call_soon_threadsafe(m.shutdown)

    def _sigterm(*_):
        loop.call_soon_threadsafe(m.shutdown)

    try:
        loop.add_signal_handler(signal.SIGINT, _sigint)
        loop.add_signal_handler(signal.SIGTERM, _sigterm)
    except NotImplementedError:
        signal.signal(signal.SIGINT, _sigint)
        signal.signal(signal.SIGTERM, _sigterm)

    if hasattr(signal, "SIGPIPE"):
        signal.signal(signal.SIGPIPE, signal.SIG_IGN)

    await m.run()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    multiprocessing.freeze_support()
    sys.exit(main())
