import customtkinter
import CTkMenuBar
import string
import os
import json
import random
import asyncio

try:
    from scalar.client.implementations.scalar0 import Scalar0Client
except ImportError:
    print("ScalarCore is not installed.")
    print("Install it via running next commands:")
    print("  | $ cd [path to repository]")
    print("  | $ cd api")
    print("  | $ python setup.py install")
    exit()


ALLOWED_NAME_CHARACTERS = string.ascii_letters+string.digits+"_-."


class Settings:
    name: str
    last_server_ip: str
    last_server_port: int
    
    def __init__(self):
        self.load()
    
    def load(self):
        if not os.path.isfile("data/settings.json"):
            os.makedirs("data", exist_ok=True) # exist, okay?
            with open("data/settings.json", "w") as file:
                file.write("{}")
        
        with open("data/settings.json", "r") as file:
            data = json.load(file)
        
        self.name             = data.get("name", f"user_{random.randint(10000, 99999)}")
        self.last_server_ip   = data.get("last_server_ip", "")
        self.last_server_port = data.get("last_server_port", -1)
        
        self.save()

    # saves the settings
    def save(self):
        data = {}
        
        data["name"]             = self.name
        data["last_server_ip"]   = self.last_server_ip
        data["last_server_port"] = self.last_server_port
        
        with open("data/settings.json", "w") as file:
            json.dump(data, file)
    
    def reset(self):
        with open("data/settings.json", "w") as file:
            file.write("{}")
        
        self.load()

settings: Settings = Settings()

