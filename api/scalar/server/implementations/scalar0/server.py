from scalar.server.baseserver import BaseServer
from scalar.server.implementations.scalar0.client import Scalar0Client
from scalar.server.implementations.scalar0.state import Scalar0ServerState
import scalar.primitives as primitives
import scalar.identifier as identifier
import scalar.protocol.packets.protocol as protocol

class Scalar0Server(BaseServer):
    _client_class: type = Scalar0Client
    _implementation: str = 'scalar0'
    _userlist: list[primitives.User] = None
    _channellist: list[primitives.Channel] = None
    _state: Scalar0ServerState = Scalar0ServerState()
    _identifier: identifier.Identifier = None
    _setup_done: bool = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._userlist = []
        self._channellist = []
        self._identifier = identifier.Identifier()
    
    def load_state(self, state):
        if self._setup_done:
            return
        self._state = state
        self._identifier.state = self._state.idenfifier_state

    def bind(self, *args, **kwargs):
        super().bind(*args, **kwargs)
        self._setup_done = True
        for cid, name in self._state.channels.items():
            messages = self._state.load_channel_messages(cid)
            self._channellist.append(primitives.Channel(cid, name, messages))
    
    async def event_on_login_complete(self, client: Scalar0Client):
        self._userlist.append(client._user)
        await self.broadcast(protocol.CLIENTBOUND_EventUserJoined(user=client._user))
        print(f"{client._user.username} joined")
        if client._client_implementation not in ('scalar0',):
            return
        
    async def event_on_socket_broken(self, client: Scalar0Client):
        if client._user in self._userlist:
            self._userlist.remove(client._user)
        await self.broadcast(protocol.CLIENTBOUND_EventUserLeft(fingerprint=client._user.fingerprint), [client])
        print(f"{client._user.username} left: disconnected")
    async def event_on_kick(self, client: Scalar0Client, reason: str):
        if client._user in self._userlist:
            self._userlist.remove(client._user)
        await self.broadcast(protocol.CLIENTBOUND_EventUserLeft(fingerprint=client._user.fingerprint), [client])
        print(f"{client._user.username} left: kicked: {reason}")
        
    async def send_message(self, channel: primitives.Channel, message: str):
        mid = self._identifier.get_identifier(identifier.UNIVERSE_MESSAGE)
        message = primitives.Message(mid=mid, channel=channel, author=None, content=message)
        channel.push_message(message)
        return await self.broadcast(protocol.CLIENTBOUND_ServerMessage(mid=mid, channel=channel.cid, message=message))
    
    async def _process_packet(self, client: Scalar0Client, packet_type: type, packet: protocol.packet.Packet):
        if packet_type is protocol.SERVERBOUND_UserListRequest:
            ulist = {}
            for user in self._userlist:
                ulist[user.fingerprint] = user.username
            return await client._send_packet(protocol.CLIENTBOUND_UserListResponse(users=ulist))
        if packet_type is protocol.SERVERBOUND_ChannelListRequest:
            clist = {}
            for channel in self._channellist:
                clist[channel.cid] = channel.name
            return await client._send_packet(protocol.CLIENTBOUND_ChannelListResponse(channels=clist))
        
        if packet_type is protocol.SERVERBOUND_SendMessage:
            mid = self._identifier.get_identifier(identifier.UNIVERSE_MESSAGE)
            channel = self.find_channel(packet.channel)
            message = primitives.Message(mid=mid, channel=channel, author=client._user, content=packet.message)
            channel.push_message(message)
            await self._invoke_event(client, "on_message", message)
            return await self.broadcast(protocol.CLIENTBOUND_UserMessage(mid=mid, channel=packet.channel, user=client._user.fingerprint, message=packet.message))

        
    def find_user_by_fingerprint(self, fingerprint: int) -> primitives.User|None:
        for user in self._userlist:
            if user.fingerprint != fingerprint:
                continue
            return user
        return None
    def find_channel(self, channel_id: int) -> primitives.Channel|None:
        for channel in self._channellist:
            if channel.cid != channel_id:
                continue
            return channel
        return None