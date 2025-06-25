import scalar.primitives as primitives
import scalar.protocol.packets.packet as packet

### HANDSHAKE STAGE
class SERVERBOUND_HANDSHAKE_Hello(packet.Packet):
    side = packet.SERVER
    datavalues = {"version": int}
    defaults = {}
    def _write(self, buffer: packet.buf.Buffer):
        buffer.WriteU16(self.version)
    def _read(self, buffer: packet.buf.Buffer):
        self.version = buffer.ReadU16()

class CLIENTBOUND_HANDSHAKE_Hello(packet.Packet):
    side = packet.CLIENT
    datavalues = {"version": int}
    defaults = {}
    def _write(self, buffer: packet.buf.Buffer):
        buffer.WriteU16(self.version)
    def _read(self, buffer: packet.buf.Buffer):
        self.version = buffer.ReadU16()

class SERVERBOUND_HANDSHAKE_EncryptionSupported(packet.Packet):
    side = packet.SERVER
    datavalues = {"encryptions": list[str]}
    defaults = {}
    def _write(self, buffer: packet.buf.Buffer):
        buffer.WriteU16(len(self.encryptions))
        for encrypt in self.encryptions:
            buffer.WriteStringNT(encrypt)
    def _read(self, buffer: packet.buf.Buffer):
        self.encryptions = []
        for i in range(buffer.ReadU16()):
            self.encryptions.append(buffer.ReadStringNT())
            
class CLIENTBOUND_HANDSHAKE_EncryptionSelect(packet.Packet):
    side = packet.CLIENT
    datavalues = {"select": int}
    defaults = {}
    def _write(self, buffer: packet.buf.Buffer):
        buffer.WriteU16(self.select)
    def _read(self, buffer: packet.buf.Buffer):
        self.select = buffer.ReadU16()

class SERVERBOUND_HANDSHAKE_EncryptionPubKey(packet.Packet):
    side = packet.SERVER
    datavalues = {"key": str}
    defaults = {}
    def _write(self, buffer: packet.buf.Buffer):
        buffer.WriteStringLPL(self.key)
    def _read(self, buffer: packet.buf.Buffer):
        self.key = buffer.ReadStringLPL()

class CLIENTBOUND_HANDSHAKE_EncryptionPubKey(packet.Packet):
    side = packet.CLIENT
    datavalues = {"key": str}
    defaults = {}
    def _write(self, buffer: packet.buf.Buffer):
        buffer.WriteStringLPL(self.key)
    def _read(self, buffer: packet.buf.Buffer):
        self.key = buffer.ReadStringLPL()

packet.register(SERVERBOUND_HANDSHAKE_Hello)
packet.register(CLIENTBOUND_HANDSHAKE_Hello)
packet.register(SERVERBOUND_HANDSHAKE_EncryptionSupported)
packet.register(CLIENTBOUND_HANDSHAKE_EncryptionSelect)
packet.register(SERVERBOUND_HANDSHAKE_EncryptionPubKey)
packet.register(CLIENTBOUND_HANDSHAKE_EncryptionPubKey)

### LOGIN STAGE
class SERVERBOUND_LOGIN_UserInfo(packet.Packet):
    side = packet.SERVER
    datavalues = {"username": str}
    defaults = {}
    def _write(self, buffer: packet.buf.Buffer):
        buffer.WriteStringNT(self.username)
    def _read(self, buffer: packet.buf.Buffer):
        self.username = buffer.ReadStringNT()

class CLIENTBOUND_LOGIN_UserInfo(packet.Packet):
    side = packet.CLIENT
    datavalues = {"username": str}
    defaults = {}
    def _write(self, buffer: packet.buf.Buffer):
        buffer.WriteStringNT(self.username)
    def _read(self, buffer: packet.buf.Buffer):
        self.username = buffer.ReadStringNT()
packet.register(SERVERBOUND_LOGIN_UserInfo)
packet.register(CLIENTBOUND_LOGIN_UserInfo)


### GENERAL
class CLIENTBOUND_SHeartbeat(packet.Packet):
    side = packet.CLIENT
    datavalues = {"nonce": int}
    defaults = {}
    def _write(self, buffer: packet.buf.Buffer):
        buffer.WriteU16(self.nonce)
    def _read(self, buffer: packet.buf.Buffer):
        self.nonce = buffer.ReadU16()
class SERVERBOUND_SHeartbeat(packet.Packet):
    side = packet.SERVER
    datavalues = {"nonce": int}
    defaults = {}
    def _write(self, buffer: packet.buf.Buffer):
        buffer.WriteU16(self.nonce)
    def _read(self, buffer: packet.buf.Buffer):
        self.nonce = buffer.ReadU16()
class CLIENTBOUND_CHeartbeat(packet.Packet):
    side = packet.CLIENT
    datavalues = {"nonce": int}
    defaults = {}
    def _write(self, buffer: packet.buf.Buffer):
        buffer.WriteU16(self.nonce)
    def _read(self, buffer: packet.buf.Buffer):
        self.nonce = buffer.ReadU16()
class SERVERBOUND_CHeartbeat(packet.Packet):
    side = packet.SERVER
    datavalues = {"nonce": int}
    defaults = {}
    def _write(self, buffer: packet.buf.Buffer):
        buffer.WriteU16(self.nonce)
    def _read(self, buffer: packet.buf.Buffer):
        self.nonce = buffer.ReadU16()
packet.register(SERVERBOUND_SHeartbeat)
packet.register(CLIENTBOUND_SHeartbeat)
packet.register(SERVERBOUND_CHeartbeat)
packet.register(CLIENTBOUND_CHeartbeat)

