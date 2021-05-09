import os
import pickle
import socket
import sys
import threading
import time
from typing import Any, Tuple

from chord.message_container import MessageContainer
from security.chat_cipher import ChatCipher
from hashlib import sha1
from chord.command_codes import CommandCodes
from chord.decorators import execute_periodically
from message.message import MessageSerializer
from chord.command_handler import CommandHandler


# TODO: sort methods to different classes

class TableNode:
    # Temp id for sockets
    _m = 160

    # List of sockets, ciphers and threads for receive
    _ids = []
    _peers = {}
    _ciphers = {}
    _threads = []
    _token_dict = {}
    _successor_query = {}
    _key_to_chat = {}

    def __init__(self):
        print(os.getpid())
        # Personal data
        self._id = None
        self.nickname = None
        self._invite = None

        # Crypto
        self.key = None

        # Chord
        self.predecessor = None
        self.successors = [None] * 2
        self._command_handler = CommandHandler(self)
        self._fingers = []
        self._finger_num = 0
        self._successor_num = 0
        self._fixing_fingers = False
        self._fixing_successors = False
        self._is_started = False

        # MessageContainer
        self._message_container = MessageContainer()

        # Starting listener
        self._socket_listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket_listener.bind(("localhost", 0))
        self._socket_listener.listen()
        print(f"Listening on 127.0.0.1:{self._socket_listener.getsockname()[1]}")
        self._mutex = threading.Lock()

        self._accept_thread = threading.Thread(target=self._accept_connection)
        self._accept_thread.start()

        # Message
        self.storage = {}
        self.count = {}

    @staticmethod
    def in_range(c: int, a: int, b: int):
        if a < b:
            return a < c <= b
        return a < c or c <= b

    def _start_threads(self):
        thread = threading.Thread(target=self.stabilize)
        thread.start()
        thread = threading.Thread(target=self.fix_fingers)
        thread.start()

    def create(self):
        nickname = input("Enter your nickname:\n")
        self.nickname = nickname
        self._id = int(sha1(nickname.encode()).hexdigest(), 16) % (2 ** self._m)

        self.successors[0] = self._id
        self.predecessor = None
        self._fingers = [None] * self._m

        self._start_threads()

    def join(self, node_id: int):
        invite = self.get_invite()
        key = os.urandom(32).hex()

        self._fingers = [None] * self._m
        self._successor_query[key] = -100
        self.send(node_id, f"{self._id} {self._id} {key} {invite}", CommandCodes.FIND_SUCCESSOR)

    def find_successor(self, x: int, sender: int, key: str, invite: str):
        with self._mutex:
            if self.successors[0] is None:
                return
            n = self._closest_preceding(x)
        if TableNode.in_range(x, self._id, self.successors[0]) or n == self._id:
            with self._mutex:
                successor_id = self.successors[0]

            self.send(successor_id, invite, CommandCodes.ESTABLISH_WITH)
            time.sleep(0.05)
            self.send(sender, f"{self.successors[0]} {key}", CommandCodes.RETURN_SUCCESSOR)
        else:
            with self._mutex:
                if key not in self._successor_query.keys():
                    self._successor_query[key] = sender
            self.send(n, f"{x} {self._id} {key} {invite}", CommandCodes.FIND_SUCCESSOR)

    def _closest_preceding(self, x: int) -> int:
        for finger in reversed(self._fingers):
            if finger and TableNode.in_range(finger, self._id, x):
                return finger
        return self._id

    def return_successor(self, successor: int, key: str):
        with self._mutex:
            sender = 0
            if key in self._successor_query.keys():
                sender = self._successor_query.pop(key)
            if -101 <= sender <= -100:
                self.successors[- sender - 100] = successor
                self._fixing_successors = False
                if not self._is_started:
                    self._is_started = True
                    self._start_threads()
                print(f"Successor {- sender - 100} received")
            elif sender == -200:
                self._fixing_fingers = False
                self._fingers[self._finger_num] = successor
                self._finger_num = (self._finger_num + 1) % self._m

        if sender > 0:
            self.send(sender, str(successor) + " " + key, CommandCodes.RETURN_SUCCESSOR)
        elif sender == -300:
            self.send(successor, f"{self._id} {self._key_to_chat.pop(key)}", CommandCodes.CHAT_REQUEST)

    def update_successors(self):
        with self._mutex:
            if None not in self.successors or self._fixing_successors:
                return
            if self.successors[0] is None:
                self.successors = [self._id] * len(self.successors)
                return
            first_none = next(i for i, v in enumerate(self.successors) if v is None)
            key = os.urandom(32).hex()
            self._successor_query[key] = -first_none - 100
            self._fixing_successors = True
        self.send(self.successors[first_none - 1],
                  f"{self.successors[first_none - 1]} {self._id} {key} {self._invite}",
                  CommandCodes.FIND_SUCCESSOR)

    def notify(self, node_id):
        with self._mutex:
            if self.predecessor is None or self.in_range(node_id, self.predecessor, self._id):
                self.predecessor = node_id

    @execute_periodically(0.5)
    def stabilize(self):
        with self._mutex:
            if self.successors[0] == self._id:
                if self.predecessor:
                    self.successors[0] = self.predecessor
        if not self._fixing_successors and self.successors[0] != self._id:
            invite = self.get_invite()
            if self.successors[self._successor_num] is not None:
                with self._mutex:
                    self._fixing_successors = True
                self.send(self.successors[self._successor_num],
                          f"{self._id} {invite}", CommandCodes.PREDECESSOR_REQUEST)
            else:
                self.update_successors()

    def continue_stabilizing(self, s_predecessor):
        with self._mutex:
            if self._successor_num == 0:
                send_id = self._id
            else:
                send_id = self.successors[self._successor_num - 1]

            if s_predecessor != send_id and s_predecessor is not None \
                    and (self.in_range(s_predecessor, send_id, self.successors[self._successor_num])
                         or self.predecessor == self.successors[0]):
                print(f"Successor {self._successor_num} received: stabilized")
                self.successors[self._successor_num] = s_predecessor
        self.send(self.successors[self._successor_num], str(send_id), CommandCodes.NOTIFY)
        with self._mutex:
            self._successor_num = (self._successor_num + 1) % len(self.successors)
            self._fixing_successors = False

    @execute_periodically(0.5)
    def fix_fingers(self):
        with self._mutex:
            boolean = self.successors[0] != self._id and not self._fixing_fingers
        if boolean:
            with self._mutex:
                self._fixing_fingers = True
                key = os.urandom(32).hex()
                self._successor_query[key] = -200
                finger = int(self._id + 2 ** self._finger_num)
            invite = self.get_invite()
            self.send(self.successors[0], f"{finger} {self._id} {key} {invite}",
                      CommandCodes.FIND_SUCCESSOR)
        if self._mutex.locked():
            self._mutex.release()

    def pass_message(self, x: int, message: str):
        with self._mutex:
            n = self._closest_preceding(x)
            successor_id = self.successors[0]
        if TableNode.in_range(x, self._id, successor_id) or n == self._id:
            self.send(successor_id, f"{x} {message}", CommandCodes.STORE_MESSAGE)
        else:
            self.send(successor_id, f"{x} {message}", CommandCodes.PASS_MESSAGE)

    def store_message(self, x: int, message: str):
        self._message_container.add_message(x, message)

    def get_chat(self, x: bytes):
        x = int(sha1(x).hexdigest(), 16) % (2 ** self._m)
        return self._message_container.get_messages(x)

    def reload_chat(self, x: bytes):
        x = int(sha1(x).hexdigest(), 16) % (2 ** self._m)
        key = os.urandom(32).hex()

        self._successor_query[key] = -300
        self._key_to_chat[key] = x
        if self._invite is None:
            self._invite = self.generate_invite()
        self.send(self.successors[0], f"{x} {self._id} {key} {self._invite}", CommandCodes.FIND_SUCCESSOR)

    def chat_request(self, node_id: int, key: int):
        self.send(node_id, f"{key} {pickle.dumps(self._message_container.get_messages(key)).hex()}",
                  CommandCodes.CHAT_RESPONSE)

    def chat_response(self, key: int, messages: bytes):
        messages = pickle.loads(messages)
        self._message_container.set_chat(key, messages)

    def _accept_connection(self):
        while True:
            connection = self._socket_listener.accept()
            key = connection[0].recv(32)
            if key in self._token_dict.keys():
                connection[0].send("CODE: 000".encode())
                self.log("Key accepted")
            else:
                connection[0].send("CODE: 001".encode())
                self.log("Invalid key {}".format(key))
                continue
            status = connection[0].recv(3)
            self.log(str(status.decode()))
            nickname = connection[0].recv(32)
            self.log(str(nickname.decode()))
            if status.decode() == "REG":
                # TODO: check if exists user with the same nickname
                connection[0].send("CODE: 100".encode())

            chat_token = self._generate_chat_token()
            connection[0].send(chat_token.encode())

            sid = int(sha1(nickname).hexdigest(), 16) % (2 ** self._m)

            with self._mutex:
                self._ids.append(sid)
                self._ciphers[sid] = ChatCipher(self._token_dict[key][0], self._token_dict[key][1], self.nickname)
                self._peers[sid] = connection
                thread = threading.Thread(target=self._receive,
                                          args=(sid, connection[0], self._ciphers[sid]))
                thread.start()
                self._threads.append(thread)

    def establish_connection(self, token: str) -> Tuple[bool, Any]:
        address, port, key, nickname = self._parse_invite_token(token)
        hashed_nickname = int(sha1(nickname.encode()).hexdigest(), 16) % (2 ** self._m)

        if key in self._token_dict.keys() or hashed_nickname in self._ids:
            self.log("Already connected")
            return False, hashed_nickname

        socket_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        socket_client.connect((address, port))

        self.log("Sending key - " + str(key))
        socket_client.send(key)
        return_code = socket_client.recv(9).decode()
        is_reg = False
        if return_code != "CODE: 000":
            print("ERROR: Connection is not established")
            return False, None

        if self.nickname is None:
            is_reg = True
            socket_client.send("REG".encode())
            return_code = ""
            while return_code != "CODE: 100":  # nickname accepted
                q = input("Your nickname:\n")
                socket_client.send(str(q).encode())
                return_code = socket_client.recv(9).decode()
            self.nickname = q
            self._id = int(sha1(q.encode()).hexdigest(), 16) % (2 ** self._m)
        else:
            socket_client.send("CON".encode())
            socket_client.send(str(self.nickname).encode())

        iv, message_token = self._parse_chat_token(socket_client.recv(96).decode())

        with self._mutex:
            self._ids.append(hashed_nickname)
            self._ciphers[hashed_nickname] = ChatCipher(message_token, iv, self.nickname)
            self._peers[hashed_nickname] = (socket_client, (address, port))
            thread = threading.Thread(target=self._receive,
                                      args=(hashed_nickname, socket_client, self._ciphers[hashed_nickname]))
            thread.start()
            self._threads.append(thread)

        if is_reg:
            self.join(hashed_nickname)
            print("Success! You connected to user {}".format(nickname))

        return True, None

    def send_chat_message(self, key: bytes, message: bytes):
        key = int(sha1(key).hexdigest(), 16) % (2 ** self._m)
        print("CHAT MESSAGE:")
        self.send(self._id, f"{key} {message.hex()}", CommandCodes.PASS_MESSAGE)

    def send(self, sid: int, message: str, code: CommandCodes = CommandCodes.TEXT_MESSAGE):
        self.send_bytes(sid, message.encode(), code)

    def send_bytes(self, sid: int, message: bytes, code: CommandCodes = CommandCodes.TEXT_MESSAGE):
        if sid == self._id:
            self._command_handler.handle_commands(code, (self.nickname, message, code, None))
            return

        with self._mutex:
            if sid not in self._ids:
                self._fixing_successors = False
                print("Lost smtng", sid)
                return

            sock = self._peers[sid][0]
            cipher = self._ciphers[sid]

        data = cipher.serialize(bytes(message), code)
        arr = len(data).to_bytes(4, "little") + data
        try:
            sock.sendall(arr)
        except BrokenPipeError:
            print(f"Data, that been sending to {sid} was lost")

    def send_all(self, message: list):
        for i in self.get_connections():
            for j in message:
                self.send_bytes(i, j)

    def receive_message(self, data):
        who = data[0]
        what = data[1]
        parser = MessageSerializer()
        ans = parser.deserialize_message(what)
        if ans[0] == "text":
            print(who + ":", ans[1])
        elif ans[0] == "video":
            print(who + " sends you a video message")
        elif ans[0] == "picture":
            print(who + " sends you an image")

    def _receive(self, sid: int, sock: socket.socket, cipher: ChatCipher):
        while True:
            try:
                buf = sock.recv(4)
                if buf == b"":
                    self._delete_user(sid)
                    sys.exit(0)

                leni = int.from_bytes(buf, "little")
                true_msg = b""
                while leni != 0:
                    read_sz = min(leni, 4096)
                    buf = sock.recv(read_sz)
                    if buf == b"":
                        self._delete_user(sid)
                        sys.exit(0)
                    true_msg += buf
                    leni -= len(buf)
                data = cipher.deserialize(true_msg)
                code = data[2]
                self.log(str(data))
                self._command_handler.handle_commands(code, data)
            except ConnectionResetError:
                self._delete_user(sid)
                sys.exit(0)

    def generate_invite(self):
        invite = ""
        ip_list = self._socket_listener.getsockname()[0].split('.')
        for i in ip_list:
            invite += format(int(i), '02x')
        invite += format(self._socket_listener.getsockname()[1], '04x')

        # TODO: Check if token is already taken in global network

        with self._mutex:
            key = os.urandom(32)
            while key in self._token_dict.keys():
                key = os.urandom(32)

            self.key = key
            self._token_dict[key] = (None, None)
            self.log("Generated key - " + str(key))
            invite += key.hex()
            invite += self.nickname
            self._invite = invite
        return invite

    def _generate_chat_token(self):
        with self._mutex:
            iv = os.urandom(16)
            token = os.urandom(32)
            while len([item for item in self._token_dict.values() if token == item[0]]) != 0:
                token = os.urandom(32)

            self._token_dict[self.key] = (token, iv)

        return iv.hex() + token.hex()

    @staticmethod
    def _parse_invite_token(token: str):
        ip = token[:8]
        port = int(token[8:12], 16)
        key = bytes.fromhex(token[12:76])
        nickname = token[76:]

        parsed_ip = str(int(token[0:2], 16)) + "." + str(int(token[2:4], 16)) + \
                    "." + str(int(token[4:6], 16)) + "." + str(int(token[6:8], 16))
        return parsed_ip, port, key, nickname

    @staticmethod
    def _parse_chat_token(token):
        iv = bytes.fromhex(token[:32])
        message_token = bytes.fromhex(token[32:])

        return iv, message_token

    def _delete_user(self, sid: int):
        with self._mutex:
            index = self._ids.index(sid)

            self._ids.pop(index)
            del self._peers[sid]
            self._threads.pop(index)
            del self._ciphers[sid]
            if self.predecessor not in self._ids:
                self.predecessor = None

            is_needed_to_fix = False
            for i in self.successors:
                if i not in self._ids:
                    is_needed_to_fix = True
                    break
            if is_needed_to_fix:
                correct_id = None
                for i in self.successors:
                    if i in self._ids:
                        correct_id = i
                        break
                self.successors = [None] * len(self.successors)
                self.successors[0] = correct_id
                print("Successor missing. Rebuilding list")
            self._finger_num = 0
            self._fingers = [None] * self._m
            self._fixing_successors = False
            self._fixing_fingers = False
        self.update_successors()

    def log(self, msg):
        with open("./log.txt", "a") as log_file:
            log_file.write("{}:{} - ".format(self.nickname, self._id) + msg + '\n')

    def print_info(self):
        print("Id: ", self._id)
        print("Successor: ", self.successors)
        print("Predecessor", self.predecessor)
        print("Connections", self._peers.keys())

    def get_connections(self):
        ans = self._peers.keys()
        return ans

    def get_invite(self):
        if self._invite:
            invite = self._invite
        else:
            invite = self.generate_invite()
        return invite
