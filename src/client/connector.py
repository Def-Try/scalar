
from client.command_handler import CommandHandler
import packets
import constants

import socket
import threading
import random
import json
import os

CLIENT_STATUS_NONE = 'idling'
CLIENT_STATUS_CONNECTING = 'connecting'
CLIENT_STATUS_CONNECT_FAIL = 'connection failed'
CLIENT_STATUS_HANDSHAKING = 'handshaking'
CLIENT_STATUS_HANDSHAKE_FAIL = 'handshake failed'
CLIENT_STATUS_ENCRYPTING = 'encrypting'
CLIENT_STATUS_ENCRYPTION_FAIL = 'encryption failed'
CLIENT_STATUS_GETSVDATA = 'getting server data'
CLIENT_STATUS_CONNECTED = 'connected to {address} as {uname}'

CLIENT_ERROR_OSERROR = "os error: {strerror}"
CLIENT_ERROR_TIMEOUT = "read timed out"
CLIENT_ERROR_SERVERDIED = "server shut down"

CLIENT_STAT_KICKED = "kicked: {reason}"

class Connector:
	status = CLIENT_STATUS_NONE
	laststatus = None
	authenticated = False
	socket = None
	closed = False

	uname = None
	oname = None
	host, port = None, None

	screen = None

	command_handler = CommandHandler()
	command_queue_ = {}
	def __init__(self, codespeak):
		self.codespeak = codespeak
		self.commands_init()

	def start(self):
		self.thread = threading.Thread(target=self.serve, daemon=True)
		self.thread.start()

	def _low_send(self, data: bytes) -> bool:
		"""
		low level send call
		:param bytes data: data to send
		:return: whether the sending was successful
		:rtype: bool
		"""
		try:
			self.socket.sendall(data)
		except OSError:
			self._low_close(error=CLIENT_ERROR_OSERROR)
			return False
		return True
	def _low_recv(self, amount: int) -> bytes|None:
		"""
		low level recv call
		:param int amount: data to send
		:return: received bytes or None if unsuccessful
		:rtype: bytes or None
		"""
		recvd = b''
		while len(recvd) < amount:
			try:
				d = self.socket.recv(amount - len(recvd))
				if d == b'':
					self._low_close(error=CLIENT_ERROR_SERVERDIED)
					return None
				recvd += d
			except socket.timeout:
				self._low_close(error=CLIENT_ERROR_TIMEOUT)
				return None
			except OSError as e:
				self._low_close(error=CLIENT_ERROR_OSERROR.format(strerror=e.strerror))
				return None
		return recvd
	def _low_close(self, error=None):
		if self.closed: return
		if error is not None:
			self.status = str(error)
			self.screen.push_to_log("LOG", str(error))
		self.closed = True
		if self.socket is None: return
		try:
			self.socket.shutdown(socket.SHUT_RDWR)
			self.socket.close()
		except Exception:
			pass
		del self.socket
		self.socket = None

	def _send(self, data: bytes):
		if not self._low_send(data):
			exit()
	def _recv(self, amount: int) -> bytes:
		data = self._low_recv(amount)
		if data is None:
			exit()
		return data
	def _close(self, error=None):
		self._low_close(error=error)
		self.status = CLIENT_STATUS_NONE

	def send(self, packet):
		iv, tag, encrypted = self.codespeak.encrypt(packet.pack())
		# header (30 bytes)
		self._send(len(encrypted).to_bytes(2, 'little')) # 4 bytes
		self._send(iv) # 12 bytes
		self._send(tag) # 16 bytes
		# data (n bytes)
		self._send(encrypted) # n bytes
	def recv(self):
		# header (30 bytes)
		encrypted_len = int.from_bytes(self._recv(2), 'little')
		iv, tag = self._recv(12), self._recv(16)
		# data (n bytes)
		encrypted = self._recv(encrypted_len)
		packet = self.codespeak.decrypt(iv, tag, encrypted)
		return packets.Packet.unpack(packets.PACKET_SIDE_CLIENT, packet)
	def close(self, error=None):
		os.makedirs('data/client', exist_ok=True)
		with open('data/client/config.json', 'w') as f:
			json.dump({
				'host': self.host,
				'port': self.port,
				'name': self.oname
			}, f)
		with open('data/client/private.key', 'wb') as f:
			f.write(self.codespeak.save_key())
		if self.socket is None: return
		if self.authenticated:
			self.send(packets.SERVERBOUND_Disconnect())
		self._close(error=error)
	def connected(self):
		if self.socket is None: return False
		if not self.authenticated: return False
		return True

	def commands_init(self):
		self.command_handler.register('exit', 'Exit Scalar', '', exit)
		self.command_handler.register('name', 'Change or display current name', '[name]', self.command_name)
		self.command_handler.register('connect', 'Connect to Scalar server', '<host> <port:int>', self.command_connect)
		self.command_handler.register('reconnect', 'Reconnect to last server', '', self.command_reconnect)
		self.command_handler.register('disconnect', 'Disconnect from server', '', self.command_disconnect)

		self.command_handler.register('list', 'Query list of users connected to server', '', self.command_list)
		self.command_handler.register('uinfo', 'Query info about a specific user on server', '<name>', self.command_uinfo)
	def commands_queue(self, callback):
		while True:
			cid = random.randint(0, 65535)
			if self.command_queue_.get(cid): continue
			break
		self.command_queue_[cid] = callback
		return cid
	def commands_continue(self, cid, data):
		if not self.command_queue_.get(cid): return
		callback = self.command_queue_[cid]
		del self.command_queue_[cid]
		return callback(data)
	def command_name(self, name):
		self.oname = None
		if not all(ch in constants.ALLOWED_USERNAME_CHARACTERS for ch in name):
			return "name should only contain printable ASCII characters"
		self.oname = name
		self.uname = name
		return f"name set to \"{name}\""
	def command_connect(self, host, port):
		self.host = host
		self.port = port
		if not self.oname:
			return "no name set"
		self.start()
		return f"connecting to {host}:{port}"
	def command_reconnect(self):
		if not self.host or not self.port:
			return "wasn't connected yet"
		self.close()
		self.start()
		return None
	def command_disconnect(self):
		self.close()
		return "disconnected"
	def command_list(self):
		if not self.connected():
			return "not connected"
		cid = self.commands_queue(self.command_list_cont)
		self.send(packets.SERVERBOUND_CommandRequest(cid=cid, command='list', data=[]))
		return None
	def command_list_cont(self, data):
		self.screen.push_to_log("SERVER", f"Connected users ({len(data)}):")
		if len(data) == 0:
			self.screen.push_to_log("SERVER", f"  <empty>")
		for usr in data:
			self.screen.push_to_log("SERVER", f"  {usr}")
	def command_uinfo(self, name):
		if not self.connected():
			return "not connected"
		cid = self.commands_queue(self.command_uinfo_cont)
		self.send(packets.SERVERBOUND_CommandRequest(cid=cid, command='uinfo', data=[name]))
		return None
	def command_uinfo_cont(self, data):
		if data[1] == '':
			self.screen.push_to_log("SERVER", f"No such user: {data[0]}")
			return
		self.screen.push_to_log("SERVER", f"User {data[0]}")
		self.screen.push_to_log("SERVER", f"  OName	   {data[1]}")
		self.screen.push_to_log("SERVER", f"  Fingerprint {data[2]}")

	def input(self, inp):
		if inp.startswith('/'):
			self.screen.push_to_log("COMMAND", inp)
			ret = self.command_handler.exec(inp[1:])
			if ret:
				self.screen.push_to_log("LOG", ret)
			return
		if not self.connected():
			self.screen.push_to_log("LOG", "not connected")
			return
		self.send(packets.SERVERBOUND_SendMessage(message=inp))
		self.screen.push_message(self.uname, inp)

	def serve(self):
		self.connect()
		if self.socket is None: return
		while True:
			recvd = self.recv()
			if type(recvd) == packets.CLIENTBOUND_Kick:
				self._close()
				self.status = CLIENT_STAT_KICKED.format(reason=recvd.reason)
				self.screen.push_to_log("LOG", self.status)
				break
			if type(recvd) == packets.CLIENTBOUND_ServerMessage:
				self.screen.push_to_log("SERVER", recvd.message)
			if type(recvd) == packets.CLIENTBOUND_UserMessage:
				if recvd.uname == self.uname: continue
				self.screen.push_message(recvd.uname, recvd.message)
			if type(recvd) == packets.CLIENTBOUND_KeepAlive:
				self.send(packets.SERVERBOUND_KeepAlive(nonce=recvd.nonce))
			if type(recvd) == packets.CLIENTBOUND_CommandResponse:
				self.commands_continue(recvd.cid, recvd.data)

	def connect(self):
		if not self.oname:
			self.screen.push_to_log("LOG", "name not set")
			return
		self.uname = self.oname

		self.status = CLIENT_STATUS_CONNECTING
		self.screen.push_to_log("LOG", CLIENT_STATUS_CONNECTING)
		self.closed = False
		self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.socket.settimeout(60)
		try:
			self.socket.connect((self.host, self.port))
			self.socket.settimeout(120)
		except ConnectionRefusedError:
			self.status = CLIENT_STATUS_CONNECT_FAIL
			self.screen.push_to_log("LOG", CLIENT_STATUS_CONNECT_FAIL)
			del self.socket
			self.socket = None
			return
		self.status = CLIENT_STATUS_HANDSHAKING
		self.screen.push_to_log(f"LOG", CLIENT_STATUS_HANDSHAKING)

		self._send(b'CDSP')
		if self._recv(4) != b'CDSP':
			self.status = CLIENT_STATUS_HANDSHAKE_FAIL
			self.screen.push_to_log("LOG", CLIENT_STATUS_HANDSHAKE_FAIL)
			self._close()
			return
		self.status = CLIENT_STATUS_ENCRYPTING
		self.screen.push_to_log("LOG", CLIENT_STATUS_ENCRYPTING)
		pub = self.codespeak.public_key()
		self._send(len(pub).to_bytes(2, 'little'))
		self._send(pub)
		server_pub = self._recv(int.from_bytes(self._recv(2), 'little'))
		try:
			self.codespeak.exchange(server_pub)
		except ValueError:
			self.status = CLIENT_STATUS_ENCRYPTION_FAIL
			self.screen.push_to_log("LOG", CLIENT_STATUS_ENCRYPTION_FAIL)
			self._close()
			return
		self.status = CLIENT_STATUS_GETSVDATA
		self.screen.push_to_log("LOG", CLIENT_STATUS_GETSVDATA)
		self.authenticated = True
		ulist = self.recv()
		self.send(packets.SERVERBOUND_UserInfo(name=self.uname))
		uinfo = self.recv()
		self.uname = uinfo.name
		self.status = CLIENT_STATUS_CONNECTED.format(address=f"{self.host}:{self.port}", uname=self.uname)
		self.screen.push_to_log("LOG", self.status)
		self.screen.push_to_log("SERVER", f"Connected users ({len(ulist.list)}):")
		if len(ulist.list) == 0:
			self.screen.push_to_log("SERVER", f"  <empty>")
		for usr in ulist.list:
			self.screen.push_to_log("SERVER", f"  {usr}")