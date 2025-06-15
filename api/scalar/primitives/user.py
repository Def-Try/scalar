from dataclasses import dataclass

@dataclass
class User:
    username: str|None = None
    fingerprint: str|None = None