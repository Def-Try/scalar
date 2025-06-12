from codespeak import Codespeak

from client.screen import Screen
from client.connector import Connector

import curses
import os
import json

CODESPEAK = Codespeak()
client = Connector(CODESPEAK)

os.makedirs('data/client', exist_ok=True)
config = None
try:
	with open('data/client/private.key', 'rb') as f:
		CODESPEAK.load_key(f.read())
except FileNotFoundError:
	CODESPEAK.generate_key()
	with open('data/client/private.key', 'wb') as f:
		f.write(CODESPEAK.save_key())
try:
	with open('data/client/config.json', 'r') as f:
		config = json.load(f)
except FileNotFoundError:
	pass
except json.JSONDecodeError as e:
	print('Unable to read config:')
	print(f"{e.msg} at L{e.lineno} col{e.colno}")
	exit()
client.host = config.get('host')
client.port = config.get('port')
client.oname = config.get('name')

def main(stdscr):
	if curses.has_colors():
		curses.start_color()
		for i in range(0, 16):
			curses.init_pair(i+1, i+1, curses.COLOR_BLACK)
	screen = Screen(client, stdscr)
	screen.push_to_log("WELCOME", "Welcome to Scalar")
	screen.push_to_log("WELCOME", "All your settings are automatically saved")
	screen.push_to_log("WELCOME", "Some useful commands:")
	# screen.push_to_log("WELCOME", "  /reset [YESIAMSUREPLEASEFORGET]  Delete all your configuration and exit")
	screen.push_to_log("WELCOME", "  /exit                         Exit")
	screen.push_to_log("WELCOME", "  /name <name>                  Change your display name")
	screen.push_to_log("WELCOME", "  /connect <host> <port>        Connect to codespeak server")
	screen.push_to_log("WELCOME", "  /reconnect                    Reconnect to last connected server")
	screen.push_to_log("WELCOME", "  /help                         Show commands help")
	screen.push_to_log("WELCOME", f"Your key fingerprint is {CODESPEAK.fingerprint(CODESPEAK.public_key())}")

	while True:
		screen.update()

try:
	curses.wrapper(main)
except KeyboardInterrupt as e:
	client.close()
	print("Bye")
except SystemExit:
	client.close()
	print("Bye")