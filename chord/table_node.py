import os
import socket
import sys
import threading
from typing import Any, Tuple

from chord.message_container import MessageContainer
from security.chat_cipher import ChatCipher
from hashlib import sha1
from chord.command_codes import CommandCodes
from chord.decorators import execute_periodically
from message.message import MessageSerializer
from chord.command_handler import CommandHandler


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
        self.successor = None
        self._command_handler = CommandHandler(self)
        self._fingers = []
        self._finger_num = 0
        self._fixing_fingers = False

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

        self.successor = self._id
        self.predecessor = None
        self._fingers = [self._id] * self._m

        self._start_threads()

    def join(self, node_id: int):
        if self._invite:
            invite = self._invite
        else:
            invite = self.generate_invite()
        key = os.urandom(32).hex()

        self._fingers = [self._id] * self._m
        self._successor_query[key] = -1
        self.send(node_id, str(self._id) + " " + str(self._id) + " " +
                  key + " " + invite, CommandCodes.FIND_SUCCESSOR)

    def find_successor(self, x: int, sender: int, key: str, invite: str):
        self._mutex.acquire()
        # self.log(f"{x}, {sender}, {self._id}, {self.successor}")
        if TableNode.in_range(x, self._id, self.successor):
            node_id = self._id
            successor_id = self.successor
            self._mutex.release()

            if node_id == successor_id:
                self.establish_connection(invite)
            else:
                self.send(successor_id, invite, CommandCodes.ESTABLISH_WITH)
            self.send(sender, str(self.successor) + " " + key, CommandCodes.RETURN_SUCCESSOR)
        else:
            n = self._closest_preceding(x)
            if n == self._id:
                self._mutex.release()
                self.establish_connection(invite)
                self.send(self.successor, invite, CommandCodes.ESTABLISH_WITH)
                self.send(sender, str(self.successor) + " " + key, CommandCodes.RETURN_SUCCESSOR)
            else:
                self._successor_query[key] = sender
                self._mutex.release()
                self.send(n, str(x) + " " + str(self._id) + " " + key + " " + invite,
                          CommandCodes.FIND_SUCCESSOR)

    def _closest_preceding(self, x: int) -> int:
        for finger in reversed(self._fingers):
            if finger and TableNode.in_range(finger, self._id, x):
                return finger
        return self._id

    def return_successor(self, successor: int, key: str):
        self._mutex.acquire()
        sender = self._successor_query.pop(key)
        if sender > 0:
            self._mutex.release()
            self.send(sender, str(successor) + " " + key, CommandCodes.RETURN_SUCCESSOR)
        elif sender == -1:
            self.successor = successor
            self._start_threads()
            print("Successor received")
            self._mutex.release()
        elif sender == -2:
            self._fingers[self._finger_num] = successor
            self._finger_num = (self._finger_num + 1) % self._m
            self._mutex.release()

    def notify(self, node_id):
        self._mutex.acquire()
        if self.predecessor is None or self.in_range(node_id, self.predecessor, self._id):
            self.predecessor = node_id
        self._mutex.release()

    @execute_periodically(1)
    def stabilize(self):
        self._mutex.acquire()
        if self.successor == self._id:
            if self.predecessor:
                self.successor = self.predecessor
            self._mutex.release()
        else:
            self._mutex.release()
            if self._invite:
                invite = self._invite
            else:
                invite = self.generate_invite()

            self.send(self.successor, f"{self._id} {invite}", CommandCodes.PREDECESSOR_REQUEST)

    def continue_stabilizing(self, s_predecessor):
        if s_predecessor != self._id and \
                s_predecessor and (self.in_range(s_predecessor, self._id, self.successor)
                                   or self.predecessor == self.successor):
            self._mutex.acquire()
            self.successor = s_predecessor
            self._mutex.release()
        self.send(self.successor, str(self._id), CommandCodes.NOTIFY)

    @execute_periodically(1)
    def fix_fingers(self):
        self._mutex.acquire()
        if self.successor != self._id:
            self._fixing_fingers = True
            self._mutex.release()
            if self._invite:
                invite = self._invite
            else:
                invite = self.generate_invite()
            key = os.urandom(32).hex()
            self._successor_query[key] = -2
            finger = int(self._id + 2 ** (self._finger_num - 1))
            self.send(self.successor, f"{finger} {self._id} {key} {invite}",
                      CommandCodes.FIND_SUCCESSOR)
        if self._mutex.locked():
            self._mutex.release()

    def pass_message(self, x: int, message: bytes):
        self._mutex.acquire()
        if TableNode.in_range(x, self._id, self.successor):
            successor_id = self.successor
            print("Pass 1")
            self._mutex.release()
            self.send(successor_id, f"{x} {message}", CommandCodes.STORE_MESSAGE)
        else:
            n = self._closest_preceding(x)
            print("Pass 2")
            if n == self._id:
                self._mutex.release()
                self.send(self.successor, f"{x} {message}", CommandCodes.STORE_MESSAGE)
            else:
                self._mutex.release()
                self.send(self.successor, f"{x} {message}", CommandCodes.PASS_MESSAGE)

    def store_message(self, x: int, message: bytes):
        self._message_container.add_message(x, message)

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

            self._mutex.acquire()
            self._ids.append(sid)
            self._ciphers[sid] = ChatCipher(self._token_dict[key][0], self._token_dict[key][1], self.nickname)
            self._peers[sid] = connection
            thread = threading.Thread(target=self._receive,
                                      args=(sid, connection[0], self._ciphers[sid]))
            thread.start()
            self._threads.append(thread)
            self._mutex.release()

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

        self._mutex.acquire()
        self._ids.append(hashed_nickname)
        self._ciphers[hashed_nickname] = ChatCipher(message_token, iv, self.nickname)
        self._peers[hashed_nickname] = (socket_client, (address, port))
        thread = threading.Thread(target=self._receive,
                                  args=(hashed_nickname, socket_client, self._ciphers[hashed_nickname]))
        thread.start()
        self._threads.append(thread)

        self._mutex.release()

        if is_reg:
            self.join(hashed_nickname)
            print("Success! You connected to user {}".format(nickname))

        return True, None

    def send_chat_message(self, key: bytes, message: bytes):
        key = int(sha1(key).hexdigest(), 16) % (2 ** self._m)
        print(f"CHAT MESSAGE: {key} {message}")
        self.send(self._id, f"{key} {message}", CommandCodes.PASS_MESSAGE)

    def send(self, sid: int, message: str, code: CommandCodes = CommandCodes.TEXT_MESSAGE):
        self.send_bytes(sid, message.encode(), code)

    def send_bytes(self, sid: int, message: bytes, code: CommandCodes = CommandCodes.TEXT_MESSAGE):
        if sid == self._id:
            self._command_handler.handle_commands(code, (self.nickname, message, code, None))
            return

        self._mutex.acquire()
        sock = self._peers[sid][0]
        cipher = self._ciphers[sid]
        self._mutex.release()

        data = cipher.serialize(bytes(message), code)
        arr = len(data).to_bytes(4, "little") + data
        sock.send(arr)

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
            buf = sock.recv(4)
            if buf == b"":
                self._delete_user(sid)
                sys.exit(0)

            leni = int.from_bytes(buf, "little")
            true_msg = b""
            while leni != 0:
                read_sz = min(leni, 4096)
                true_msg += sock.recv(read_sz)
                leni -= read_sz
            data = cipher.deserialize(true_msg)
            code = data[2]
            self.log(str(data))
            self._command_handler.handle_commands(code, data)

    def generate_invite(self):
        invite = ""
        ip_list = self._socket_listener.getsockname()[0].split('.')
        for i in ip_list:
            invite += format(int(i), '02x')
        invite += format(self._socket_listener.getsockname()[1], '04x')

        # TODO: Check if token is already taken in global network

        self._mutex.acquire()

        key = os.urandom(32)
        while key in self._token_dict.keys():
            key = os.urandom(32)

        self.key = key
        self._token_dict[key] = (None, None)
        self.log("Generated key - " + str(key))
        self._mutex.release()
        invite += key.hex()
        invite += self.nickname
        self._invite = invite
        return invite

    def _generate_chat_token(self):
        self._mutex.acquire()
        iv = os.urandom(16)
        token = os.urandom(32)
        while len([item for item in self._token_dict.values() if token == item[0]]) != 0:
            token = os.urandom(32)

        self._token_dict[self.key] = (token, iv)
        self._mutex.release()

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
        self._mutex.acquire()
        index = self._ids.index(sid)

        self._ids.pop(index)
        del self._peers[sid]
        self._threads.pop(index)
        del self._ciphers[sid]
        self._mutex.release()

    def log(self, msg):
        with open("./log.txt", "a") as log_file:
            log_file.write("{}:{} - ".format(self.nickname, self._id) + msg + '\n')

    def print_info(self):
        print("Id: ", self._id)
        print("Successor: ", self.successor)
        print("Predecessor", self.predecessor)
        print("Connections", self._peers.keys())

    def get_connections(self):
        ans = self._peers.keys()
        return ans
