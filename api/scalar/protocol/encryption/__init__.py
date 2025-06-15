import hashlib

from scalar.protocol.encryption.baseencryption import BaseEncryption
from scalar.protocol.encryption.dhaes_encryption import DHAESEncryption, DHKeypair

SUPPORTED = {
    "dhaes": [DHAESEncryption, DHKeypair]
}

def fingerprint_key(key: str):
    return hashlib.sha256(key.encode()).hexdigest()[0:16]