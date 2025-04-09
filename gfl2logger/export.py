from gfl2logger import ignore_tls, logger

addons = [
    ignore_tls.IgnoreTls(),
    logger.GFL2Logger(),
]
