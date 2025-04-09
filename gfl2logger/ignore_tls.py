from mitmproxy import tls


class IgnoreTls:
    async def tls_clienthello(self, data: tls.ClientHelloData):
        data.ignore_connection = True
