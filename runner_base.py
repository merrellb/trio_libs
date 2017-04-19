# Code by Brian Merrell
import trio
from trio_util import AwaitableSet

# Base class handles nursery and socket scoping plus KeyboardInterrupt
class RunnerBase():
    def __init__(self, connection_cls, host="127.0.0.1", port=8080, *args, **kwargs):
        self.connection_cls = connection_cls
        self.host, self.port = host, port
        self.args = args
        self.kwargs = kwargs
    async def run(self):
        with trio.socket.socket() as socket:
            connection_manager = AwaitableSet()
            try:
                async with trio.open_nursery() as nursery:            
                        await self.process(nursery, socket, connection_manager)
            except KeyboardInterrupt:
                print("Keyboard")
                await connection_manager.shutdown_all()
                print("Done")

class ClientRunner(RunnerBase):
    async def process(self, nursery, sock, connection_manager):
        print("connecting to {}:{}".format(self.host, self.port))
        await sock.connect((self.host, self.port))
        print("socket connected")
        wsc = self.connection_cls(sock, "Singleton", self.host, self.port,
                                  *self.args, **self.kwargs)
        wsc.run(nursery, connection_manager)

class ServerRunner(RunnerBase):
    async def process(self, nursery, listen_sock, connection_manager):
        listen_sock.bind((self.host, self.port))
        listen_sock.listen()
        print("listening on {}:{}".format(self.host, self.port))
        ident = 0
        while True:
            sock, _ = await listen_sock.accept()
            print("listener: got new connection, spawning server")
            ident += 1
            wss = self.connection_cls(sock, ident, self.host, self.port,
                                      *self.args, **self.kwargs)
            wss.run(nursery, connection_manager)
