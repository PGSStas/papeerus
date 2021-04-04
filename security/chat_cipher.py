import pickle

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


class ChatCipher:
    def __init__(self, token: bytes, iv: bytes, src: str):
        assert len(token) == 32, "Invalid token"

        self.token = token
        self.src = src

        self.cipher = Cipher(algorithms.AES(self.token), modes.CBC(iv))

    def encrypt_message(self, message: bytes):
        padder = padding.PKCS7(128).padder()
        p_data = padder.update(message) + padder.finalize()
        encryptor = self.cipher.encryptor()
        e_data = encryptor.update(p_data) + encryptor.finalize()
        return e_data

    def decrypt_message(self, message: bytes):
        decryptor = self.cipher.decryptor()
        de_data = decryptor.update(message) + decryptor.finalize()
        unpadder = padding.PKCS7(128).unpadder()
        up_data = unpadder.update(de_data) + unpadder.finalize()
        return up_data

    def serialize(self, message: bytes):
        data = (self.encrypt_message(self.src.encode()), self.encrypt_message(message))
        return pickle.dumps(data)

    def deserialize(self, data: bytes):
        p_data = pickle.loads(data)
        return self.decrypt_message(p_data[0]).decode(), self.decrypt_message(p_data[1])
