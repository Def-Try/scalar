class Scalar0ServerState:
    motd = "Welcome to Scalar0 server"
    channels = {0: "main"}
    users = {}
    identifier_state = {}

    @classmethod
    def from_string(cls, strstate: str):
        pass

    def to_string(self) -> str:
        pass

    def load_channel_messages(self, cid: int) -> list:
        return []