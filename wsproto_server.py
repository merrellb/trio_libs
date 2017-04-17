# Sample code by Brian Merrell
# Process incoming messages with simple reply

import trio
from ws_base import WebsocketBase, RunnerBase
from wsproto.connection import WSConnection, SERVER


class WebSocketServerConnection(WebsocketBase):

    def __init__(self, server_sock, ident):
        self.ident = ident
        self.wsconn = WSConnection(SERVER)
        WebsocketBase.__init__(self, server_sock)

    async def process(self):
        while True:
            msg = await self.in_q.get()
            # Simple echo server
            await self.out_q.put(msg)


class WSServerRunner(RunnerBase):

    def __init__(self, ws_server_process, host="127.0.0.1", port=8080):
        self.host, self.port = host, port
        self.ws_server_process = ws_server_process

    async def process(self, nursery, listen_sock, all_ws):
        listen_sock.bind((self.host, self.port))
        listen_sock.listen()
        print("ws_listener: listening on {}:{}".format(self.host, self.port))
        ident = 0
        while True:
            web_sock, _ = await listen_sock.accept()
            print("echo_listener: got new connection, spawning echo_server", len(all_ws))
            ident += 1
            wss = self.ws_server_process(web_sock, ident)
            wss.run(nursery, all_ws)


wss = WSServerRunner(WebSocketServerConnection)
trio.run(wss.run)
