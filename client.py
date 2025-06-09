from codespeak import Codespeak
import packets
import constants

import curses
import socket
import threading
import random
import json
import os

CODESPEAK = Codespeak()

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

TEXT_DEC_BOLD	  = 0b001
TEXT_DEC_ITALIC	= 0b010
TEXT_DEC_UNDERLINE = 0b100

class CommandHandler:
	def __init__(self):
		self.register("help", "Show this text", "[page:int]", self._help)
	def _help(self, page=1):
		pages = int(len(self.commands)/10+1)
		page = min(max(1, page), pages)-1
		text = f"Help (page {page+1}/{pages})\n"
		maxlen = 0
		ptrn = lambda command, data: f"{command}{' '+data[0] if data[0] != '' else ''}"
		for command, data in list(self.commands.items())[10*(page):10*(page+1)]:
			maxlen = max(maxlen, len(ptrn(command, data)))
		for command, data in list(self.commands.items())[10*(page):10*(page+1)]:
			head = ptrn(command, data)
			text += head+' '+' '*(maxlen-len(head))+data[2]+'\n'
		return text[:-1]
	commands = {}
	def parse_args_command(self, arglist):
		i = 0
		done_required = False
		required = 0
		args = []
		while i < len(arglist):
			ch = arglist[i]
			if ch == '[':
				done_required = True
				name_ = ""
				type_ = ""
				i += 1
				while i < len(arglist):
					ch2 = arglist[i]
					if ch2 == ":":
						break
					if ch2 == "]":
						break
					name_ += ch2
					i += 1
				if arglist[i] == ":":
					i += 1
					while i < len(arglist):
						ch2 = arglist[i]
						if ch2 == "]":
							break
						type_ += ch2
						i += 1
				args.append(('opt', name_, type_ if type_ != '' else 'any'))
			if ch == '<':
				if done_required:
					raise ValueError("required argument after optional")
				required += 1
				name_ = ""
				type_ = ""
				i += 1
				while i < len(arglist):
					ch2 = arglist[i]
					if ch2 == ":":
						break
					if ch2 == ">":
						break
					name_ += ch2
					i += 1
				if arglist[i] == ":":
					i += 1
					while i < len(arglist):
						ch2 = arglist[i]
						if ch2 == ">":
							break
						type_ += ch2
						i += 1
				args.append(('req', name_, type_ if type_ != '' else 'str'))
			i += 1
		return required, args
	def parse_args_input(self, args, arglist):
		argslist = ['']
		quote = None
		i = 0
		while i < len(arglist):
			ch = arglist[i]
			if ch == '\\' and quote is None:
				argslist[-1] += arglist[i+1]
				i += 2
				continue
			if (ch == '"' or ch == "'") and quote is None:
				quote = ch
				i += 1
				continue
			if (ch == '"' or ch == "'") and quote == ch:
				quote = None
				i += 1
				continue
			if ch == ' ' and quote is None:
				argslist.append('')
				i += 1
				continue
			argslist[-1] += ch
			i += 1
		if argslist == ['']: return []
		return argslist
	def register(self, command, desc, args, callback):
		self.commands[command] = [args, callback, desc]
	def exec(self, inp):
		command = inp.split(' ')[0]
		arglist = inp[len(command)+1:]
		cmd = self.commands.get(command)
		if cmd is None:
			return f"no such command: {command}"
		required, args = self.parse_args_command(cmd[0])
		args_parsed = self.parse_args_input(args, arglist)
		if len(args_parsed) > len(args):
			return f"too many arguments ({len(args_parsed)} > {len(args)})"
		if len(args_parsed) < required:
			return f"too few arguments ({len(args_parsed)} < {required})"
		args_final = []
		for i, (arg_cmd, arg_inp) in enumerate(zip(args, args_parsed)):
			arg_type, arg_name, arg_val_type = arg_cmd
			try:
				arg_inp = eval(f"{arg_val_type}({repr(arg_inp)})")
			except ValueError:
				return f"argument #{i+1} ({arg_name}) should be of type {arg_val_type}"
			args_final.append(arg_inp)
		return cmd[1](*args_final)

class ClientState:
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
	def __init__(self):
		self.commands_init()
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
			return
		except json.JSONDecodeError as e:
			print('Unable to read config:')
			print(f"{e.msg} at L{e.lineno} col{e.colno}")
			exit()
		self.host = config.get('host')
		self.port = config.get('port')
		self.oname = config.get('name')

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
		iv, tag, encrypted = CODESPEAK.encrypt(packet.pack())
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
		packet = CODESPEAK.decrypt(iv, tag, encrypted)
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
			f.write(CODESPEAK.save_key())
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
		pub = CODESPEAK.public_key()
		self._send(len(pub).to_bytes(2, 'little'))
		self._send(pub)
		server_pub = self._recv(int.from_bytes(self._recv(2), 'little'))
		try:
			CODESPEAK.exchange(server_pub)
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

