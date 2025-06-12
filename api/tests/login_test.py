import os
import sys
import inspect

# import from parent folder
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir) 

from scalar.server.server import Server
from scalar.client.client import Client

import threading

server_complete = False
client_complete = False

server = Server()
server.generate_key('dh')
server.bind('', 1440)
@server.event("on_login_complete")
async def on_server_login_complete(self, client):
    global server_complete
    print(f"[SERVER] [{client.format_address()}] Login complete!")
    server_complete = True
    if server_complete and client_complete:
        os._exit(0)
threading.Thread(target=server.run, daemon=True).start()

client = Client(username='googer_')
client.generate_key('dh')
@client.event("on_login_complete")
async def on_client_login_complete(self):
    global client_complete
    print("[CLIENT] Login complete!")
    client_complete = True
    if server_complete and client_complete:
        os._exit(0)
client.run('localhost', 1440)