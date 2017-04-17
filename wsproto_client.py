# Code by Brian Merrell
# Generate task sends the current time
# Process task measures the throughput and latency of echoes

import time
import trio
from wsproto.connection import WSConnection, CLIENT
from ws_base import WebsocketBase, RunnerBase


class WebSocketClientConnection(WebsocketBase):

    def __init__(self, client_sock, host="", port=8080, path=''):
        self.wsconn = WSConnection(CLIENT, host+":"+str(port), path)
        self.host, self.port, self.path = host, port, path
        WebsocketBase.__init__(self, client_sock)

    async def generate(self):
        count = 100000
        start_time = time.time()
        for i in range(count):
            msg = str(time.time())
            await self.out_q.put(msg)  # {} message".format(i).encode('utf8'))
        print(count / (time.time() - start_time))

    async def process(self):
        count = 0
        start_time = None
        while True:
            msg = await self.in_q.get()
            current_time = time.time()
            if not start_time:
                start_time = current_time
            count += 1
            if count % 1000 == 0:
                sent_time = float(msg)
                throughput = count / (current_time - start_time)
                latency = current_time - sent_time
                print("Latency:", latency, "Throughput:", throughput, "/sec")


class WSClientRunner(RunnerBase):

    def __init__(self, ws_client_process, host="127.0.0.1", port=8080, path='/'):
        self.host, self.port, self.path = host, port, path
        self.ws_client_process = ws_client_process

    async def process(self, nursery, web_sock, all_ws):
        print("connecting to {}:{}{}".format(self.host, self.port, self.path))
        await web_sock.connect((self.host, self.port))
        print("socket connected")
        wsc = self.ws_client_process(web_sock, self.host, self.port, self.path)
        wsc.run(nursery, all_ws)
        await wsc.finished.wait()

wsc = WSClientRunner(WebSocketClientConnection)
trio.run(wsc.run)
