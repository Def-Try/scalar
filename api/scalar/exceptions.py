class ScalarException(Exception):
    """
    Base Scalar exception class
    """

class SocketLeadsToVoid(ScalarException):
    """
    Raised when attempted to read, write, or close an unconnected or unbound socket.
    """

class SocketAlreadyConnected(ScalarException):
    """
    Raised when attempted to connect or bind a socket that's already connected or bound.
    """

class SocketBroken(ScalarException):
    """
    Raised when low-level function fails to read or write to a socket due to other side closing connection.
    """

class SocketTimedOut(ScalarException):
    """
    Raised when read from socket times out
    """

class ClientConnectionError(ScalarException):
    """
    Raised when Client failed to connect to server
    """

class UnexpectedPacket(ScalarException):
    """
    Raised when an unexpected packet is received
    """

class ClientKicked(ScalarException):
    """
    Raised when client was kicked from the server
    """

class EncryptionKeysUnsupported(ScalarException):
    """
    Raised when encryption doesn't exist or it doesn't implement key loading
    """

class ClientNoKeyProvided(ScalarException):
    """
    Raised when encryption doesn't have key loaded
    """

class PacketUnregistered(ScalarException):
    """
    Raised when attempting to send an unregistered packet
    """
class PacketRegistered(ScalarException):
    """
    Raised when attempting to register packet with set and registered packet ID
    """
class PacketUnknown(ScalarException):
    """
    Raised when received packet is unknown
    """
class PacketUnknownSide(ScalarException):
    """
    Raised when packet receiving/registerign side is unknown
    """

class ConnectionTimedOut(ScalarException):
    """
    Raised when connected client or server skipped too many heartbeat attempts
    """

class ClientNoNameSpecified(ScalarException):
    """
    Raised when client tries to connect without a name set
    """
class ClientConnected(ScalarException):
    """
    Raised when trying to execute an action that's impossible while connected
    """