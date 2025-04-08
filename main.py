import asyncio
import logging
import signal
import sys

from mitmproxy import master, options
from mitmproxy.addons import next_layer, proxyserver, tlsconfig

from gfl2logger.export import addons


def get_master() -> master.Master:
    opts = options.Options(
        mode=["local:GF2_Exilium"], http2=False, http3=False, websocket=False
    )
    m = master.Master(
        opts,
        with_termlog=True,
    )
    m.addons.add(
        proxyserver.Proxyserver(),
        next_layer.NextLayer(),
        tlsconfig.TlsConfig(),
    )
    m.addons.add(*addons)
    opts.update(termlog_verbosity="alert")
    return m


async def run() -> master.Master:
    logging.getLogger().setLevel(logging.INFO)
    m = get_master()
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
    return m


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    sys.exit(main())
