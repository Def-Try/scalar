
import scalar.client.implementations.scalar0 as scalar0
import scalar.primitives as primitives
import datetime

client = scalar0.Scalar0Client()
client.set_username('test')
client.generate_key('dhaes')

@client.event("on_message")
def on_message(self, message: primitives.Message):
    print(f"[#{message.channel.name}] {message.author.username}: {message.content}")
@client.event("on_server_message")
def on_server_message(self, message: primitives.Message):
    print(f"[#{message.channel.name}] SERVER: {message.content}")

@client.event("heartbeat")
def heartbeat(self, nonce: int):
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] <Heartbeat {nonce}>")
@client.event("heartbeat_missed")
def heartbeat(self, missed: int):
    print(f"<Heartbeat #{missed} missed>")

@client.event("on_login_complete")
async def on_login_complete(self):
    pass

@client.event("on_channellist_received")
async def on_channellist_received(self):
    await self.send_message(self._channellist[0], "penis")

def run(host: str = 'localhost', port: int = 1440):
    print("Starting")
    try:
        client.run(host, port)
    except KeyboardInterrupt:
        pass
    print("Bye")