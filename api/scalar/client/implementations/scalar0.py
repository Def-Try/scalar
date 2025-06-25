from scalar.client.baseclient import BaseClient
import scalar.primitives as primitives
import scalar.protocol.packets.protocol as protocol

class Scalar0Client(BaseClient):
    _userlist: list[primitives.User] = None
    _channellist: list[primitives.Channel] = None
    _implementation: str = 'scalar0'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._userlist = []
        self._channellist = []

    async def event_on_login_complete(self):
        if self._server_implementation not in ('scalar0',):
            return
        await self._send_packet(protocol.SERVERBOUND_UserListRequest())
        await self._send_packet(protocol.SERVERBOUND_ChannelListRequest())

            
    async def send_message(self, channel: primitives.Channel, message: str):
        await self._send_packet(protocol.SERVERBOUND_SendMessage(channel=channel.cid, message=message))
    async def edit_message(self, message_id: int, new_message: str):
        await self._send_packet(protocol.SERVERBOUND_EditMessage(mid=message_id, message=new_message))
    async def delete_message(self, message_id: int):
        await self._send_packet(protocol.SERVERBOUND_DeleteMessage(mid=message_id))

    async def _process_packet(self, packet_type: type, packet: protocol.packet.Packet):
        if packet_type is protocol.CLIENTBOUND_UserListResponse:
            self._userlist = []
            for fingerprint, name in packet.users.items():
                self._userlist.append(primitives.User(fingerprint=fingerprint, username=name))
            await self._invoke_event("on_userlist_received")
            return
        if packet_type is protocol.CLIENTBOUND_ChannelListResponse:
            self._channellist = []
            for cid, name in packet.channels.items():
                self._channellist.append(primitives.Channel(cid=cid, name=name))
            await self._invoke_event("on_channellist_received")
            return
        
        if packet_type is protocol.CLIENTBOUND_EventUserJoined:
            # user = primitives.User(fingerprint=packet.fingerprint)
            await self._invoke_event("on_user_joined", packet.user)
            for user in self._userlist:
                if user != packet.user:
                    continue
                return
            self._userlist.append(packet.user)
            return
        if packet_type is protocol.CLIENTBOUND_EventUserLeft:
            user = self.find_user_by_fingerprint(packet.fingerprint)
            await self._invoke_event("on_user_left", user)
            for user in self._userlist:
                if user != user:
                    continue
                self._userlist.remove(user)
                return
            return
        
        if packet_type is protocol.CLIENTBOUND_ServerMessage:
            channel = self.find_channel(packet.cid)
            message = primitives.Message(packet.mid, channel=channel, content=packet.message, author=None)
            return await self._invoke_event("on_server_message", message)
        
        if packet_type is protocol.CLIENTBOUND_UserMessage:
            channel = self.find_channel(packet.channel)
            user = self.find_user_by_fingerprint(packet.user)
            message = primitives.Message(packet.mid, channel=channel, content=packet.message, author=user)
            return await self._invoke_event("on_message", message)
        
        
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
        