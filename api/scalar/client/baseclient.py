import scalar.protocol.encryption as encryption
import scalar.protocol.packets.protocol as protocol
import scalar.protocol.socket.protosocket as protosocket
import scalar.exceptions as exceptions
import scalar.primitives as primitives

import typing
import asyncio
import traceback
import random
import threading
import queue

VERSION = 1

class BaseClient:
    _socket: protosocket.ProtoSocket|None = None
    _username: str|None = None
    _original_username: str|None = None
    _fingerprint: str|None = None
    _implementation: str = 'base'
    _server_implementation: str|None = None
    _user: primitives.User|None = None
    _thread: bool = False
    _thread_host: threading.Thread = None
    _thread_event_out_queue: queue.Queue = None
    _thread_event_in_queue: queue.Queue = None
    # _thread_kill_event: threading.Event = None
    _running: bool = False

    def __init__(self, *, username: str|None = None):
        self._original_username = username

        @self.event("on_exception")
        def print_exception(self, e):
            print("Exception occured, ignoring")
            print("".join(traceback.format_exception(e))[:-1])

    def set_username(self, username: str|None):
        if self._running:
            raise exceptions.ClientConnected()
        self._original_username = username
    def get_username(self) -> str|None:
        return self._original_username
    def has_username(self) -> bool:
        return self._original_username is not None

    _keys: dict[str, typing.Any] = {}
    def load_key(self, key_type: str, key_bytes: bytes):
        try:
            keypair = encryption.SUPPORTED[key_type][1]
        except IndexError:
            raise exceptions.EncryptionKeysUnsupported()
        self._keys[key_type] = keypair.load(key_bytes)
    def save_key(self, key_type: str) -> bytes:
        if not key_type in self._keys:
            return None
        return self._keys[key_type].save()
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
    def _threaded_process_events(self):
        if self._thread_event_out_queue is None:
            return
        async def _asyncpart():
            while True:
                try:
                    event = self._thread_event_out_queue.get(False)
                    self._thread_event_out_queue.task_done()
                except queue.Empty:
                    return
                event_id, event_name, event_args, event_kwargs = event
                exception = False
                try:
                    result = await self._process_event(event_name, event_args, event_kwargs)
                except BaseException as e:
                    result = e
                    exception = True
                self._thread_event_in_queue.put((event_id, exception, result))
        asyncio.run(_asyncpart())
    def _threaded_invoke_event(self, event_name: str, *event_args: list[typing.Any], **event_kwargs: dict[str, typing.Any]):
        eid = random.randint(0, 65535)
        self._thread_event_out_queue.put((eid, event_name, event_args, event_kwargs))
        while True:
            out = self._thread_event_in_queue.get()
            self._thread_event_in_queue.task_done()
            if out[0] != eid:
                self._thread_event_in_queue.put(out)
                continue
            break
        if out[1]:
            raise out[2] from out[2]
        return out[2]
    async def _invoke_event(self, event_name: str, *event_args: list[typing.Any], **event_kwargs: dict[str, typing.Any]):
        if self._thread:
            return self._threaded_invoke_event(event_name, *event_args, **event_kwargs)
        res = None
        try:
            res = await self._process_event(event_name, event_args, event_kwargs)
        except BaseException as e:
            await self._process_event("on_exception", [e], {})
        return res
    async def _process_event(self, event_name: str, event_args: list[typing.Any], event_kwargs: dict[str, typing.Any]):
        if hasattr(self, "event_"+event_name):
            call = getattr(self, "event_"+event_name)(*event_args, **event_kwargs)
            if call is not None:
                await call
        if self._events.get(event_name) is None:
            return
        for event in self._events[event_name]:
            call = event(self, *event_args, **event_kwargs)
            if call is None:
                continue
            await call

    def connected(self) -> bool:
        return self._socket is not None

    async def connect(self, host: str, port: int):
        if not self.has_username():
            raise exceptions.ClientNoNameSpecified()
        
        self._running = True
        
        self._username = self._original_username

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
        self._user = primitives.User(self._username, self._fingerprint)
        await self._invoke_event('on_login_complete')

    def close(self):
        self._socket.close()
        self._socket = None
        self._running = False

    def run(self, host: str, port: int, we_be_thread: bool = False):
        self._thread = we_be_thread
        asyncio.run(self.serve(host, port))

    def start_thread(self, host: str, port: int):
        if self._running:
            raise exceptions.ClientThreadRunning()
        if self._thread_host is not None and self._thread_host.is_alive():
            raise exceptions.ClientThreadRunning()
        self._running = True
        # self._thread_kill_event = threading.Event()
        self._thread_event_out_queue = queue.Queue()
        self._thread_event_in_queue = queue.Queue()
        self._thread_host = threading.Thread(target=self.run, args=(host, port, True))
        self._thread_host.start()
    def end_thread(self):
        if not self._thread_host:
            raise exceptions.ClientThreadNotRunning()
        if self._thread_host == threading.current_thread():
            raise exceptions.ClientThreadSuicideImpossible()
        # self._thread_kill_event.set()
        # self._thread_host.join()
        # self._thread_kill_event.clear()
        self.close()
        self._thread_host.join(5.0)
        self._thread_host = None
        self._thread_queue = None

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
        self._fingerprint = encryption.fingerprint_key(encryptor.public_key())
        
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
        if stat == protosocket.SOCKET_TIMEOUT:
            return None
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
        await self._send_packet(protocol.SERVERBOUND_ImplementationInfo(implementation=self._implementation))
        self._server_implementation = (await self._recv_packet(protocol.CLIENTBOUND_ImplementationInfo)).implementation
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
                await self._send_packet(protocol.SERVERBOUND_SHeartbeat(nonce=expect_nonce))
                heartbeats_missed += 1
                if heartbeats_missed > 1:
                    await self._invoke_event("heartbeat_missed", heartbeats_missed-1)
            if heartbeats_missed >= 6:
                self.close()
                raise exceptions.ConnectionTimedOut()
            if not packet:
                continue
            if type(packet) is protocol.CLIENTBOUND_SHeartbeat:
                if packet.nonce == expect_nonce:
                    heartbeats_missed = 0
                continue

            # reply to client heartbeat (checking client responsiveness)
            if type(packet) is protocol.CLIENTBOUND_CHeartbeat:
                await self._invoke_event("heartbeat", packet.nonce)
                await self._send_packet(protocol.SERVERBOUND_CHeartbeat(nonce=packet.nonce))
                continue

            if type(packet) is protocol.CLIENTBOUND_Kick:
                self.close()
                raise exceptions.ClientKicked(packet.reason)
            
            queue.append(packet)
            if heartbeats_missed > 0:
                continue
            return queue
        
    async def _process_packet(self, packet_type: type, packet: protocol.packet.Packet):
        pass

    async def serve(self, host: str, port: int):
        await self.connect(host, port)
        while True:
            try:
                packets = await self.recv_packets()
            except exceptions.SocketBroken:
                return
            for packet in packets:
                await self._process_packet(type(packet), packet)