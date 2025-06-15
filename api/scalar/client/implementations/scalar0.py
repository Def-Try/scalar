from scalar.client.baseclient import BaseClient
import scalar.primitives as primitives
import scalar.protocol.packets.protocol as protocol

class Scalar0Client(BaseClient):
    _userlist: list[primitives.User] = []
    _implementation: str = 'scalar0'

    async def event_on_login_completed(self):
        if self._server_implementation not in ('scalar0',):
            return
        await self._send_packet(protocol.SERVERBOUND_UserListRequest)
        for packet in await self.recv_packets():
            if type(packet) is not protocol.CLIENTBOUND_UserListResponse:
                await self._process_packet(type(packet), packet)
                continue
            self._userlist = packet.users

    async def _process_packet(self, packet_type: type, packet: protocol.packet.Packet):
        if packet_type is protocol.CLIENTBOUND_EventUserJoined:
            await self._invoke_event("on_user_joined", packet.user)
            for user in self._userlist:
                if user != packet.user:
                    continue
                return
            self._userlist.append(packet.user)
            return
        if packet_type is protocol.CLIENTBOUND_EventUserLeft:
            await self._invoke_event("on_user_left", packet.user)
            for user in self._userlist:
                if user != packet.user:
                    continue
                self._userlist.remove(packet.user)
                return
            return
        if packet_type is protocol.CLIENTBOUND_ServerMessage:
            return await self._invoke_event("on_server_message", packet.message)
        if packet_type is protocol.CLIENTBOUND_UserMessage:
            return await self._invoke_event("on_message", self.find_user_by_fingerprint(packet.fingerprint), packet.message)
        
        
    def find_user_by_fingerprint(self, fingerprint: str) -> primitives.User|None:
        for user in self._userlist:
            if user.fingerprint != fingerprint:
                continue
            return user
        return None
        