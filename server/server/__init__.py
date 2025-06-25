try:
    import scalar.server.implementations.scalar0 as scalar0
    import scalar.primitives as primitives
except ImportError:
    print("ScalarCore is not installed.")
    print("Install it via running next commands:")
    print("  | $ cd [path to repository]")
    print("  | $ cd api")
    print("  | $ python setup.py install")
    exit()

server = scalar0.Scalar0Server()
server.generate_key('dhaes')

@server.event("on_message")
def on_message(self, client, message: primitives.Message):
    print(f"[#{message.channel.name}] {message.author.username}: {message.content}")
    
@server.event("heartbeat")
def heartbeat(self, client, nonce: int):
    print("<Heartbeat>")
@server.event("heartbeat_missed")
def heartbeat(self, client, missed: int):
    print(f"<Heartbeat #{missed} missed>")

def run(host: str = '', port: int = 1440):
    print("Starting")
    server.bind(host, port)
    try:
        server.run()
    except KeyboardInterrupt:
        pass
    print("Bye")