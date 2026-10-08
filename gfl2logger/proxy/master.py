import logging
from collections.abc import Sequence
from pathlib import Path

from mitmproxy import exceptions, log, master, options, optmanager
from mitmproxy.addons import next_layer, proxyserver

from gfl2logger.gfl2.logger import GFL2Logger
from gfl2logger.gui.manager import GUIManager, run_with_window
from gfl2logger.proxy.capture import default_capture_mode
from gfl2logger.proxy.ignore_tls import IgnoreTls
from gfl2logger.utils.paths import CONFIG_FILENAME, default_data_dir

logger = logging.getLogger(__name__)

addons = [
    GFL2Logger(),
    GUIManager(),
    IgnoreTls(),
    next_layer.NextLayer(),
    proxyserver.Proxyserver(),
]


class ProxyMaster(master.Master):
    def __init__(self):
        data_dir = default_data_dir()
        data_dir.mkdir(parents=True, exist_ok=True)

        opts = options.Options()
        opts.add_option(
            "mode", Sequence[str], [default_capture_mode()], help="Capture GF2 traffic"
        )
        opts.add_option("http2", bool, False, help="")
        opts.add_option("http3", bool, False, help="")
        opts.add_option("websocket", bool, False, help="")
        opts.add_option("confdir", str, str(data_dir), help="")

        super().__init__(opts, with_termlog=False)
        self.addons.add(*addons)
        config = Path(opts.confdir).joinpath(CONFIG_FILENAME)
        try:
            optmanager.load_paths(opts, config)
        except (exceptions.OptionsError, OSError) as error:
            # The app has no console; refusing to start over a damaged config file would
            # look like the app silently failing to open. Fall back to the defaults.
            logger.error(f"Ignoring unreadable configuration {config}, error={error}")

    async def run(self) -> None:
        logger.log(log.ALERT, f"Starting capture: {', '.join(self.options.mode)}")
        await run_with_window(self.addons.get("guimanager"), super().run)