class CLIENTBOUND_ImplementationInfo(packet.Packet):
    side = packet.CLIENT
    datavalues = {"implementation": str}
    defaults = {}
    def _write(self, buffer: packet.buf.Buffer):
        buffer.WriteStringNT(self.implementation)
    def _read(self, buffer: packet.buf.Buffer):
        self.implementation = buffer.ReadStringNT()
class SERVERBOUND_ImplementationInfo(packet.Packet):
    side = packet.SERVER
    datavalues = {"implementation": str}
    defaults = {}
    def _write(self, buffer: packet.buf.Buffer):
        buffer.WriteStringNT(self.implementation)
    def _read(self, buffer: packet.buf.Buffer):
        self.implementation = buffer.ReadStringNT()
packet.register(SERVERBOUND_ImplementationInfo)
packet.register(CLIENTBOUND_ImplementationInfo)

class CLIENTBOUND_Kick(packet.Packet):
    side = packet.CLIENT
    datavalues = {"reason": str}
    defaults = {"reason": "no reason specified"}
    def _write(self, buffer: packet.buf.Buffer):
        buffer.WriteStringNT(self.reason)
    def _read(self, buffer: packet.buf.Buffer):
        self.reason = buffer.ReadStringNT()
packet.register(CLIENTBOUND_Kick)

class CLIENTBOUND_UserMessage(packet.Packet):
    side = packet.CLIENT
    datavalues = {"mid": int, "channel": int, "user": int, "message": str}
    defaults = {}
    def _write(self, buffer: packet.buf.Buffer):
        buffer.WriteU64(self.mid)
        buffer.WriteU64(self.channel)
        buffer.WriteU64(self.user)
        buffer.WriteStringNT(self.message)
    def _read(self, buffer: packet.buf.Buffer):
        self.mid = buffer.ReadU64()
        self.channel = buffer.ReadU64()
        self.user = buffer.ReadU64()
        self.message = buffer.ReadStringNT()
class SERVERBOUND_SendMessage(packet.Packet):
    side = packet.SERVER
    datavalues = {"channel": int, "message": str}
    defaults = {}
    def _write(self, buffer: packet.buf.Buffer):
        buffer.WriteU64(self.channel)
        buffer.WriteStringNT(self.message)
    def _read(self, buffer: packet.buf.Buffer):
        self.channel = buffer.ReadU64()
        self.message = buffer.ReadStringNT()
class CLIENTBOUND_ServerMessage(packet.Packet):
    side = packet.CLIENT
    datavalues = {"mid": int, "channel": int, "message": str}
    defaults = {}
    def _write(self, buffer: packet.buf.Buffer):
        buffer.WriteU64(self.mid)
        buffer.WriteU64(self.channel)
        buffer.WriteStringNT(self.message)
    def _read(self, buffer: packet.buf.Buffer):
        self.mid = buffer.ReadU64()
        self.channel = buffer.ReadU64()
        self.message = buffer.ReadStringNT()
packet.register(CLIENTBOUND_UserMessage)
packet.register(SERVERBOUND_SendMessage)
packet.register(CLIENTBOUND_ServerMessage)

class SERVERBOUND_UserListRequest(packet.Packet):
    side = packet.SERVER
    datavalues = {}
    defaults = {}
class SERVERBOUND_ChannelListRequest(packet.Packet):
    side = packet.SERVER
    datavalues = {}
    defaults = {}
class CLIENTBOUND_UserListResponse(packet.Packet):
    side = packet.CLIENT
    datavalues = {"users": dict[int,str]}
    defaults = {}
    def _write(self, buffer: packet.buf.Buffer):
        buffer.WriteU16(len(self.users))
        for fingerprint,name in self.users.items():
            buffer.WriteU64(fingerprint)
            buffer.WriteStringNT(name)
    def _read(self, buffer: packet.buf.Buffer):
        self.users = {}
        for i in range(buffer.ReadU16()):
            fingerprint = buffer.ReadU64()
            name = buffer.ReadStringNT()
            self.users[fingerprint] = name
class CLIENTBOUND_ChannelListResponse(packet.Packet):
    side = packet.CLIENT
    datavalues = {"channels": dict[int,str]}
    defaults = {}
    def _write(self, buffer: packet.buf.Buffer):
        buffer.WriteU16(len(self.channels))
        for cid,name in self.channels.items():
            buffer.WriteU64(cid)
            buffer.WriteStringNT(name)
    def _read(self, buffer: packet.buf.Buffer):
        self.channels = {}
        for i in range(buffer.ReadU16()):
            cid = buffer.ReadU64()
            name = buffer.ReadStringNT()
            self.channels[cid] = name
packet.register(SERVERBOUND_UserListRequest)
packet.register(SERVERBOUND_ChannelListRequest)
packet.register(CLIENTBOUND_UserListResponse)
packet.register(CLIENTBOUND_ChannelListResponse)

class CLIENTBOUND_EventUserJoined(packet.Packet):
    side = packet.CLIENT
    datavalues = {"user": primitives.User}
    defaults = {}
    def _write(self, buffer: packet.buf.Buffer):
        buffer.WriteStringNT(self.user.username)
        buffer.WriteU64(self.user.fingerprint)
    def _read(self, buffer: packet.buf.Buffer):
        username = buffer.ReadStringNT()
        fingerprint = buffer.ReadU64()
        self.user = primitives.User(username, fingerprint)
class CLIENTBOUND_EventUserLeft(packet.Packet):
    side = packet.CLIENT
    datavalues = {"fingerprint": int}
    defaults = {}
    def _write(self, buffer: packet.buf.Buffer):
        buffer.WriteU64(self.fingerprint)
    def _read(self, buffer: packet.buf.Buffer):
        self.fingerprint = buffer.ReadU64()
packet.register(CLIENTBOUND_EventUserJoined)
packet.register(CLIENTBOUND_EventUserLeft)
