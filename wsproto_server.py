# Sample code by Brian Merrell
# Process incoming messages with simple reply

import trio
from wsproto.connection import WSConnection, SERVER
from ws_base import WebsocketBase
from runner_base import ServerRunner


class WebSocketServerConnection(WebsocketBase):

    def __init__(self, server_sock, ident, *args, **kwargs):
        self.ident = ident
        self.wsconn = WSConnection(SERVER)
        WebsocketBase.__init__(self, server_sock)

    async def process(self):
        while True:
            msg = await self.in_q.get()
            # Simple echo server
            await self.out_q.put(msg)


wss = ServerRunner(WebSocketServerConnection)
trio.run(wss.run)
