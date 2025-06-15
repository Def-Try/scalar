import hashlib

from scalar.protocol.encryption.baseencryption import BaseEncryption
from scalar.protocol.encryption.dhaes_encryption import DHEncryption, DHKeypair

SUPPORTED = {
    "dhaes": [DHEncryption, DHKeypair]
}

def fingerprint_key(key_bytes: bytes):
    return hashlib.sha256(key_bytes).hexdigest()[0:16]