try:
    import scalar.server.server as sserver
    import scalar.protocol.packets as spackets
except ImportError:
    print("ScalarCore is not installed.")
    print("Install it via running next commands:")
    print("  | $ cd [path to repository]")
    print("  | $ cd api")
    print("  | $ python setup.py install")
    exit()

server = sserver.Server()

def run(host: str = '', port: int = 1440):
    print("Starting")
    server.bind(host, port)
    try:
        server.run()
    except KeyboardInterrupt:
        pass
    print("Bye")