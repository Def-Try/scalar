from codespeak import Codespeak
from server.server import Server

import os
import json

HOST, PORT = '', 1440
MOTD = ("""
Welcome to server!

This is an example MOTD.
Server owner can change it by altering contents in "data/server/motd.txt" file.
""").strip()

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

server = Server(PRIVATE_KEY, MOTD)
server.bind(HOST, PORT)
try:
	print("Serving")
	server.serve()
except KeyboardInterrupt:
	print("Exiting")
	server.close()