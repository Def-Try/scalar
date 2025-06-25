from dataclasses import dataclass, field

class Message: pass

@dataclass
class Channel:
    cid: int
    name: str = 'main'
    messages: list[Message] = field(default_factory=list)

    def push_message(self, message: Message):
        self.messages.append(message)

@dataclass
class User:
    username: str|None = None
    fingerprint: int|None = None

@dataclass
class Message:
    mid: int
    channel: Channel|None = None
    author: User|None = None
    content: str|None = None