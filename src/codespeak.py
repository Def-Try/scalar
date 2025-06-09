from cryptography.hazmat.primitives import serialization, hashes, padding
from cryptography.hazmat.primitives.asymmetric import dh
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
import os
import hashlib

P = 0xFFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD129024E088A67CC74020BBEA63B139B22514A08798E3404DDEF9519B3CD3A431B302B0A6DF25F14374FE1356D6D51C245E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7EDEE386BFB5A899FA5AE9F24117C4B1FE649286651ECE45B3DC2007CB8A163BF0598DA48361C55D39A69163FA8FD24CF5F83655D23DCA3AD961C62F356208552BB9ED529077096966D670C354E4ABC9804F1746C08CA18217C32905E462E36CE3BE39E772C180E86039B2783A2EC07A28FB5C55DF06F4C52C9DE2BCBF6955817183995497CEA956AE515D2261898FA051015728E5A8AACAA68FFFFFFFFFFFFFFFF
G = 2

class Codespeak:
	GENERATOR = 2
	KEY_SIZE = 512

	params_numbers = dh.DHParameterNumbers(P, G)
	parameters = params_numbers.parameters()
	private_key = None
	shared_key = None
	def __init__(self):
		pass
	def load_key(self, key):
		self.private_key = serialization.load_pem_private_key(key, None)
	def generate_key(self):
		self.private_key = self.parameters.generate_private_key()
	def save_key(self):
		return self.private_key.private_bytes(
			encoding=serialization.Encoding.PEM,
			format=serialization.PrivateFormat.PKCS8,
			encryption_algorithm=serialization.NoEncryption()
		)
	def fingerprint(self, pubkey):
		return hashlib.sha256(pubkey).hexdigest()[0:8]
	def public_key(self):
		return self.private_key.public_key().public_bytes(
			encoding=serialization.Encoding.PEM,
			format=serialization.PublicFormat.SubjectPublicKeyInfo
		)
	def exchange(self, public_bytes):
		shared = self.private_key.exchange(serialization.load_pem_public_key(public_bytes))
		self.shared_key = HKDF(
			algorithm=hashes.SHA256(),
			length=32,
			salt=None,
			info=b'handshake data',
		).derive(shared)

	def encrypt(self, data):
		iv = os.urandom(12)
		encryptor = Cipher(
			algorithms.AES(self.shared_key),
			modes.GCM(iv)
		).encryptor()
		crypted = encryptor.update(data) + encryptor.finalize()
		return iv, encryptor.tag, crypted
	def decrypt(self, iv, tag, crypted):
		decryptor = Cipher(
			algorithms.AES(self.shared_key),
			modes.GCM(iv, tag)
		).decryptor()
		data = decryptor.update(crypted) + decryptor.finalize()
		return data