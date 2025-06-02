from collections.abc import Sequence
from pathlib import Path

from mitmproxy import master, options, optmanager
from mitmproxy.addons import next_layer, proxyserver

from gfl2logger.gfl2.logger import GFL2Logger
from gfl2logger.gui.manager import GUIManager
from gfl2logger.proxy.ignore_tls import IgnoreTls

addons = [
    GFL2Logger(),
    GUIManager(),
    IgnoreTls(),
    next_layer.NextLayer(),
    proxyserver.Proxyserver(),
]


class ProxyMaster(master.Master):
    def __init__(self):
        opts = options.Options()
        opts.add_option("mode", Sequence[str], ["local:GF2_Exilium"], help="")
        opts.add_option("http2", bool, False, help="")
        opts.add_option("http3", bool, False, help="")
        opts.add_option("websocket", bool, False, help="")
        opts.add_option("confdir", str, str(Path.cwd()), help="")

        super().__init__(opts, with_termlog=False)
        self.addons.add(*addons)
        optmanager.load_paths(
            opts, Path(opts.confdir).joinpath("gfl2logger.config.yaml")
        )