def reverseenumerate(data: list):
	for i in range(len(data)-1, -1, -1):
		yield (i, data[i])

DISALLOW_INPUT = [getattr(curses, i) for i in list(filter(lambda x: x.startswith("KEY_"), dir(curses)))]
class Screen:
	main_scroll = 0
	current_input = ''
	def __init__(self, client, stdscr):
		self.client = client
		self.client.screen = self

		self.stdscr = stdscr
		self.stdscr.timeout(0)
		self.stdscr.refresh()

		self.inputwin = curses.newwin(0, 0, 0, 0)
		self.infowin = curses.newwin(0, 0, 0, 0)
		self.mainpad = curses.newpad(2, 2)
		self.mainpad.scrollok(True)

		self.resize()

	def resize(self):
		self.height, self.width = self.stdscr.getmaxyx()
		self.stdscr.clear()
		curses.resize_term(self.height, self.width)
		self.stdscr.refresh()
		self.inputwin.border(' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ')
		self.inputwin.resize(5, self.width)
		self.inputwin.mvwin(self.height-5, 0)
		self.inputwin.box()
		self.inputwin.addstr(0, 2, "INPUT")
		self.inputwin.refresh()
		self.infowin.border(' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ')
		self.infowin.resize(3, self.width)
		self.infowin.box()
		self.infowin.addstr(0, 2, "STATUS")
		self.infowin.addstr(1, 1, client.status)
		self.infowin.refresh()
		self.mainpad.border(' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ')
		self.mainpad.resize(8192, self.width)
		self.mainpad.box()
		self.refresh()

	def parse_markup(self, text) -> list:
		result = [['', 0, None]]
		color_stack = [None]
		i = 0
		flags = 0b000
		while i < len(text):
			ch = text[i]
			nch = text[i + 1] if i + 1 < len(text) else ''

			if ch == '\\' and i + 1 < len(text):
				result[-1][0] += nch
				i += 2
				continue
			if ch == '*' and nch == '*':
				if flags & TEXT_DEC_BOLD != 0:
					flags -= TEXT_DEC_BOLD
				else:
					flags += TEXT_DEC_BOLD
				result.append(['', flags, color_stack[-1]])
				i += 2
				continue
			if ch == '*':
				if flags & TEXT_DEC_ITALIC != 0:
					flags -= TEXT_DEC_ITALIC
				else:
					flags += TEXT_DEC_ITALIC
				result.append(['', flags, color_stack[-1]])
				i += 1
				continue
			if ch == '_':
				if flags & TEXT_DEC_UNDERLINE != 0:
					flags -= TEXT_DEC_UNDERLINE
				else:
					flags += TEXT_DEC_UNDERLINE
				result.append(['', flags, color_stack[-1]])
				i += 1
				continue
			if ch == '!':
				if nch in '0123456789abcdef':
					i += 2
					color_stack.append(int(nch, 16))
					result.append(['', flags, color_stack[-1]])
					continue
				if nch == 'x':
					if color_stack.pop() != None:
						i += 2
						result.append(['', flags, color_stack[-1]])
						continue
					color_stack.append(None)

			result[-1][0] += ch
			i += 1
		if flags != 0:
			for flag, trigger in zip([TEXT_DEC_BOLD, TEXT_DEC_ITALIC, TEXT_DEC_UNDERLINE], ["**", "*", "_"]):
				if flags & flag == 0:
					continue
				for i, t in reverseenumerate(result):
					if t[1] & flag != 0:
						t[1] -= flag
					if t[1] & flag == 0:
						t[0] = trigger+t[0]
						break

		result = [t for t in result if t[0] != '']
		return result
	def get_raw_text(self, markup_parsed):
		return ''.join(i[0] for i in markup_parsed)
	def get_text_size(self, text):
		tall = 0
		wide = 0
		width = (self.width - 2)
		for line in text.split('\n'):
			tall += 1 + (len(line) // width)
			wide = max(wide, len(line) % width)
		return tall, wide

	def push_to_log(self, who, message):
		self.push_message(who, message, "[]")
	def push_message(self, uname, message, brackets='<>'):
		width = self.width - 2 - (len(uname)+3) - 1
		tagged = self.parse_markup(message)
		tall, wide = self.get_text_size(self.get_raw_text(tagged))
		y, x = 0, 0

		self_ping = f'@{self.client.uname}'
		pinged = None
		if message == self_ping:
			pinged = 0
		if self_ping+' ' in message:
			pinged = message.find(self_ping+' ')
		if message.endswith(self_ping):
			pinged = len(message)-len(self_ping)
		if pinged is not None:
			curses.beep()


		self.mainpad.border(' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ')
		self.mainpad.scroll(tall)
		self.mainpad.addstr(8192 - 2 - tall, 1, f"{brackets[0]}{uname}{brackets[1]}")
		ch_num = 0
		for text in tagged:
			attrs = 0
			attrs += curses.A_BOLD if text[1] & TEXT_DEC_BOLD != 0 else 0
			attrs += curses.A_ITALIC if text[1] & TEXT_DEC_ITALIC != 0 else 0
			attrs += curses.A_UNDERLINE if text[1] & TEXT_DEC_UNDERLINE != 0 else 0
			attrs += curses.color_pair(text[2]) if text[2] is not None else 0
			for ch in text[0]:
				ch_num += 1
				if ch == '\n':
					x = 0
					y = y + 1
					continue
				self.mainpad.addstr(8192 - 2 - tall + y, len(uname)+4+x, ch, attrs + (curses.A_REVERSE if pinged is not None and (ch_num >= pinged and ch_num-pinged <= len(self_ping)) else 0))
				x += 1
				if x > width:
					x = 0
					y = y + 1
		self.mainpad.box()

	def refresh(self):
		self.mainpad.refresh(
			8192 - (self.height-8) - self.main_scroll, 0,
			3, 0,
			self.height-6, self.width-1
		)

	def on_keypress(self, recv):
		width = self.width - 2
		if recv == curses.KEY_UP:
			self.main_scroll = min(8192 - self.height, self.main_scroll + 1)
			self.refresh()
			return
		if recv == curses.KEY_DOWN:
			self.main_scroll = max(0, self.main_scroll - 1)
			self.refresh()
			return
		ignore = False
		if recv in [ord('\b'), ord('\x7f'), curses.KEY_BACKSPACE]:
			self.current_input = self.current_input[:-1]
			ignore = True
		if recv in [ord('\n'), curses.KEY_ENTER]:
			self.client.input(self.current_input)
			self.current_input = ""
			self.inputwin.addstr(1, 1, " "*width)
			self.inputwin.addstr(2, 1, " "*width)
			self.inputwin.addstr(3, 1, " "*width)
			self.inputwin.refresh()
			return
		if recv in [529]: # ctrl-enter
			self.current_input += '\n'
			ignore = True
		if not ignore and recv in DISALLOW_INPUT:
			return
		if not ignore:
			ch = chr(recv)
			self.current_input += ch
		self.inputwin.addstr(1, 1, " "*width)
		self.inputwin.addstr(2, 1, " "*width)
		self.inputwin.addstr(3, 1, " "*width)
		tall = 0
		uinp_display = ""
		for line in self.current_input.split('\n'):
			tall += 1 + (len(line) // width)
			uinp_display += line
			uinp_display += ' ' * ((width-2) - (len(line) % width))
		self.inputwin.addstr(1, 1, uinp_display[width*(0+tall-3):width*(1+tall-3)])
		self.inputwin.addstr(2, 1, uinp_display[width*(1+tall-3):width*(2+tall-3)])
		self.inputwin.addstr(3, 1, uinp_display[width*(2+tall-3):width*(3+tall-3)])
		self.inputwin.refresh()

	def update(self):
		client_status = self.client.status
		if self.client.laststatus != client_status:
			self.client.laststatus = client_status
			self.infowin.addstr(1, 1, " "*(self.width-2))
			self.infowin.addstr(1, 1, client_status)
			self.infowin.refresh()
		recv = self.stdscr.getch()
		if recv == curses.KEY_RESIZE:
			self.resize()
		if recv != -1:
			self.on_keypress(recv)
		self.refresh()


client = ClientState()


def main(stdscr):
	if curses.has_colors():
		curses.start_color()
		for i in range(0, 16):
			curses.init_pair(i+1, i+1, curses.COLOR_BLACK)
	screen = Screen(client, stdscr)
	screen.push_to_log("WELCOME", "Welcome to codespeak -- TODO: come up with a better name")
	screen.push_to_log("WELCOME", "All your settings are automatically saved")
	screen.push_to_log("WELCOME", "Some useful commands:")
	# screen.push_to_log("WELCOME", "  /reset [YESIAMSUREPLEASEFORGET]  Delete all your configuration and exit")
	screen.push_to_log("WELCOME", "  /exit                         Exit")
	screen.push_to_log("WELCOME", "  /name <name>                  Change your display name")
	screen.push_to_log("WELCOME", "  /connect <host> <port>        Connect to codespeak server")
	screen.push_to_log("WELCOME", "  /reconnect                    Reconnect to last connected server")
	screen.push_to_log("WELCOME", "  /help                         Show commands help")
	screen.push_to_log("WELCOME", f"Your key fingerprint is {CODESPEAK.fingerprint(CODESPEAK.public_key())}")

	# client.push_message("testing", ' '.join([f"fuckoff{i:03d}" for i in range(64)]))
	# client.push_message("testing", "**bold** *italic* _underline_ ***bold italic***")

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
