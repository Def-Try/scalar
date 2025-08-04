import customtkinter
import string
import os
import json
import random
import asyncio
from scalar.client.implementations.scalar0 import Scalar0Client


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
        self.add_channel(-1, "logs")

    def add_channel(self, channel_id: int, name: str):
        label = customtkinter.CTkButton(self,
            text=name,
            command=lambda channel_id=channel_id: self._select_channel(channel_id),
            fg_color="transparent",
            anchor="w")
        label.grid(row=len(self._channels_list), column=0, pady=(0, 5), sticky="nswe")
        self._channels_lookup[len(self._channels_list)] = label
        self._channels_list.append(label)


    def _select_channel(self, channel_id):
        return self.command(channel_id)

class UserPanel(customtkinter.CTkFrame):
    name_label: customtkinter.CTkLabel
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self.name_label = customtkinter.CTkLabel(self,
            text=settings.name)
        self.name_label.grid(row=0, column=0, sticky="nswe")

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
        message.grid(row=len(self.messages), column=0, sticky="nswe")
        self.messages.append(message)


class ChatFrame(customtkinter.CTkFrame):
    messages_frames: dict[int, MessagesFrame]
    message_entry: customtkinter.CTkEntry
    current_channel: int|None

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.message_entry = customtkinter.CTkEntry(self, placeholder_text="Message...")
        self.message_entry.grid(row=1, column=0, sticky="nswe")
        self.messages_frames = {}
        self.current_channel = None

        self.add_channel(-1)
        self.select_channel(-1)
        self.add_message(-1, "SYSTEM", "This channel will contain client logs")

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
        if self.messages_frames.get(channel_id, None): return False
        messages_frame = MessagesFrame(self)
        self.messages_frames[channel_id] = messages_frame
        return True

    def add_message(self, channel_id: int, name: str, content: str) -> bool:
        messages_frame = self.messages_frames.get(channel_id, None)
        if not messages_frame: return False
        return messages_frame.add_message(name, content)      

class MainWindow(customtkinter.CTk):
    client: Scalar0Client = Scalar0Client()

    channel_bar: ChannelSidebar = None
    userpanel: UserPanel = None
    chat_frame: ChatFrame = None

    loop = None
    tasks = None

    def __init__(self):
        super().__init__()

        self.loop = asyncio.get_event_loop()
        self.tasks = []
        self.protocol("WM_DELETE_WINDOW", self.close)

        self.title("Scalar")
        self.geometry("800x600")

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.channel_bar = ChannelSidebar(self, self.select_channel)
        self.channel_bar.grid(row=0, column=0, rowspan=1, sticky="nswe")
        self.userpanel = UserPanel(self)
        self.userpanel.grid(row=1, column=0, sticky="we")

        self.chat_frame = ChatFrame(self)
        self.chat_frame.grid(row=0, column=1, rowspan=4, sticky="nswe")

        self.add_channel(0, "testing")

        for method in dir(self):
            if not method.startswith("_client_event__"): continue
            self.client.event(method[15:])(getattr(self, method))

    def add_channel(self, channel_id: int, name: str):
        self.channel_bar.add_channel(channel_id, name)
        self.chat_frame.add_channel(channel_id)
    def select_channel(self, channel_id: int):
        return self.chat_frame.select_channel(channel_id)
    def add_message(self, channel_id: int, name: str, content: str):
        return self.chat_frame.add_message(channel_id, name, content)

    def start(self):
        self.client.set_username(settings.name)
        self.client.generate_key("dhaes")
        self.tasks.append(self.loop.create_task(self.client.serve("localhost", 1440)))
        self.tasks.append(self.loop.create_task(self._updater(1/60)))
        self.loop.run_forever()
        self.loop.close()

    async def _updater(self, interval):
        while True:
            self.update()
            await asyncio.sleep(interval)

    def close(self):
        for task in self.tasks:
            task.cancel()
        self.loop.stop()
        self.destroy()

    def _client_event__on_login_complete(self, client):
        self.add_message(-1, "CLIENT", "Logged in!")