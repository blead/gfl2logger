import logging

from mitmproxy import optmanager

logger = logging.getLogger(__name__)


class GFL2OptManagerWrapper(optmanager.OptManager):
    def __init__(self, optmanager: optmanager.OptManager):
        self.optmanager = optmanager
        self._options = optmanager._options

    def keys(self) -> set[str]:
        s = {k for k in self.optmanager.keys() if k.startswith("gfl2_")}
        return s
