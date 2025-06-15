import scalar.protocol.encryption as encryption
import scalar.protocol.packets.protocol as protocol
import scalar.protocol.socket.protosocket as protosocket
import scalar.exceptions as exceptions

import scalar.server.baseclient as client

import threading
import typing
import asyncio
import traceback

VERSION = 1

class BaseServer:
    _socket: protosocket.ProtoSocket|None = None
    _clients: dict[str, client.Client] = {}
    _keys: dict[str, typing.Any] = {}
    _client_class: type = client.BaseClient
    _implementation: str = 'base'
    def __init__(self):
        @self.event("on_exception")
        def print_exception(self, client, e):
            print(f"Exception occured for client {client.format_address()}, ignoring")
            print("".join(traceback.format_exception(e))[:-1])

    def bind(self, host: str, port: int):
        self._socket = protosocket.ProtoSocket(
            host=host,
            port=port,
            encryption=encryption.BaseEncryption # aka no encryption
        )
        self._socket.bind(128)

    _events: dict[str, list[typing.Callable]] = {}
    def event(self, event_name: str):
        if self._events.get(event_name) is None:
            self._events[event_name] = []
        def _inner_decorator(func: typing.Callable):
            if func in self._events[event_name]:
                return func
            self._events[event_name].append(func)
            return func
        return _inner_decorator
    async def _invoke_event(self, client: client.Client, event_name: str, *event_args: list[typing.Any], **event_kwargs: dict[str, typing.Any]):
        if self._events.get(event_name) is None:
            return
        if hasattr(self, "event_"+event_name):
            try:
                call = getattr(self, "event_"+event_name)(*event_args, **event_kwargs)
                if call is not None:
                    await call
            except BaseException as e:
                await self._invoke_event("on_exception", e)
        for event in self._events[event_name]:
            try:
                call = event(self, client, *event_args, **event_kwargs)
                if call is None:
                    continue
                await call
            except BaseException as e:
                await self._invoke_event(client, "on_exception", e)

    def load_key(self, key_type: str, key_bytes: bytes):
        try:
            keypair = encryption.SUPPORTED[key_type][1]
        except IndexError:
            raise exceptions.EncryptionKeysUnsupported()
        self._keys[key_type] = keypair.load(key_bytes)
    def generate_key(self, key_type: str):
        try:
            keypair = encryption.SUPPORTED[key_type][1]
        except IndexError:
            raise exceptions.EncryptionKeysUnsupported()
        self._keys[key_type] = keypair.generate()

    def run(self):
        asyncio.run(self.serve())
    
    async def serve(self):
        while True:
            addr, sock = await self._socket.accept()
            if addr is None:
                raise exceptions.SocketBroken()
            stat, packet = await sock.recv_packet()
            if stat != protosocket.SOCKET_SUCCESS:
                continue
            if type(packet) is not protocol.SERVERBOUND_HANDSHAKE_Hello:
                await sock.send_packet(protocol.CLIENTBOUND_Kick(reason=f"Expected SERVERBOUND_HANDSHAKE_Hello, got {type(packet).__name__}"))
                sock.close()
                continue
            if packet.version != VERSION:
                await sock.send_packet(protocol.CLIENTBOUND_Kick(reason=f"Mismatched versions: Client={packet.version}, Server={VERSION}"))
                sock.close()
                continue
            if await sock.send_packet(protocol.CLIENTBOUND_HANDSHAKE_Hello(version=VERSION)) != protosocket.SOCKET_SUCCESS:
                continue
            cl = self._client_class(self, addr, sock)
            self._clients[cl.format_address()] = cl
            threading.Thread(target=cl.run, daemon=True).start()
            
    def clients(self):
        clients = self._clients.copy()
        for client in clients.values():
            yield client

    async def broadcast(self, packet: protocol.packet.Packet, except_clients: list):
        for client in self.clients():
            if client in except_clients: continue
            await client._send_packet(packet)

    async def _process_packet(self, client, packet_type: type, packet: protocol.packet.Packet):
        pass
