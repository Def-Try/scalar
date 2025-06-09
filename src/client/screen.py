import curses

def reverseenumerate(data: list):
	for i in range(len(data)-1, -1, -1):
		yield (i, data[i])

TEXT_DEC_BOLD	  = 0b001
TEXT_DEC_ITALIC	= 0b010
TEXT_DEC_UNDERLINE = 0b100

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
		self.infowin.addstr(1, 1, self.client.status)
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