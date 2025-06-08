from codespeak import Codespeak
import packets
import constants

import socket
import select
import threading
import random
import os
import json

HOST, PORT = '', 1440
MOTD = ("""
Welcome to server!

This is an example MOTD.
Server owner can change it by altering contents in "data/server/motd.txt" file.
""").strip()

CLIENT_ERROR_OSERROR = "os error: {strerror}"
CLIENT_ERROR_TIMEOUT = "read timed out"
CLIENT_ERROR_CLIENTDIED = "client disconnected unexpectedly"

os.makedirs('data/server', exist_ok=True)
try:
	with open('data/server/private.key', 'rb') as f:
		PRIVATE_KEY = f.read()
except FileNotFoundError:
	csp = Codespeak()
	csp.generate_key()
	PRIVATE_KEY = csp.save_key()
	with open('data/server/private.key', 'wb') as f:
		f.write(PRIVATE_KEY)
try:
	with open('data/server/config.json', 'r') as f:
		config = json.load(f)
		HOST = config['host']
		PORT = config['port']
except FileNotFoundError:
	with open('data/server/config.json', 'w') as f:
		json.dump({
			'host': HOST,
			'port': PORT
		}, f)
except json.JSONDecodeError as e:
	print('Unable to read config:')
	print(f"{e.msg} at L{e.lineno} col{e.colno}")
	exit()

try:
	with open('data/server/motd.txt', 'r') as f:
		MOTD = f.read()
except FileNotFoundError:
	with open('data/server/motd.txt', 'w') as f:
		f.write(MOTD)

