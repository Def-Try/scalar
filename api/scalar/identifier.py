import threading

UNIVERSEBITS = 4

UNIVERSE_CHANNEL = 0
UNIVERSE_MESSAGE = 1

class Identifier:
    lock = threading.Lock()
    state = {}

    def __init__(self, state: dict=None):
        if state is not None:
            self.state = state

    def get_identifier(self, universe: int):
        with self.lock:
            if not self.state.get(universe):
                self.state[universe] = 0
            self.state[universe] += 1
            identifier = self.state[universe]
            result = universe + identifier << UNIVERSEBITS
        return result
