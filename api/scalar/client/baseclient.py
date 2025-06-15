import scalar.protocol.encryption as encryption
import scalar.protocol.packets.protocol as protocol
import scalar.protocol.socket.protosocket as protosocket
import scalar.exceptions as exceptions

import typing
import asyncio
import traceback
import random
import threading

VERSION = 1

class BaseClient:
    _socket: protosocket.ProtoSocket|None = None
    _username: str = ''
    _original_username: str = ''
    def __init__(self, *, username: str):
        self._original_username = username
        self._username = username

        @self.event("on_exception")
        def print_exception(self, e):
            print("Exception occured, ignoring")
            print("".join(traceback.format_exception(e))[:-1])

    _keys: dict[str, typing.Any] = {}
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
    async def _invoke_event(self, event_name: str, *event_args: list[typing.Any], **event_kwargs: dict[str, typing.Any]):
        if self._events.get(event_name) is None:
            return
        for event in self._events[event_name]:
            try:
                call = event(self, *event_args, **event_kwargs)
                if call is None:
                    continue
                await call
            except BaseException as e:
                await self._invoke_event("on_exception", e)

    async def connect(self, host: str, port: int):
        self._socket = protosocket.ProtoSocket(
            host=host,
            port=port,
            encryption=encryption.BaseEncryption # aka no encryption
        )
        self._socket.connect()
        self._socket._socket.settimeout(10)
        if not await self._protocol_connect():
            raise exceptions.ClientConnectionError()
        if not await self._protocol_login():
            raise exceptions.ClientConnectionError()
        await self._invoke_event('on_login_complete')

    def close(self):
        self._socket.close()
        del self._socket
        self._socket = False

    def run(self, host: str, port: int):
        asyncio.run(self.serve(host, port))

    def run_thread(self, host: str, port: int):
        threading.Thread(target=self.run, args=(host, port)).start()

    async def _protocol_connect(self):
        if await self._socket.send_packet(protocol.SERVERBOUND_HANDSHAKE_Hello(version=VERSION)) != protosocket.SOCKET_SUCCESS:
            return False
        
        stat, packet = await self._socket.recv_packet()
        if stat != protosocket.SOCKET_SUCCESS:
            return False
        if type(packet) is protocol.CLIENTBOUND_Kick:
            await self._invoke_event("on_kicked", packet.reason)
            raise exceptions.ClientKicked(packet.reason)
        if type(packet) is not protocol.CLIENTBOUND_HANDSHAKE_Hello:
            self.close()
            raise exceptions.UnexpectedPacket(f"Expected CLIENTBOUND_HANDSHAKE_Hello, got {type(packet).__name__}")
        
        await self._invoke_event("on_hello")

        if await self._socket.send_packet(protocol.SERVERBOUND_HANDSHAKE_EncryptionSupported(encryptions=list(encryption.SUPPORTED.keys()))) != protosocket.SOCKET_SUCCESS:
            return False
        
        stat, packet = await self._socket.recv_packet()
        if stat != protosocket.SOCKET_SUCCESS:
            return False
        if type(packet) is protocol.CLIENTBOUND_Kick:
            await self._invoke_event("on_kicked", packet.reason)
            raise exceptions.ClientKicked(packet.reason)
        if type(packet) is not protocol.CLIENTBOUND_HANDSHAKE_EncryptionSelect:
            self.close()
            raise exceptions.UnexpectedPacket(f"Expected CLIENTBOUND_HANDSHAKE_EncryptionSelect, got {type(packet).__name__}")
        
        selected_name = list(encryption.SUPPORTED.keys())[packet.select]
        selected = encryption.SUPPORTED[selected_name]

        encryptor: encryption.BaseEncryption = None
        if selected[1] is not None:
            try:
                keypair = self._keys[selected_name]
            except IndexError:
                raise exceptions.ClientNoKeyProvided()
            encryptor = selected[0](keypair)
        else:
            encryptor = selected[0]()
        
        if await self._socket.send_packet(protocol.SERVERBOUND_HANDSHAKE_EncryptionPubKey(key=encryptor.public_key())) != protosocket.SOCKET_SUCCESS:
            return False
        
        stat, packet = await self._socket.recv_packet()
        if stat != protosocket.SOCKET_SUCCESS:
            return False
        if type(packet) is protocol.CLIENTBOUND_Kick:
            await self._invoke_event("on_kicked", packet.reason)
            raise exceptions.ClientKicked(packet.reason)
        if type(packet) is not protocol.CLIENTBOUND_HANDSHAKE_EncryptionPubKey:
            self.close()
            raise exceptions.UnexpectedPacket(f"Expected CLIENTBOUND_HANDSHAKE_EncryptionPubKey, got {type(packet).__name__}")
        
        encryptor.exchange(packet.key)
        self._socket.set_encryption(encryptor)

        await self._invoke_event("on_encrypted", packet.key)
        
        return True
    
    async def _send_packet(self, packet: protocol.packet.Packet):
        if await self._socket.send_packet(packet) != protosocket.SOCKET_SUCCESS:
            await self._invoke_event("on_socket_broken")
            raise exceptions.SocketBroken("Socket closed when sending packet")
        await self._invoke_event("on_packet_sent", packet)
        
    async def _recv_packet(self, expect: protocol.packet.Packet|None = None) -> protocol.packet.Packet:
        stat, packet = await self._socket.recv_packet()
        if stat != protosocket.SOCKET_SUCCESS:
            await self._invoke_event("on_socket_broken")
            raise exceptions.SocketBroken("Socket closed when receiving packet")
        await self._invoke_event("on_packet_received", packet)
        if type(packet) is expect:
            return packet
        if type(packet) is protocol.CLIENTBOUND_Kick:
            await self._invoke_event("on_kicked", packet.reason)
            raise exceptions.ClientKicked(packet.reason)
        if expect is not None and type(packet) is not expect:
            self.close()
            raise exceptions.UnexpectedPacket(f"Expected {expect.__name__}, got {type(packet).__name__}")

        return packet

    async def _protocol_login(self):
        await self._send_packet(protocol.SERVERBOUND_LOGIN_UserInfo(username=self._username))
        agreed_uinfo = await self._recv_packet(protocol.CLIENTBOUND_LOGIN_UserInfo)
        self._username = agreed_uinfo.username
        await self._invoke_event("on_uinfo_negotiated", self._username)
        return True
    
    async def recv_packets(self):
        heartbeats_missed = 0
        queue = []
        expect_nonce = None
        while True:
            packet = await self._recv_packet()

            # send server heartbeat (check server responsiveness)
            if not packet:
                expect_nonce = random.randint(0, 65535)
                await self._send_packet(protocol.CLIENTBOUND_SHeartbeat(nonce=expect_nonce))
                heartbeats_missed += 1
                await self._invoke_event("heartbeat_missed", heartbeats_missed)
            if heartbeats_missed >= 6:
                self.close()
                raise exceptions.ConnectionTimedOut()
            if not packet:
                continue
            if type(packet) is protocol.SERVERBOUND_SHeartbeat:
                if packet.nonce == expect_nonce:
                    heartbeats_missed = 0
                continue

            # reply to client heartbeat (checking client responsiveness)
            if type(packet) is protocol.SERVERBOUND_CHeartbeat:
                await self._invoke_event("heartbeat", packet.nonce)
                await self._send_packet(protocol.CLIENTBOUND_CHeartbeat(nonce=packet.nonce))
                continue
            
            queue.append(packet)
            if heartbeats_missed > 0:
                continue
            return queue
        
    async def _process_packet(packet_type: type, packet: protocol.packet.Packet):
        pass

    async def serve(self, host: str, port: int):
        await self.connect(host, port)
        while True:
            for packet in await self.recv_packets():
                await self._process_packet(type(packet), packet)