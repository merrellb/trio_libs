# Code by Brian Merrell
# Inspiration from Curio and Trio documentation and examples

import traceback
import trio
from wsproto.events import (ConnectionClosed, ConnectionRequested, ConnectionEstablished,
                            TextReceived, BytesReceived)

DATA_TYPES = (TextReceived, BytesReceived)


# Simple Websocket management
class AwaitableSet(set):

    def __init__(self, *args, **kwargs):
        set.__init__(self, *args, **kwargs)
        self.empty = trio.Event()
        self.empty.set()

    def add(self, *args, **kwargs):
        set.add(self, *args, **kwargs)
        self.empty.clear()

    def remove(self, *args, **kwargs):
        set.remove(self, *args, **kwargs)
        print("await", len(self))
        if not self:
            self.empty.set()

    async def shutdown_all(self):
        for conn in self:
            conn.shutdown.set()
        await self.empty.wait()

# Base class handles nursery and socket scoping plus KeyboardInterrupt


class RunnerBase():
    async def run(self):
        async with trio.open_nursery() as nursery:
            connection_manager = AwaitableSet()
            with trio.socket.socket() as socket:
                try:
                    await self.process(nursery, socket, connection_manager)
                except KeyboardInterrupt:
                    print("Keyboard")
                    await connection_manager.shutdown_all()
                    print("Done")


def cancellable_factory(func_name, ws_instance):
    func = getattr(ws_instance, func_name)
    async def scope_func():
        try:
            print(func_name, " {}: started".format(ws_instance.ident))
            with trio.open_cancel_scope() as cancel_scope:
                ws_instance.cancel_scopes.append(cancel_scope)
                await func()
        except Exception as exc:
            traceback.print_exc()
            print(func_name, " {}: crashed: {!r}".format(ws_instance.ident, exc))
            await ws_instance.shutdown.set()
        print(func_name, " {}: stopped".format(ws_instance.ident))
    return scope_func


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
        self.finished = trio.Event()
        self.in_q = trio.Queue(self.in_q_size)
        self.out_q = trio.Queue(self.out_q_size)
        self.cancel_scopes = []

    async def sendall(self):
        try:
            ws_bytes = self.wsconn.bytes_to_send()
            await self.web_sock.sendall(ws_bytes)
        except Exception:
            traceback.print_exc()
            print("Broken - sendall")
            self.shutdown.set()

    def run(self, nursery, all_ws):
        for func_name in ["generate", "send", "process", "recv"]:
            nursery.spawn(cancellable_factory(func_name, self))
        self.all_ws = all_ws
        self.all_ws.add(self)
        nursery.spawn(self.do_shutdown)

    async def close_conn(self):
        try:
            self.wsconn.close()
            await self.sendall()
        except Exception:
            pass  # Connection has already been closed

    async def do_shutdown(self):
        print("Awaiting shutdown event")
        await self.shutdown.wait()
        await self.close_conn()
        for cancel_scope in self.cancel_scopes:
            cancel_scope.cancel()
        await trio.sleep(0)
        self.all_ws.remove(self)
        self.finished.set()

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
