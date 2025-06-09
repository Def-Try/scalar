import sys

if __name__ != "__main__":
    exit()

run = sys.argv[1] if len(sys.argv) > 1 else None
if run not in ('server', 'client'):
    print("Usage:")
    print(f"  {sys.argv[0]} [server/client]")
    exit()
if run == 'server':
    import server.__main__
    exit()
if run == 'client':
    import client.__main__
    exit()