class Client:
	valid = True
	closed = False
	authenticated = False

	uname = None
	oname = None
	cname = None
	fingerprint = None
	skipped_keepalives = 0

	def __init__(self, address, connection, server):
		self.address = address
		self.socket = connection
		self.server = server
		self.codespeak = Codespeak()
		self.codespeak.load_key(PRIVATE_KEY)
		self.socket.settimeout(10)
		threading.Thread(target=self.serve, daemon=True).start()

	def _low_send(self, data: bytes) -> bool:
		"""
		low level send call
		:param bytes data: data to send
		:return: whether the sending was successful
		:rtype: bool
		"""
		try:
			self.socket.sendall(data)
		except OSError as e:
			self._low_close(error=CLIENT_ERROR_OSERROR.format(strerror=e.strerror))
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
					self._low_close(error=CLIENT_ERROR_CLIENTDIED)
					return None
				recvd += d
			except socket.timeout:
				return None
			except OSError as e:
				self._low_close(error=CLIENT_ERROR_OSERROR.format(strerror=e.strerror))
				return None
		return recvd
	def _low_close(self, delete=True, error=None):
		if self.closed: return
		print(f"{self.address} disconnected")
		if error is not None:
			print(f"[{self.address}] {error}")
		self.closed = True
		if delete:
			del self.server.clients[self.address]
		self.server.broadcast(packets.CLIENTBOUND_ServerMessage(message=f"{self.uname} disconnected"))
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
			if not self.closed:
				return b''
			exit()
		return data
	def _close(self, delete=True, error=None):
		self._low_close(delete=delete, error=error)
		

	def send(self, packet):
		iv, tag, encrypted = self.codespeak.encrypt(packet.pack())
		# header (30 bytes)
		self._send(len(encrypted).to_bytes(2, 'little')) # 4 bytes
		self._send(iv) # 12 bytes
		self._send(tag) # 16 bytes
		# data (n bytes)
		self._send(encrypted) # n bytes
	def recv(self, enforce=False, expect=None):
		# header (30 bytes)
		while True:
			encrypted_len = int.from_bytes(self._recv(2), 'little')
			if encrypted_len == 0:
				if self.skipped_keepalives > 5:
					self._close(delete=True, error=CLIENT_ERROR_TIMEOUT)
					exit()
				self.skipped_keepalives += 1
				# print(f"[{self.address}] [WARN] client timing out! current skipped keepalives: {self.skipped_keepalives}")
				# try keepalive
				nonce = random.randint(0, 255)
				self.send(packets.CLIENTBOUND_KeepAlive(nonce=nonce))
				pack = self.recv(enforce=False, expect=packets.SERVERBOUND_KeepAlive)
				if type(pack) == packets.SERVERBOUND_KeepAlive:
					if pack.nonce != nonce:
						print(f"[{self.address}] [WARN] KeepAlive message returned with wrong nonce. ignoring")
					self.skipped_keepalives = 0
					continue
				self.skipped_keepalives = 0
				print(f"[{self.address}] [WARN] KeepAlive message not returned. ignoring")
				return pack
			else:
				self.skipped_keepalives = 0
				break
		iv, tag = self._recv(12), self._recv(16)
		# data (n bytes)
		encrypted = self._recv(encrypted_len)
		packet = self.codespeak.decrypt(iv, tag, encrypted)
		unpacked = packets.Packet.unpack(packets.PACKET_SIDE_SERVER, packet)

		if expect is not None and ((type(expect) is list and type(unpacked) not in expect) or type(unpacked) is not expect):
			msg = f"sent unexpected packet {type(unpacked).__name__}"
			if not enforce:
				print(f"[{self.address}] [WARN] {msg}")
			else:
				self.close(msg)
				raise ValueError(msg)
		return unpacked
	def close(self, reason='Kicked', delete=True):
		print(f"[{self.address}] Kicking because {reason}")
		if self.authenticated:
			self.send(packets.CLIENTBOUND_Kick(reason=reason))
		self._close(delete=delete)

	def serve(self):
		self.handshake()
		if self.closed: return
		while True:
			packet = self.recv()
			if type(packet) is packets.SERVERBOUND_Disconnect:
				self._close(delete=True)
				self.server.broadcast(packets.CLIENTBOUND_ServerMessage(message=f"{self.uname} left"))
				return exit()
			if type(packet) is packets.SERVERBOUND_SendMessage:
				self.server.broadcast(packets.CLIENTBOUND_UserMessage(uname=self.uname, message=packet.message))
				print(f"[{self.address}] <{self.uname}> {packet.message}")
				continue
			if type(packet) is packets.SERVERBOUND_CommandRequest:
				self.handle_command(packet.cid, packet.command, packet.data)
				print(f"[{self.address}] <{self.uname}> /{packet.command} {packet.data}")
				continue
			print(packet)

	def handshake(self):
		if self._recv(4) != b'CDSP':
			self._close()
			return
		self._send(b'CDSP')
		client_pub = self._recv(int.from_bytes(self._recv(2), 'little'))
		pub = self.codespeak.public_key()
		self._send(len(pub).to_bytes(2, 'little'))
		self._send(pub)
		try:
			self.codespeak.exchange(client_pub)
		except ValueError:
			self._close()
			return
		# using Protocol from now on (using .send and .recv instead of ._send and ._recv)
		self.authenticated = True
		self.fingerprint = self.codespeak.fingerprint(client_pub)
		print(f"{self.address} passed key exchange (fingerprint={self.fingerprint})")
		userslist = []
		clients = self.server.clients.copy()
		for client in clients.values():
			if client.uname is None: continue
			userslist.append(str(client.uname))
		self.send(packets.CLIENTBOUND_ConnectedUsersList(list=userslist))
		uinfo = self.recv(enforce=True, expect=packets.SERVERBOUND_UserInfo)
		if not all(ch in constants.ALLOWED_USERNAME_CHARACTERS for ch in uinfo.name):
			self.close("Non-ASCII characters in name")
			return
		self.oname = uinfo.name
		self.cname = 0
		for client in clients.values():
			if client == self: continue
			if client.oname == uinfo.name:
				self.cname = max(self.cname, client.cname + 1)
		if self.cname != 0:
			self.uname = f"{self.oname}_{self.cname}"
		else:
			self.uname = self.oname
		self.send(packets.CLIENTBOUND_UserInfo(name=self.uname,fingerprint=self.fingerprint))
		self.send(packets.CLIENTBOUND_ServerMessage(message=MOTD))
		self.server.broadcast(packets.CLIENTBOUND_ServerMessage(message=f"{self.uname} joined"))
		print(f"{self.address} joined as {self.uname}")


	def handle_command(self, cid, command, data):
		if command == 'list':
			userslist = []
			clients = self.server.clients.copy()
			for client in clients.values():
				if client.uname is None: continue
				userslist.append(str(client.uname))
			self.send(packets.CLIENTBOUND_CommandResponse(cid=cid, data=userslist))
			return
		if command == 'uinfo':
			clients = self.server.clients.copy()
			for client in clients.values():
				if client.uname != data[0]: continue
				self.send(packets.CLIENTBOUND_CommandResponse(cid=cid, data=[data[0], client.oname, client.fingerprint]))
				return
			self.send(packets.CLIENTBOUND_CommandResponse(cid=cid, data=[data[0], '', '']))
			return

class Server:
	def __init__(self):
		self.clients = {}
		self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

	def bind(self):
		self.socket.bind((HOST, PORT))
		self.socket.listen(128)

	def serve(self):
		while True:
			ready, _, _ = select.select([self.socket], [], [], 0)
			if not ready:
				continue
			conn, addr = self.socket.accept()
			address = addr[0]+":"+str(addr[1])
			client = Client(address, conn, self)
			self.clients[address] = client
			print(f"{address} connected")

	def broadcast(self, packet):
		clients = self.clients.copy()
		for client in clients.values():
			try: client.send(packet)
			except: pass

	def close(self):
		for addr, client in self.clients.items():
			print(f"Kicking {addr}")
			client.close(reason="Server shutting down", delete=False)



server = Server()
server.bind()
try:
	print("Serving")
	server.serve()
except KeyboardInterrupt:
	print("Exiting")
	server.close()