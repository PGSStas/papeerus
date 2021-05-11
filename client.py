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
        thread = threading.Thread(target=self._reload_all)
        thread.start()

    def input_cycle(self):
        while True:
            q = input("c - create own ring; r - join to the known ring\n")
            if q == "c":
                self.client_node.create()
                self.load_chats()
            elif q == "r":
                q = input("Please, write your invite token:\n")
                self.client_node.establish_connection(q)
                self.load_chats()
                # try:
                #     self.client_node.establish_connection(q)
                #     break
                # except Exception:
                #     pass
                # TODO: exception for existing nickname
            else:
                continue
            break

        while True:
            q = input()
            ls = q.split(' ')
            if ls[0] == "quit":
                # Exit from program
                os._exit(0)
            elif ls[0] == "invite":
                print(self.client_node.generate_invite())
            elif ls[0] == "info":
                self.client_node.print_info()
                print("Messages:", self.client_node._message_container._messages)
                print("Chats:", self._chat_data)
            elif ls[0] == "chats":
                print(self._chat_data)
            elif ls[0] == "newchat":
                print(self.generate_token())
                self.save_chats()
            elif ls[0] == "enterchat":
                self.parse_token(ls[1])
                self.save_chats()
            elif ls[0] == "reload_chat":
                self.client_node.reload_chat(self._chat_data[int(ls[1])][1])
            elif len(ls) == 2 and ls[0] == "chat" and self._is_integer(ls[1]):
                print(f"CHAT {ls[1]}:")
                chat_id = self.client_node.bytes_to_hash(self._chat_data[int(ls[1])][1])
                messages = self.client_node.local_chats.get(chat_id, [])
                for message in messages:
                    decrypted = self.parse_message(int(ls[1]), bytes.fromhex(message[1])[32:])[0]
                    if len(decrypted) == 2:
                        print(decrypted)
                    else:
                        code, what_format, data = decrypted
                        hsh = data[:min(32, len(data))]
                        if hsh in self._path_map:
                            print(self._path_map[hsh])
                            continue
                        dir = str(hashlib.sha1(self.client_node.nickname.encode()).hexdigest()) + "_media"
                        if not os.path.exists(dir):
                            os.makedirs(dir)
                        path = dir + '/' + str(hashlib.sha1(data).hexdigest()) + "." + what_format
                        print(data)
                        file = open(file=path, mode="wb")
                        file.write(data)
                        file.close()
                        print(path)
                        self._path_map[hsh] = path
            elif self._is_integer(ls[0]):
                chat_id = int(ls[0])
                list_message = []
                text_message = ""
                while True:
                    q = input()
                    ls = q.split(' ')
                    if q == "send":
                        break
                    if len(ls) > 1 and ls[0] == "attach":
                        path = q.split(" ", 1)[1]
                        if os.path.exists(path):
                            what_format = path.split(".")[-1]
                            with open(file=path,mode="rb") as file:
                                data = file.read()
                            message = (MessageCodes.FILE, what_format, data)
                            list_message.append(message)
                    else:
                        text_message += q + '\n'
                if text_message != "":
                    list_message.append((MessageCodes.TEXT, text_message))
                print(list_message)
                with self.chat_mutex:
                    list_message = self.create_message(chat_id, *list_message)
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

    def create_message(self, chat_id: int, *messages):
        final_message = []
        for message in messages:
            final_message.append(self._ciphers[chat_id].encrypt_message(pickle.dumps(message)))
        return pickle.dumps(final_message)

    def parse_message(self, chat_id: int, data: bytes):
        message_list = pickle.loads(data)
        for i in range(len(message_list)):
            message_list[i] = pickle.loads(self._ciphers[chat_id].decrypt_message(message_list[i]))
        return message_list

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
