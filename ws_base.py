# Code by Brian Merrell
# Inspiration from Curio and Trio documentation and examples

import trio
from wsproto.events import (ConnectionClosed, ConnectionRequested,
                            ConnectionEstablished, TextReceived,
                            BytesReceived)
DATA_TYPES = (TextReceived, BytesReceived)

from trio_util import cancellable_factory

# Websocket Base class.
# Initializes four tasks
# recv and send move messages between websocket and queues
# generate and process should be subclassed with stuff to do
class WebsocketBase:
    ident = "Singleton"
    in_q_size = 1
    out_q_size = 1
    BUFSIZE = 16384

    def __init__(self, web_sock):
        self.web_sock = web_sock
        self.shutdown = trio.Event()
        self.in_q = trio.Queue(self.in_q_size)
        self.out_q = trio.Queue(self.out_q_size)
        self.cancel_scopes = []

    async def sendall(self):
        try:
            ws_bytes = self.wsconn.bytes_to_send()
            await self.web_sock.sendall(ws_bytes)
        except Exception:
            print("Broken - sendall")
            self.shutdown.set()

    def run(self, nursery, all_ws):
        for func_name in ["generate", "send", "process", "recv"]:
            nursery.spawn(cancellable_factory(func_name, self))
        self.all_ws = all_ws
        self.all_ws.add(self)
        nursery.spawn(self.shutdown_wait)

    async def close_conn(self):
        try:
            self.wsconn.close()
            await self.sendall()
        except Exception:
            pass  # Connection has already been closed

    async def shutdown_wait(self):
        print("Awaiting shutdown event")
        await self.shutdown.wait()
        print("Shutdown Event")
        await self.do_shutdown()

    async def do_shutdown(self):
        await self.close_conn()
        for cancel_scope in self.cancel_scopes:
            cancel_scope.cancel()
        self.all_ws.remove(self)

    async def send(self):
        await self.sendall()
        while True:
            data = await self.out_q.get()
            self.wsconn.send_data(data)
            await self.sendall()

    async def recv(self):
        while True:
            data = await self.web_sock.recv(self.BUFSIZE)
            if not data:
                print("No data - recv")
                self.shutdown.set()
                return
            self.wsconn.receive_bytes(data)
            for event in self.wsconn.events():
                cl = event.__class__
                if cl in DATA_TYPES:
                    await self.in_q.put(event.data)
                elif cl is ConnectionRequested:
                    print("AcceptingConnection")
                    self.wsconn.accept(event)
                elif cl is ConnectionEstablished:
                    print("ConnectionEstablished")
                elif cl is ConnectionClosed:
                    print("Closed by Client")
                    self.shutdown.set()
                    return
                else:
                    print("Surprised:", event)

    #subclass me
    async def process(self):
        pass

    async def generate(self):
        pass
