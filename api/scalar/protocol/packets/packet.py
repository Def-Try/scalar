import scalar.protocol.packets.buffer as buf
import scalar.exceptions as exceptions
import types

SERVER = 'SERVERBOUND'
CLIENT = 'CLIENTBOUND'
registered = {}
registered[SERVER] = {}
registered[CLIENT] = {}

class Packet:
	pid = None
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
		if self.pid is None:
			raise exceptions.PacketUnregistered()
		buffer = buf.Buffer.fromNoFile(b'', 'w')
		buffer.WriteU16(self.pid)
		self._write(buffer)
		buffer.seek(0)
		data = buffer.handle.read(buffer.size())
		return data
	@staticmethod
	def unpack(side, data):
		if side not in [SERVER, CLIENT]:
			raise exceptions.PacketUnknownSide()
		buffer = buf.Buffer.fromNoFile(data, 'r')
		pid = buffer.ReadU16()
		if registered[side].get(pid) is None:
			raise exceptions.PacketUnknown()
		packet = registered[side][pid](__SKIPDATAVALUES=True)
		packet._read(buffer)
		return packet
	def _write(self, buffer: buf.Buffer):
		writers = {
			str: buffer.WriteStringNT,
			bytes: lambda data: buffer.WriteU64(len(data)) or buffer.WriteData(data),
			int: buffer.WriteI64,
			float: buffer.WriteDouble
		}
		for name, type_ in self.datavalues.items():
			if type(type_) is types.GenericAlias:
				if type_.__origin__ == list:
					buffer.WriteU64(len(getattr(self, name)))
					for i in getattr(self, name):
						writers[type_.__args__[0]](i)
					continue
				elif type_.__origin__ == dict:
					buffer.WriteU64(len(getattr(self, name)))
					for i in getattr(self, name):
						writers[type_.__args__[0]](i)
						writers[type_.__args__[1]](i)
					continue
			if not writers.get(type_):
				raise exceptions.ScalarException("Unknown type for writing, define a custom _write and _read or use other types")
			writers[type_](getattr(self, name))
	def _read(self, buffer: buf.Buffer):
		readers = {
			str: buffer.ReadStringNT,
			bytes: lambda: buffer.ReadData(buffer.ReadU64()),
			int: buffer.ReadI64,
			float: buffer.ReadDouble
		}
		for name, type_ in self.datavalues.items():
			if type(type_) is types.GenericAlias:
				if type_.__origin__ == list:
					setattr(self, name, [])
					for n in range(buffer.ReadU64()):
						getattr(self, name).append(readers[type_.__args__[0]]())
					continue
				elif type_.__origin__ == dict:
					setattr(self, name, {})
					for n in range(buffer.ReadU64()):
						getattr(self, name)[readers[type_.__args__[0]]()] = readers[type_.__args__[1]]()
					continue
			if not readers.get(type_):
				raise exceptions.ScalarException("Unknown type for writing, define a custom _write and _read or use other types")
			setattr(self, name, readers[type_]())

	def __repr__(self):
		additional = ''
		for datavalue in self.datavalues:
			additional += f", {datavalue}={repr(getattr(self, datavalue))}"
		return f"{type(self).__name__}(pid={self.pid}, side={self.side}{additional})"
	
def register(klass):
	global registered
	if klass.side not in [SERVER, CLIENT]:
		raise exceptions.PacketUnknownSide()
	if klass.pid and registered[klass.side].get(klass.pid) is not None:
		raise exceptions.PacketRegistered()
	if not klass.pid:
		klass.pid = max(list(registered[klass.side].keys()) + [-1])+1
	registered[klass.side][klass.pid] = klass