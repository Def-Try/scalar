from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import os

from scalar.protocol.encryption.baseencryption import BaseEncryption
from scalar.protocol.encryption.dhkeypair import DHKeypair

class DHAESEncryption(BaseEncryption):
    keypair: DHKeypair

    def __init__(self, keypair: DHKeypair):
        self.keypair = keypair

    def public_key(self):
        return self.keypair.public_key()
    
    def shared_key(self):
        return self.keypair.shared_key
    
    def exchange(self, public_bytes: bytes):
        self.keypair.derive(public_bytes)

    def encrypt(self, message):
        iv = os.urandom(12)
        encryptor = Cipher(
            algorithms.AES(self.shared_key()),
            modes.GCM(iv)
        ).encryptor()
        encrypted = encryptor.update(message) + encryptor.finalize()
        return iv+encryptor.tag+encrypted
    
    def decrypt(self, message):
        iv = message[0:12]; message = message[12:]
        tag = message[0:16]; message = message[16:]
        decryptor = Cipher(
            algorithms.AES(self.shared_key()),
            modes.GCM(iv, tag)
        ).decryptor()
        decrypted = decryptor.update(message) + decryptor.finalize()
        return decrypted