class ChannelSidebar(customtkinter.CTkScrollableFrame):
    def __init__(self, master, channel_select, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.command = channel_select
        self._channels_list = []
        self._channels_lookup = {}
        self.add_channel(-1, "console")

    def add_channel(self, channel_id: int, name: str) -> bool:
        if self._channels_lookup.get(channel_id, None) is not None: return False
        label = customtkinter.CTkButton(self,
            text=name,
            command=lambda channel_id=channel_id: self._select_channel(channel_id),
            fg_color="transparent",
            anchor="w")
        label.grid(row=len(self._channels_list), column=0, pady=(0, 5), sticky="nswe")
        self._channels_list.append(label)
        self._channels_lookup[channel_id] = label
        return True

    def remove_channel(self, channel_id: int) -> bool:
        if self._channels_lookup.get(channel_id, None) is None: return False
        label = self._channels_lookup[channel_id]
        label.grid_forget()
        label.destroy()
        del label
        # self.reorganise()


    def _select_channel(self, channel_id):
        return self.command(channel_id)

class UserPanel(customtkinter.CTkFrame):
    name_label: customtkinter.CTkLabel
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self.name_label = customtkinter.CTkLabel(self,
            text=settings.name)
        self.name_label.grid(row=0, column=0, sticky="nswe")
        self.fgprint_label = customtkinter.CTkLabel(self,
            text="fingerprint here")
        self.fgprint_label.grid(row=1, column=0, sticky="nswe")

    def set_server_name(self, new_name: str|None = None):
        self.name_label.configure(text=new_name if new_name is not None else settings.name)

class MessageFrame(customtkinter.CTkFrame):
    name_label: customtkinter.CTkLabel
    content_label: customtkinter.CTkLabel
    def __init__(self, master, name: str, content: str, **kwargs):
        super().__init__(master, corner_radius=5, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.name_label = customtkinter.CTkLabel(self,
            text=name,
            anchor="w",
            justify="left",
            font=customtkinter.CTkFont(size=14, weight="bold"))
        self.name_label.grid(row=0, column=0, sticky="nswe", padx=(10, 3), pady=(3, 3))
        self.content_label = customtkinter.CTkLabel(self,
            text=content,
            anchor="nw")
        self.content_label.grid(row=1, column=0, sticky="nswe", padx=(10, 3), pady=(3, 0))

class MessagesFrame(customtkinter.CTkScrollableFrame):
    messages = []

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.messages = []

    def add_message(self, name: str, content: str):
        print(f"<{name}> {content}")
        message = MessageFrame(self, name, content)
        message.grid(row=len(self.messages), column=0, sticky="nswe", pady=(0, 5))
        self.messages.append(message)


class ChatFrame(customtkinter.CTkFrame):
    messages_frames: dict[int, MessagesFrame]
    message_entry: customtkinter.CTkEntry
    current_channel: int|None

    def __init__(self, master, on_enter, **kwargs):
        super().__init__(master, **kwargs)
        self.command = on_enter
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.message_entry = customtkinter.CTkEntry(self, placeholder_text="Message...")
        self.message_entry.grid(row=1, column=0, sticky="nswe")
        self.message_entry.bind("<Return>", lambda x: self._enter())
        self.messages_frames = {}
        self.current_channel = None

        self.add_channel(-1)
        self.select_channel(-1)
        self.add_message(-1, "SYSTEM", "This channel will contain client logs and can be used to run client commands")

    def _enter(self):
        text = self.message_entry.get()
        self.message_entry.delete(0, len(text)+1)
        self.command(text)

    def select_channel(self, channel_id: int) -> bool:
        if self.current_channel is not None and self.messages_frames.get(self.current_channel, None):
            self.messages_frames.get(self.current_channel, None).grid_forget()
            self.current_channel = None
        messages_frame = self.messages_frames.get(channel_id, None)
        if not messages_frame: return False
        messages_frame.grid(row=0, column=0, sticky="nswe")
        self.current_channel = channel_id
        return True

    def add_channel(self, channel_id: int) -> bool:
        if self.messages_frames.get(channel_id, None) is not None: return False
        messages_frame = MessagesFrame(self)
        self.messages_frames[channel_id] = messages_frame
        return True

    def remove_channel(self, channel_id: int) -> bool:
        if channel_id == -1: return False
        if self.messages_frames.get(channel_id, None) is None: return False
        if channel_id == self.current_channel:
            self.select_channel(-1)
        self.messages_frames[channel_id].destroy()
        del self.messages_frames[channel_id]
        return True

    def add_message(self, channel_id: int, name: str, content: str) -> bool:
        messages_frame = self.messages_frames.get(channel_id, None)
        if not messages_frame: return False
        return messages_frame.add_message(name, content)

class MenuFrame(customtkinter.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)


class MainWindow(customtkinter.CTk):
    client: Scalar0Client = Scalar0Client()

    channel_bar: ChannelSidebar = None
    userpanel: UserPanel = None
    chat_frame: ChatFrame = None

    loop: asyncio.EventLoop = None
    tasks: list = None
    channels: dict[int, str]
    current_channel: int = -1

    def __init__(self):
        super().__init__()

        self.loop = asyncio.get_event_loop()
        self.tasks = []
        self.channels = {}
        self.protocol("WM_DELETE_WINDOW", self._close)

        self.menu = CTkMenuBar.CTkMenuBar(master=self)
        self.menu.grid(row=0, column=0, columnspan=3, sticky="ew")
        self.menucascade_server = self.menu.add_cascade('Server')

        self.title("Scalar")
        self.geometry("800x600")

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.channel_bar = ChannelSidebar(self, self.select_channel)
        self.channel_bar.grid(row=1, column=0, rowspan=1, sticky="nswe")
        self.userpanel = UserPanel(self)
        self.userpanel.grid(row=2, column=0, sticky="we")

        self.chat_frame = ChatFrame(self, self.send_message)
        self.chat_frame.grid(row=1, column=1, rowspan=4, sticky="nswe")

        self.menudropdown_server = CTkMenuBar.CustomDropdownMenu(widget=self.menucascade_server)
        self.menudropdown_server_connect = self.menudropdown_server.add_option(option="Connect", command=lambda: self._dialog_connect())
        self.menudropdown_server_disconnect = self.menudropdown_server.add_option(option="Disconnect", state="disabled", command=lambda: self._dialog_disconnect())

        for method in dir(self):
            if not method.startswith("_client_event__"): continue
            self.client.event(method[15:])(getattr(self, method))

    _connect_dialog = None
    _connecting_dialog = None
    _allow_connect = True
    _allow_disconnect = False
    def _dialog_connect(self, error=""):
        if not self._allow_connect: return
        if self._connect_dialog and self._connect_dialog.winfo_exists():
            return self._connect_dialog.focus()

        dialog = customtkinter.CTkToplevel(self)
        self._connect_dialog = dialog
        dialog.focus()
        dialog.geometry("400x200")

        dialog.title("Scalar - Connect")
        dialog.grid_columnconfigure((0, 1), weight=1)
        title = customtkinter.CTkLabel(dialog, text="Enter server IP to attempt connect to", font=customtkinter.CTkFont(size=14, weight="bold"))
        title.grid(row=0, column=0, columnspan=2, sticky="nswe")
        ip_entry = customtkinter.CTkEntry(dialog)
        ip_entry.grid(row=1, column=0, columnspan=2, sticky="nswe")
        error_label = customtkinter.CTkLabel(dialog, text=error, font=customtkinter.CTkFont(size=11))
        error_label.grid(row=3, column=0, columnspan=2, sticky="nswe")
        
        ok_button = customtkinter.CTkButton(dialog, text="Connect", command=lambda: self._dialog_attempt_connect(ip_entry.get()))
        ok_button.grid(row=2, column=0, sticky="nswe")
        cancel_button = customtkinter.CTkButton(dialog, text="Cancel", command=lambda: dialog.destroy())
        cancel_button.grid(row=2, column=1, sticky="nswe")
    def _dialog_attempt_connect(self, ip):
        self._connect_dialog.destroy()
        if ip == "localhost":
            ip = "scalar://localhost:1440"

        if not ip.startswith("scalar://"):
            return self._dialog_connect("invalid scheme (has to start with 'scalar://')")
        ip = ip[9:]
        if len(ip.split(":")) > 2:
            return self._dialog_connect("invalid ip (too many ':')")
        host, port = ip.split(':') if len(ip.split(':')) == 2 else (ip, 1440)
        try:
            port = int(port)
        except ValueError:
            return self._dialog_connect("invalid port (has to be a whole number)")
        if port < 0 or port > 65535:
            return self._dialog_connect("invalid port (has to be in range 0 <= port <= 65535)")

        self._allow_connect = False
        self.menudropdown_server_connect.configure(state="disabled")
        dialog = customtkinter.CTkToplevel(self)
        self._connecting_dialog = dialog
        self._connecting_dialog.grid_rowconfigure((0, 1, 2), weight=1)
        self._connecting_dialog._progressbar = customtkinter.CTkProgressBar(dialog)
        self._connecting_dialog._progressbar.grid(row=1, column=0)
        self._connecting_dialog._progressbar.set(0)
        self._connecting_dialog._label_title = customtkinter.CTkLabel(dialog, text="Connecting", font=customtkinter.CTkFont(size=14, weight="bold"))
        self._connecting_dialog._label_title.grid(row=0, column=0)
        self._connecting_dialog._label_stage = customtkinter.CTkLabel(dialog, text="Binding", font=customtkinter.CTkFont(size=11))
        self._connecting_dialog._label_stage.grid(row=2, column=0)
        self.tasks.append(self.loop.create_task(self._connect(host, port)))
    def _dialog_disconnect(self):
        if not self._allow_disconnect:
            return
        self.client.close()
        self.menudropdown_server_disconnect.configure(state="disabled")
        self.menudropdown_server_connect.configure(state="normal")
        self._allow_connect = True
        self._allow_disconnect = False

    def add_channel(self, channel_id: int, name: str) -> bool:
        if self.channels.get(channel_id, None) is not None: return False
        self.channel_bar.add_channel(channel_id, name)
        self.chat_frame.add_channel(channel_id)
        self.channels[channel_id] = name
        return True
    def remove_channel(self, channel_id: int) -> bool:
        if self.channels.get(channel_id, None) is None: return False
        self.channel_bar.remove_channel(channel_id)
        self.chat_frame.remove_channel(channel_id)
        del self.channels[channel_id]
        return True

    def send_message(self, content):
        if self.current_channel == -1:
            return self._process_console(content)
        chan = self.client.find_channel(self.current_channel)
        if not chan: return end
        self.loop.create_task(self.client.send_message(chan, content))

    def _process_console(self, uinput):
        command = uinput[:uinput.index(" ")] if " " in uinput else uinput
        uinput = uinput[len(command)+1:]
        if command == "who":
            if not self.client.connected():
                return self.add_message(-1, "CLIENT", "Not connected, command unavailable.")
            reply = "Connected users:"
            for user in self.client._userlist:
                reply += f"\n    {user.username} / fingerprint={user.fingerprint:16x}"
            return self.add_message(-1, "CLIENT", reply)

    def select_channel(self, channel_id: int):
        self.current_channel = channel_id
        return self.chat_frame.select_channel(channel_id)
    def add_message(self, channel_id: int, name: str, content: str):
        return self.chat_frame.add_message(channel_id, name, content)

    def start(self):
        self.client.set_username(settings.name)
        self.client.generate_key("dhaes")
        self.tasks.append(self.loop.create_task(self._updater(1/60)))
        self.loop.run_forever()
        self.loop.close()

    async def _updater(self, interval):
        while True:
            self.update()
            await asyncio.sleep(interval)

    def _close(self):
        for task in self.tasks:
            task.cancel()
        self.loop.stop()
        self.destroy()
    def _reset(self):
        self.userpanel.set_server_name(None)
        for channel_id in self.channels.copy().keys():
            self.remove_channel(channel_id)
    async def _connect(self, host, port):
        try:
            await self.client.serve(host, port)
        except ConnectionRefusedError:
            self._connecting_dialog._progressbar.set(1)
            self._connecting_dialog._label_stage.configure(text="Connection refused")
            await asyncio.sleep(2)
            self._connecting_dialog.destroy()
            self._connecting_dialog = None
            self._allow_connect = True
            self.menudropdown_server_connect.configure(state="normal")
            return
        except Exception as e:
            print(e, type(e))
        self.add_message(-1, "CLIENT", "Disconnected")
        self._reset()

    async def _client_event__on_socket_broken(self, client):
        if self._connecting_dialog is not None:
            self._connecting_dialog._label_stage.configure(text="Socket broken")
            self._connecting_dialog._progressbar.set(1)
            await asyncio.sleep(2)
            self._connecting_dialog.destroy()
            self._connecting_dialog = None
            self._allow_connect = True
            self.menudropdown_server_connect.configure(state="normal")
        if not self._allow_connect:
            self._allow_connect = True
            self._allow_disconnect = False
            self.menudropdown_server_connect.configure(state="normal")
            self.menudropdown_server_disconnect.configure(state="disabled")
        self.add_message(-1, "CLIENT", "Socket broken")
    async def _client_event__on_kicked(self, client, reason):
        if self._connecting_dialog is not None:
            self._connecting_dialog._label_stage.configure(text=f"Kicked: {reason}")
            self._connecting_dialog._progressbar.set(1)
            await asyncio.sleep(2)
            self._connecting_dialog.destroy()
            self._connecting_dialog = None
            self._allow_connect = True
            self.menudropdown_server_connect.configure(state="normal")
        if not self._allow_connect:
            self._allow_connect = True
            self._allow_disconnect = False
            self.menudropdown_server_connect.configure(state="normal")
            self.menudropdown_server_disconnect.configure(state="disabled")
        self.add_message(-1, "CLIENT", f"Kicked: {reason}")
    def _client_event__on_login_complete(self, client):
        self._connecting_dialog._label_stage.configure(text="Logged in!")
        self._connecting_dialog._progressbar.set(1)
        self.menudropdown_server_disconnect.configure(state="normal")
        self._allow_disconnect = True
    def _client_event__on_uinfo_negotiated(self, client, username):
        self._connecting_dialog._label_stage.configure(text="Userinfo negotiated")
        self._connecting_dialog._progressbar.set(0.75)
        self.userpanel.set_server_name(username)
    def _client_event__on_encrypted(self, client, key):
        self._connecting_dialog._label_stage.configure(text="Connection encrypted")
        self._connecting_dialog._progressbar.set(0.5)
    def _client_event__on_hello(self, client):
        self._connecting_dialog._label_stage.configure(text="Client hello")
        self._connecting_dialog._progressbar.set(0.25)

    def _client_event__on_channellist_received(self, client):
        self._connecting_dialog.destroy()
        self._connecting_dialog = None
        for channel in client._channellist:
            self.add_channel(channel.cid, channel.name)

    def _client_event__on_user_joined(self, client, user):
        self.add_message(-1, "SERVER", f"{user.username} (fingerprint={user.fingerprint:16x}) joined")
    def _client_event__on_user_left(self, client, user):
        self.add_message(-1, "SERVER", f"{user.username} (fingerprint={user.fingerprint:16x}) left")
    def _client_event__on_message(self, client, message):
        self.add_message(message.channel.cid, f"<{message.author.username}>", message.content)
    def _client_event__on_server_message(self, client, message):
        self.add_message(message.channel.cid, "[SERVER]", message.content)