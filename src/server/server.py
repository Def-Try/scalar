import socket
import select
from server.client import Client

class Server:
	private_key = None
	motd = None
	def __init__(self, private_key, motd):
		self.private_key = private_key
		self.motd = motd
		self.clients = {}
		self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

	def bind(self, host, port):
		self.socket.bind((host, port))
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