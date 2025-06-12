import packets.readerwriter as readerwriter

registered = {}

PACKET_SIDE_SERVER = 'SERVERBOUND'
PACKET_SIDE_CLIENT = 'CLIENTBOUND'

registered[PACKET_SIDE_SERVER] = {}
registered[PACKET_SIDE_CLIENT] = {}

class Packet:
	pid = 0xffff
	side = 'UNBOUND'
	datavalues = {}
	defaults = {}

	def __init__(self, **kwargs):
		if kwargs.get("__SKIPDATAVALUES", False): 
			return
		for datavalue, type_ in self.datavalues.items():
			value = kwargs.get(datavalue, self.defaults.get(datavalue))
			if type(type_) is list:
				if type(value) not in type_:
					raise ValueError(f"datavalue '{datavalue}' invalid: expected one of [{', '.join([typ.__name__ for typ in type_])}], got {type(value).__name__}")
			if type(type_) is type:
				if type(value) is not type_:
					raise ValueError(f"datavalue '{datavalue}' invalid: expected {type_.__name__}, got {type(value).__name__}")
			setattr(self, datavalue, value)
	
	def pack(self):
		buffer = readerwriter.ReaderWriter.fromNoFile(b'', 'w')
		buffer.WriteU16(self.pid)
		self._write(buffer)
		buffer.seek(0)
		data = buffer.handle.read(buffer.size())
		return data
	@staticmethod
	def unpack(side, data):
		if side not in [PACKET_SIDE_SERVER, PACKET_SIDE_CLIENT]:
			raise ValueError(f'unknown side \"{side}\": should be server- or clientbound')
		buffer = readerwriter.ReaderWriter.fromNoFile(data, 'r')
		pid = buffer.ReadU16()
		if registered[side].get(pid) is None:
			raise ValueError(f"unknown packet id {pid}")
		packet = registered[side][pid](__SKIPDATAVALUES=True)
		packet._read(buffer)
		return packet
	def _write(self, buffer):
		pass
	def _read(self, buffer):
		pass
	@staticmethod
	def register(klass):
		global registered
		if klass.side not in [PACKET_SIDE_SERVER, PACKET_SIDE_CLIENT]:
			raise ValueError(f'packet {klass} is not server- or clientbound')
		if klass.pid and registered[klass.side].get(klass.pid) is not None:
			raise ValueError(f'packet id {klass.pid} is registered for side {klass.side}')
		if not klass.pid:
			klass.pid = max(list(registered[klass.side].keys()) + [-1])+1
		registered[klass.side][klass.pid] = klass

	def __repr__(self):
		additional = ''
		for datavalue in self.datavalues:
			additional += f", {datavalue}={repr(getattr(self, datavalue))}"
		return f"{type(self).__name__}(pid={self.pid}, side={self.side}{additional})"

class CLIENTBOUND_Kick(Packet):
	pid = None
	side = PACKET_SIDE_CLIENT
	datavalues = {'reason': str}
	defaults = {'reason': 'no reason specified'}

	def _write(self, buffer):
		buffer.WriteStringNT(self.reason)
	def _read(self, buffer):
		self.reason = buffer.ReadStringNT()
class SERVERBOUND_Disconnect(Packet):
	pid = None
	side = PACKET_SIDE_SERVER
	datavalues = {}
	defaults = {}
class CLIENTBOUND_KeepAlive(Packet):
	pid = None
	side = PACKET_SIDE_CLIENT
	datavalues = {'nonce': int}
	defaults = {}

	def _write(self, buffer):
		buffer.WriteU8(self.nonce)
	def _read(self, buffer):
		self.nonce = buffer.ReadU8()
class SERVERBOUND_KeepAlive(Packet):
	pid = None
	side = PACKET_SIDE_SERVER
	datavalues = {'nonce': int}
	defaults = {}
	
	def _write(self, buffer):
		buffer.WriteU8(self.nonce)
	def _read(self, buffer):
		self.nonce = buffer.ReadU8()

