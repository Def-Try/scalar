import gzip

from scalar.protocol.socket.constants import *
import scalar.protocol.socket.basesocket
import scalar.protocol.encryption
import scalar.protocol.packets

class ProtoSocket(scalar.protocol.socket.basesocket.BaseSocket):
    def __init__(self, *,
                 host: str,
                 port: int,
                 encryption: scalar.protocol.encryption.BaseEncryption = scalar.protocol.encryption.BaseEncryption()):
        super().__init__(host=host, port=port)
        self.encryption = encryption

    def set_encryption(self, encryption: scalar.protocol.encryption.BaseEncryption):
        self.encryption = encryption

    async def recv_packet(self) -> tuple[int, scalar.protocol.packets.Packet]:
        stat, length_bytes = await self.recv(2)
        if stat != SOCKET_SUCCESS:
            return stat, None
        length = int.from_bytes(length_bytes, 'little')
        stat, packet_raw_compressed_encrypted = await self.recv(length)
        if stat != SOCKET_SUCCESS:
            return stat, None
        packet_raw_compressed = self.encryption.decrypt(packet_raw_compressed_encrypted)
        packet_raw = gzip.decompress(packet_raw_compressed)
        packet = scalar.protocol.packets.Packet.unpack(
            scalar.protocol.packets.SERVER if self._bound else scalar.protocol.packets.CLIENT,
            packet_raw
        )
        return SOCKET_SUCCESS, packet
    
    async def send_packet(self, packet: scalar.protocol.packets.Packet) -> int:
        packet_raw = packet.pack()
        packet_raw_compressed = gzip.compress(packet_raw)
        packet_raw_compressed_encrypted = self.encryption.encrypt(packet_raw_compressed)
        length = len(packet_raw_compressed_encrypted)
        length_bytes = int.to_bytes(length, 2, 'little')
        await self.send(length_bytes)
        return await self.send(packet_raw_compressed_encrypted)