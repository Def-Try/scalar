import asyncio
import typing

import scalar.protocol.encryption as encryption
import scalar.protocol.socket.protosocket as protosocket
import scalar.protocol.packets.protocol as protocol

ALLOWED_USERNAME_CHARACTERS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._"

class Client:
    _address: tuple[str, int] = None
    _socket: protosocket.ProtoSocket = None

    _logged_in: bool = False
    _username: str = ''
    _original_username: str = ''
    _username_n: int = 0
    def __init__(self, server, addr: tuple[str, int], sock: protosocket.ProtoSocket):
        self._server = server
        self._address = addr
        self._socket = sock
        sock._socket.settimeout(10)

    def format_address(self):
        return f"{self._address[0]}:{self._address[1]}"
    
    def _end_it_all(self):
        self._logged_in = False
        del self._server._clients[self.format_address()]
        self._socket.close()
        exit(0) # we're a thread, kill ourselves

    async def kick(self, reason: str = "No reason specified"):
        await self._socket.send_packet(protocol.CLIENTBOUND_Kick(reason=reason))
        self._end_it_all()
    
    def run(self):
        asyncio.run(self.serve())

    async def serve(self):
        await self._protocol_connect()
        await self._protocol_login()
        await self._invoke_event('on_login_complete')

    async def _invoke_event(self, event_name: str, *event_args: list[typing.Any], **event_kwargs: dict[str, typing.Any]):
        return await self._server._invoke_event(self, event_name, *event_args, **event_kwargs)

    async def _protocol_connect(self):
        await self._invoke_event("on_hello")

        stat, packet = await self._socket.recv_packet()
        if stat != protosocket.SOCKET_SUCCESS:
            return self._end_it_all()
        if type(packet) is not protocol.SERVERBOUND_HANDSHAKE_EncryptionSupported:
            return self.kick(f"Expected SERVERBOUND_HANDSHAKE_EncryptionSupported, got {type(packet).__name__}")
        selected = None
        for i in range(len(packet.encryptions)-1, -1, -1):
            if packet.encryptions[i] not in encryption.SUPPORTED:
                continue
            selected = i
            break
        if selected is None:
            return self.kick(f"Couldn't agree on encryption")
        
        if await self._socket.send_packet(protocol.CLIENTBOUND_HANDSHAKE_EncryptionSelect(select=selected)) != protosocket.SOCKET_SUCCESS:
            return self._end_it_all()
        
        selected_name = packet.encryptions[selected]
        selected = encryption.SUPPORTED[selected_name]

        stat, packet = await self._socket.recv_packet()
        if stat != protosocket.SOCKET_SUCCESS:
            return self._end_it_all()
        if type(packet) is not protocol.SERVERBOUND_HANDSHAKE_EncryptionPubKey:
            return await self.kick(f"Expected SERVERBOUND_HANDSHAKE_EncryptionPubKey, got {type(packet).__name__}")
        
        encryptor = selected[0](selected[1].load(self._server._keys[selected_name].save()))
        encryptor.exchange(packet.key)

        if await self._socket.send_packet(protocol.SERVERBOUND_HANDSHAKE_EncryptionPubKey(key=encryptor.public_key())) != protosocket.SOCKET_SUCCESS:
            return self._end_it_all()
        
        self._socket.set_encryption(encryptor)

        await self._invoke_event("on_encrypted", packet.key)

    async def _send_packet(self, packet: protocol.packet.Packet):
        if await self._socket.send_packet(packet) != protosocket.SOCKET_SUCCESS:
            await self._invoke_event("on_socket_broken")
            return self._end_it_all()
        await self._invoke_event("on_packet_sent", packet)
        
    async def _recv_packet(self, expect: protocol.packet.Packet|None = None) -> protocol.packet.Packet:
        stat, packet = await self._socket.recv_packet()
        if stat != protosocket.SOCKET_SUCCESS:
            await self._invoke_event("on_socket_broken")
            return self._end_it_all()
        await self._invoke_event("on_packet_received", packet)
        if type(packet) is expect:
            return packet
        if expect is not None and type(packet) is not expect:
            await self._invoke_event("on_kick")
            return await self.kick(f"Expected {expect.__name__}, got {type(packet).__name__}")

        return packet
    
    async def _protocol_login(self):
        uinfo = await self._recv_packet(protocol.SERVERBOUND_LOGIN_UserInfo)
        self._original_username = uinfo.username
        if any(ch not in ALLOWED_USERNAME_CHARACTERS for ch in self._original_username):
            return self.kick("Unallowed characters in username")
        for client in self._server.clients():
            if client._original_username != uinfo.username: continue
            if client == self: continue
            self._username_n = max(client._username_n + 1, self._username_n)
        self._username = self._original_username
        if self._username_n != 0:
            self._username += f"_{self._username_n}"
        await self._send_packet(protocol.CLIENTBOUND_LOGIN_UserInfo(username=self._username))
        await self._invoke_event("on_uinfo_negotiated", self._username)

        self._logged_in = True

        return True