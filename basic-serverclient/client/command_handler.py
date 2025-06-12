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