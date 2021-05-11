import os
import pickle
import threading

from chord.table_node import TableNode
from chord.decorators import execute_periodically
from security.chat_cipher import ChatCipher
from message_codes import MessageCodes
from exceptions.registration_exeptions import ExistingNameException


class Client:
    _chat_data = []
    _ciphers = []

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
            elif q == "r":
                q = input("Please, write your invite token:\n")
                try:
                    self.client_node.establish_connection(q)
                except ExistingNameException as ex:
                    print(ex)
                    continue
                break
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
            elif ls[0] == "enterchat":
                self.parse_token(ls[1])
            elif ls[0] == "reload_chat":
                self.client_node.reload_chat(self._chat_data[int(ls[1])][1])
            elif len(ls) == 2 and ls[0] == "chat" and self._is_integer(ls[1]):
                print(f"CHAT {ls[1]}:")
                chat_id = self.client_node.bytes_to_hash(self._chat_data[int(ls[1])][1])
                messages = self.client_node.local_chats.get(chat_id, [])
                for message in messages:
                    print(self.parse_message(int(ls[1]), bytes.fromhex(message[1])[32:]))
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
                            data = open(file=path, mode="rb").read()
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