class SERVERBOUND_UserInfo(Packet):
	pid = None
	side = PACKET_SIDE_SERVER
	datavalues = {'name': str}
	defaults = {}

	def _write(self, buffer):
		buffer.WriteStringNT(self.name)
	def _read(self, buffer):
		self.name = buffer.ReadStringNT()
class CLIENTBOUND_UserInfo(Packet):
	pid = None
	side = PACKET_SIDE_CLIENT
	datavalues = {'name': str, 'fingerprint': str}
	defaults = {}

	def _write(self, buffer):
		buffer.WriteStringNT(self.name)
		buffer.WriteStringNT(self.fingerprint)
	def _read(self, buffer):
		self.name = buffer.ReadStringNT()
		self.fingerprint = buffer.ReadStringNT()

class CLIENTBOUND_ServerMessage(Packet):
	pid = None
	side = PACKET_SIDE_CLIENT
	datavalues = {'message': str}
	defaults = {}

	def _write(self, buffer):
		buffer.WriteStringNT(self.message)
	def _read(self, buffer):
		self.message = buffer.ReadStringNT()
class CLIENTBOUND_UserMessage(Packet):
	pid = None
	side = PACKET_SIDE_CLIENT
	datavalues = {'uname': str, 'message': str}
	defaults = {}

	def _write(self, buffer):
		buffer.WriteStringNT(self.uname)
		buffer.WriteStringNT(self.message)
	def _read(self, buffer):
		self.uname = buffer.ReadStringNT()
		self.message = buffer.ReadStringNT()
class SERVERBOUND_SendMessage(Packet):
	pid = None
	side = PACKET_SIDE_SERVER
	datavalues = {'message': str}
	defaults = {}

	def _write(self, buffer):
		buffer.WriteStringNT(self.message)
	def _read(self, buffer):
		self.message = buffer.ReadStringNT()

class CLIENTBOUND_ConnectedUsersList(Packet):
	pid = None
	side = PACKET_SIDE_CLIENT
	datavalues = {'list': list[str]}
	defaults = {'list': []}

	def _write(self, buffer):
		buffer.WriteU16(len(self.list))
		for uname in self.list:
			buffer.WriteStringNT(uname)
	def _read(self, buffer):
		self.list = []
		for i in range(buffer.ReadU16()):
			self.list.append(buffer.ReadStringNT())

class SERVERBOUND_CommandRequest(Packet):
	pid = None
	side = PACKET_SIDE_SERVER
	datavalues = {'cid': int, 'command': str, 'data': list[str]}
	defaults = {}

	def _write(self, buffer):
		buffer.WriteU16(self.cid)
		buffer.WriteStringNT(self.command)
		buffer.WriteU16(len(self.data))
		for val in self.data:
			buffer.WriteStringNT(val)
	def _read(self, buffer):
		self.cid = buffer.ReadU16()
		self.command = buffer.ReadStringNT()
		self.data = []
		for i in range(buffer.ReadU16()):
			self.data.append(buffer.ReadStringNT())
class CLIENTBOUND_CommandResponse(Packet):
	pid = None
	side = PACKET_SIDE_CLIENT
	datavalues = {'cid': int, 'data': list[str]}
	defaults = {}

	def _write(self, buffer):
		buffer.WriteU16(self.cid)
		buffer.WriteU16(len(self.data))
		for val in self.data:
			buffer.WriteStringNT(val)
	def _read(self, buffer):
		self.cid = buffer.ReadU16()
		self.data = []
		for i in range(buffer.ReadU16()):
			self.data.append(buffer.ReadStringNT())

Packet.register(CLIENTBOUND_Kick)
Packet.register(SERVERBOUND_Disconnect)
Packet.register(CLIENTBOUND_KeepAlive)
Packet.register(SERVERBOUND_KeepAlive)

Packet.register(SERVERBOUND_UserInfo)
Packet.register(CLIENTBOUND_UserInfo)

Packet.register(CLIENTBOUND_ServerMessage)
Packet.register(CLIENTBOUND_UserMessage)
Packet.register(SERVERBOUND_SendMessage)

Packet.register(CLIENTBOUND_ConnectedUsersList)

Packet.register(SERVERBOUND_CommandRequest)
Packet.register(CLIENTBOUND_CommandResponse)
