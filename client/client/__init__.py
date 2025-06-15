try:
    import scalar.client.implementations.scalar0 as scalar0
    import scalar.primitives as primitives
except ImportError:
    print("ScalarCore is not installed.")
    print("Install it via running next commands:")
    print("  | $ cd [path to repository]")
    print("  | $ cd api")
    print("  | $ python setup.py install")
    exit()

client = scalar0.Scalar0Client()
client.set_username('test')
client.generate_key('dhaes')

@client.event("on_message")
def on_message(self, user: primitives.User, message: str):
    print(f"{user.username}: {message}")
@client.event("on_server_message")
def on_server_message(self, message: str):
    print(f"SERVER: {message}")

@client.event("heartbeat")
def heartbeat(self, nonce: int):
    print("<Heartbeat>")
@client.event("heartbeat_missed")
def heartbeat(self, missed: int):
    print(f"<Heartbeat #{missed} missed>")

@client.event("on_login_complete")
async def on_login_complete(self):
    await self.send_message("hi")

def run(host: str = 'localhost', port: int = 1440):
    print("Starting")
    try:
        client.run(host, port)
    except KeyboardInterrupt:
        pass
    print("Bye")