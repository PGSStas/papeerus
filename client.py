import os
import pickle
import random
import threading
import json
import hashlib

from chord.table_node import TableNode
from chord.decorators import execute_periodically
from security.chat_cipher import ChatCipher
from message_codes import MessageCodes


class Client:
    _chat_data = []
    _ciphers = []
    _path_map = {}

    def __init__(self):
        print("Started client")

        self.client_node = TableNode()
        self.chat_mutex = threading.Lock()

        self.process = threading.Thread(target=self._reload_all)
        self.process.daemon = True
        self.process.start()

    def create_network(self, nickname):
        self.client_node.create(nickname)
        return self.client_node.generate_invite()

    def register_network(self, token: str, nickname: str):
        return self.client_node.establish_connection(token, nickname)

    def create_chat(self):
        self.save_chats()
        return self.generate_token()

    def enter_chat(self, token: str):
        self.save_chats()
        self.parse_token(token)

    def _reload_chat(self, chat_id: int):
        if chat_id < 0 or chat_id >= len(self._chat_data):
            return False
        self.client_node.reload_chat(self._chat_data[chat_id][1])
        return True

    def get_chat_data(self, chat_id: int):
        if not self._reload_chat(chat_id):
            return None
        chat_hash = self.client_node.bytes_to_hash(self._chat_data[chat_id][1])
        messages = self.client_node.local_chats.get(chat_hash, [])
        ans = []
        for message in messages:
            salt = bytes.fromhex(message[1])[32:]
            deciphered_message = self.parse_message(chat_id, bytes.fromhex(message[1])[32:])
            ans.append((message[0], salt, deciphered_message[0], deciphered_message[1]))
        return ans

    def send_message(self, chat_id: int, message: str, files):
        list_message = [(MessageCodes.TEXT, message)]
        for path in files:
            if os.path.exists(path):
                what_format = path.split(".")[-1]
                data = open(file=path, mode="rb").read()
                message = (MessageCodes.FILE, what_format, data)
                list_message.append(message)
        with self.chat_mutex:
            list_message = self.create_message(chat_id, self.client_node.nickname, *list_message)
            self.client_node.send_chat_message(self._chat_data[chat_id][1], os.urandom(32) + list_message)

    def generate_token(self):
        iv = os.urandom(16)
        token = os.urandom(32)
        while [item for item in self._chat_data if item[0] == token]:
            token = os.urandom(32)
        self._chat_data.append((token, iv))
        self._ciphers.append(ChatCipher(token, iv, self.client_node.nickname))
        return token.hex() + iv.hex()

    def parse_token(self, data: hex):
        data = bytes.fromhex(data)
        token = data[:32]
        iv = data[32:]
        self._chat_data.append((token, iv))
        self._ciphers.append(ChatCipher(token, iv, self.client_node.nickname))

    def create_message(self, chat_id: int, nickname: str, *messages):
        final_message = []
        for message in messages:
            final_message.append(self._ciphers[chat_id].encrypt_message(pickle.dumps(message)))
        return pickle.dumps((nickname, final_message))

    def parse_message(self, chat_id: int, data: bytes):
        nickname, message_list = pickle.loads(data)
        for i in range(len(message_list)):
            message_list[i] = pickle.loads(self._ciphers[chat_id].decrypt_message(message_list[i]))
        return nickname, message_list

    def load_chats(self):
        path = file = self.client_node.nickname + "_keys.json"
        if os.path.exists(path):
            jfile = open(file=path, mode="r")
            data_hex = json.load(jfile)
            jfile.close()
            data_bytes = []
            for i, j in data_hex:
                data_bytes.append((bytes.fromhex(i), bytes.fromhex(j)))
            self._chat_data = data_bytes
            self._ciphers = []
            for token, iv in self._chat_data:
                self._ciphers.append(ChatCipher(token, iv, self.client_node.nickname))

    def save_chats(self):
        data_hex = []
        for i, j in self._chat_data:
            data_hex.append((bytes.hex(i), bytes.hex(j)))
        jstr = json.dumps(data_hex)
        file = open(file=self.client_node.nickname + "_keys.json", mode="w")
        file.write(jstr)
        file.close()

    @execute_periodically(5)
    def _reload_all(self):
        with self.chat_mutex:
            for token in self._chat_data:
                self.client_node.reload_chat(token[1])
        self.client_node.distribute_chats()

    @staticmethod
    def _is_integer(num):
        try:
            int(num)
        except ValueError:
            return False
        else:
            return True
