from scalar.server.baseserver import BaseServer
from scalar.server.implementations.scalar0.client import Scalar0Client
import scalar.primitives as primitives
import scalar.protocol.packets.protocol as protocol

class Scalar0Server(BaseServer):
    _client_class: type = Scalar0Client
    _implementation: str = 'scalar0'
    _userlist: list[primitives.User] = []
    
    async def event_on_login_complete(self, client: Scalar0Client):
        self._userlist.append(client._user)
        await self.broadcast(protocol.CLIENTBOUND_EventUserJoined(user=client._user))
        print(f"{client._user.username} joined")
        if client._client_implementation not in ('scalar0',):
            return
        
    async def event_on_socket_broken(self, client: Scalar0Client):
        self._userlist.remove(client._user)
        await self.broadcast(protocol.CLIENTBOUND_EventUserLeft(user=client._user))
        print(f"{client._user.username} left: disconnected")
    async def event_on_kick(self, client: Scalar0Client, reason: str):
        self._userlist.remove(client._user)
        await self.broadcast(protocol.CLIENTBOUND_EventUserLeft(user=client._user))
        print(f"{client._user.username} left: kicked: {reason}")
        
    async def send_message(self, message: str):
        await self.broadcast(protocol.CLIENTBOUND_ServerMessage(message=message))

    async def _process_packet(self, client: Scalar0Client, packet_type: type, packet: protocol.packet.Packet):
        if packet_type is protocol.SERVERBOUND_UserListRequest:
            return await client._send_packet(protocol.CLIENTBOUND_UserListResponse(users=self._userlist))
        if packet_type is protocol.SERVERBOUND_SendMessage:
            await self._invoke_event(client, "on_message", client._user, packet.message)
            return await self.broadcast(protocol.CLIENTBOUND_UserMessage(fingerprint=client._user.fingerprint, message=packet.message), [client])
