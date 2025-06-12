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
class CLIENTBOUND_Kick(packet.Packet):
    side = packet.CLIENT
    datavalues = {"reason": str}
    defaults = {"reason": "no reason specified"}
    def _write(self, buffer: packet.buf.Buffer):
        buffer.WriteStringNT(self.reason)
    def _read(self, buffer: packet.buf.Buffer):
        self.reason = buffer.ReadStringNT()

class CLIENTBOUND_UserMessage(packet.Packet):
    side = packet.CLIENT
    datavalues = {"username": str, "message": str}
    defaults = {}
    def _write(self, buffer: packet.buf.Buffer):
        buffer.WriteStringNT(self.username)
        buffer.WriteStringNT(self.message)
    def _read(self, buffer: packet.buf.Buffer):
        self.username = buffer.ReadStringNT()
        self.message = buffer.ReadStringNT()
class SERVERBOUND_SendMessage(packet.Packet):
    side = packet.SERVER
    datavalues = {"message": str}
    defaults = {}
    def _write(self, buffer: packet.buf.Buffer):
        buffer.WriteStringNT(self.message)
    def _read(self, buffer: packet.buf.Buffer):
        self.message = buffer.ReadStringNT()

class CLIENTBOUND_ServerMessage(packet.Packet):
    side = packet.CLIENT
    datavalues = {"message": str}
    defaults = {}
    def _write(self, buffer: packet.buf.Buffer):
        buffer.WriteStringNT(self.message)
    def _read(self, buffer: packet.buf.Buffer):
        self.message = buffer.ReadStringNT()

packet.register(CLIENTBOUND_Kick)