import hashlib

from scalar.protocol.encryption.baseencryption import BaseEncryption
from scalar.protocol.encryption.dhencryption import DHEncryption, DHKeypair

SUPPORTED = {
    "dh": [DHEncryption, DHKeypair]
}

def fingerprint_key(key_bytes: bytes):
    return hashlib.sha256(key_bytes).hexdigest()[0:16]