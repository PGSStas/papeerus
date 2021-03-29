import pickle

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


class ChatCipher:
    def __init__(self, token, src, iv):
        assert isinstance(token, bytes), "Invalid token"
        assert isinstance(iv, bytes), "Invalid iv"
        assert len(token) == 160, "Invalid token"

        self.token = token
        self.src = src

        self.cipher = Cipher(algorithms.AES(self.token), modes.CBC(iv))

    def encrypt_message(self, message):
        assert isinstance(message, bytes), "Invalid message"

        padder = padding.PKCS7(128).padder()
        p_data = padder.update(message) + padder.finalize()
        encryptor = self.cipher.encryptor()
        e_data = encryptor.update(p_data) + encryptor.finalize()
        return e_data

    def decrypt_message(self, message):
        assert isinstance(message, bytes), "Invalid message"

        decryptor = self.cipher.decryptor()
        de_data = decryptor.update(message) + decryptor.finalize()
        unpadder = padding.PKCS7(128).unpadder()
        up_data = unpadder.update(de_data) + unpadder.finalize()
        return up_data

    def serialize(self, message):
        data = {self.encrypt_message(self.src), self.encrypt_message(message)}
        return pickle.dumps(data)

    def deserialize(self, data):
        p_data = pickle.loads(data)
        return {self.decrypt_message(p_data[0]), self.decrypt_message(p_data[1])}
