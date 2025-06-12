import os
import sys
import inspect

# import from parent folder
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir) 

from scalar.protocol.packets import packet

class BasicPacket(packet.Packet):
    side = packet.SERVER
    datavalues = {}
packet.register(BasicPacket)
basic = BasicPacket()
basic_pack = basic.pack()
assert (basic_pack == b'\x00\x00')

class DatavaluedPacket(packet.Packet):
    side = packet.SERVER
    datavalues = {
        "test1": int,
        "test2": str,
        "test3": bytes,
        "test4": float,
        "test5": list[str]
    }
packet.register(DatavaluedPacket)
datavalued = DatavaluedPacket(
    test1=1,
    test2="hi",
    test3=b'hello',
    test4=0.5,
    test5=["hi", "again"]
)
datavalued_pack = datavalued.pack()
assert(datavalued_pack == b'\x01\x00\x01\x00\x00\x00\x00\x00\x00\x00hi\x00\x05\x00\x00\x00\x00\x00\x00\x00hello\x00\x00\x00\x00\x00\x00\xe0?\x02\x00\x00\x00\x00\x00\x00\x00hi\x00again\x00')
datavalued_pack_unpack = packet.Packet.unpack(packet.SERVER, datavalued_pack)
assert(datavalued.test1 == datavalued_pack_unpack.test1 and
       datavalued.test2 == datavalued_pack_unpack.test2 and
       datavalued.test3 == datavalued_pack_unpack.test3 and
       datavalued.test4 == datavalued_pack_unpack.test4 and
       datavalued.test5 == datavalued_pack_unpack.test5)