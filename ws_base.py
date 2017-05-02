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
        self.in_q = trio.Queue(self.in_q_size)
        self.out_q = trio.Queue(self.out_q_size)

    async def sendall(self):
        try:
            ws_bytes = self.wsconn.bytes_to_send()
            await self.web_sock.sendall(ws_bytes)
        except Exception:
            print("Broken - sendall", self.ident)
            print(ws_bytes)
            await self.shutdown()

    async def run(self):
        try:
            async with trio.open_nursery() as self.nursery:
                for func_name in ["generate", "send", "process", "recv"]:
                    self.nursery.spawn(cancellable_factory(func_name, self))
        finally:
            with trio.open_cancel_scope(shield=True):
                await self.send_close_conn()

    async def send_close_conn(self):
        try:
            print("Closing Connection")
            self.wsconn.close()
            await self.sendall()
            print("Close sent")
            await trio.sleep(0)
        except Exception as exc:
            print("Can't send close")
            pass  # Connection has already been closed

    async def shutdown(self):
        self.nursery.cancel_scope.cancel()
        await trio.sleep(0)

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
                print("No data - recv", self.ident)
                await self.shutdown()
            self.wsconn.receive_bytes(data)
            for event in self.wsconn.events():
                cl = event.__class__
                if cl in DATA_TYPES:
                    await self.in_q.put(event.data)
                elif cl is ConnectionRequested:
                    print("Accepting Connection")
                    self.wsconn.accept(event)
                elif cl is ConnectionEstablished:
                    print("Connection Established")
                elif cl is ConnectionClosed:
                    print("Connection Remotely Closed")
                    await self.shutdown()
                else:
                    print("Surprised:", event)

    #subclass me
    async def process(self):
        pass

    async def generate(self):
        pass
