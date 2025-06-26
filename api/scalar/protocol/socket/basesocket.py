import socket
import select
import asyncio
import time

import scalar.exceptions
from scalar.protocol.socket.constants import *

class BaseSocket:
    host: str = None
    port: int = None

    _socket: socket.socket = None
    _closed: bool = False
    _bound: bool = False
    def __init__(self, *, host: str, port: int):
        self.host = host
        self.port = port
        
    @classmethod
    def fromSocket(cls, host: str, port: int, socket: socket.socket):
        sock = cls(host=host, port=port)
        socket.settimeout(10)
        sock._socket = socket
        sock._closed = False
        sock._bound = False
        return sock

    def _socket_available(self):
        if self._socket is None:
            return False
        if self._closed:
            return False
        return True
    
    def _close(self):
        if not self._socket_available():
            raise scalar.exceptions.SocketLeadsToVoid("Attempt to close a void socket")
        self._socket.shutdown(socket.SHUT_RDWR)
        self._socket.close()
        del self._socket
        self._socket = None
        self._closed = True
        self._bound = False

    async def _recv(self, amount: int) -> bytes:
        if not self._socket_available():
            raise scalar.exceptions.SocketLeadsToVoid("Attempt to receive data from a void socket")
        received = b""
        started = time.time()
        while len(received) < amount:
            await asyncio.sleep(0)
            try:
                while True:
                    if time.time() - started > self._socket.gettimeout():
                        raise scalar.exceptions.SocketTimedOut()
                    try:
                        ready1, _, ready2 = select.select([self._socket], [], [self._socket], 0)
                    except ValueError:
                        raise scalar.exceptions.SocketBroken(f"Socket file descriptor became invalid value")
                    if not ready1 and not ready2:
                        await asyncio.sleep(0)
                        continue
                    break
                r = self._socket.recv(amount - len(received))
            except socket.timeout:
                raise scalar.exceptions.SocketTimedOut()
            except OSError as e:
                self._close()
                raise scalar.exceptions.SocketBroken(f"OSError: {e.strerror}")
            if len(r) == 0:
                self._close()
                raise scalar.exceptions.SocketBroken("Length of zero on recv call")
            received += r
        return received
    
    async def _send(self, data: bytes) -> None:
        if not self._socket_available():
            raise scalar.exceptions.SocketLeadsToVoid("Attempt to send data to a void socket")
        try:
            sent = 0
            while sent < len(data):
                await asyncio.sleep(0)
                sent += self._socket.send(data[sent:])
        except socket.timeout:
            raise scalar.exceptions.SocketTimedOut()
        except OSError as e:
            self._close()
            raise scalar.exceptions.SocketBroken(f"OSError: {e.strerror}")
    
    async def _accept(self):
        if not self._socket_available():
            raise scalar.exceptions.SocketLeadsToVoid("Attempt to accept connection from a void socket")
        if not self._bound:
            raise scalar.exceptions.SocketAlreadyConnected("Socket is connected socket, not a bound one")
        while True:
            ready, _, _ = select.select([self._socket], [], [], 0)
            if not ready:
                await asyncio.sleep(0)
                continue
            conn, addr = self._socket.accept()
            return addr, conn

    def bind(self, max_connections: int):
        if self._socket_available():
            raise scalar.exceptions.SocketAlreadyConnected("Socket already bound")
        # del self._socket
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.bind((self.host, self.port))
        self._socket.listen(max_connections)
        self._closed = False
        self._bound = True

    def connect(self):
        if self._socket_available():
            raise scalar.exceptions.SocketAlreadyConnected("Socket already connected")
        # del self._socket
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.settimeout(120)
        try:
            self._socket.connect((self.host, self.port))
        except socket.error as exc:
            del self._socket
            raise
        self._socket.settimeout(10)
        self._closed = False
        self._bound = False

    def close(self) -> int:
        try:
            self._close()
            return SOCKET_SUCCESS
        except scalar.exceptions.SocketLeadsToVoid:
            return SOCKET_UNBOUND

    async def recv(self, amount: int) -> tuple[int, bytes|None]:
        try:
            return SOCKET_SUCCESS, await self._recv(amount)
        except scalar.exceptions.SocketLeadsToVoid:
            return SOCKET_UNBOUND, None
        except scalar.exceptions.SocketBroken:
            return SOCKET_BROKENP, None
        except scalar.exceptions.SocketTimedOut:
            return SOCKET_TIMEOUT, None
        
    async def send(self, data: bytes) -> int:
        try:
            await self._send(data)
            return SOCKET_SUCCESS
        except scalar.exceptions.SocketLeadsToVoid:
            return SOCKET_UNBOUND
        except scalar.exceptions.SocketBroken:
            return SOCKET_BROKENP
        except scalar.exceptions.SocketTimedOut:
            return SOCKET_TIMEOUT
        
    async def accept(self):
        try:
            addr, conn = await self._accept()
            sock = type(self).fromSocket(addr[0], addr[1], conn)
            sock._bound = True
            return addr, sock
        except scalar.exceptions.SocketLeadsToVoid:
            return None, None
        except scalar.exceptions.SocketAlreadyConnected:
            return None, None