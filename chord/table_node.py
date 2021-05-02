import os
import socket
import sys
import threading
from typing import Any, Tuple

from security.chat_cipher import ChatCipher
from hashlib import sha1
from chord.command_codes import CommandCodes
from chord.decorators import execute_periodically
from message.message import MessageSerializer
from chord.command_handler import CommandHandler


class TableNode:
    # Temp id for sockets
    _m = 2 ** 160
    # List of sockets, ciphers and threads for receive
    _ids = []
    _peers = {}
    _ciphers = {}
    _threads = []
    _token_dict = {}

    def __init__(self):
        print(os.getpid())
        # Personal data
        self._id = None
        self._nickname = None
        self._invite = None

        # Crypto
        self.key = None

        # Chord data
        self.finger_table = []
        self.finger_num = 0
        self.successors = []
        self.successor = None
        self.predecessor = None
        self.stabilization_thread = None
        self.finger_thread = None
        self.predecessor_thread = None  # TODO: check if predecessor (or another node) is dead
        self.fixing_fingers = False
        self.command_handler = CommandHandler(self)

        # Starting listener
        self._socket_listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket_listener.bind(("localhost", 0))
        self._socket_listener.listen()
        print(f"Listening on 127.0.0.1:{self._socket_listener.getsockname()[1]}")
        self._mutex = threading.Lock()

        self._accept_thread = threading.Thread(target=self._accept_connection)
        self._accept_thread.start()
        # message
        self.storage = {}
        self.count = {}

    def inrange(self, c, a, b):
        a = a % self._m
        b = b % self._m
        c = c % self._m
        if a < b:
            return a < c < b
        return a < c or c < b

    def create(self):
        self.predecessor = None
        nickname = input("Your nickname:\n")
        self._nickname = nickname
        self._id = int(sha1(nickname.encode()).hexdigest(), 16) % 2 ** self._m
        self.successor = self._id
        thread = threading.Thread(target=self.stabilize)
        thread.start()
        thread = threading.Thread(target=self.fix_fingers)
        thread.start()

    def join(self, node_id: int):
        self.predecessor = None
        if self._invite:
            invite = self._invite
        else:
            invite = self.generate_invite()
        self.send(node_id, str(node_id) + " " + invite, CommandCodes.FIND_SUCCESSOR)

    def closest_preceding_node(self, node_id: int):
        for finger in reversed(self.finger_table):
            if self.inrange(finger, self._id, node_id):
                return finger
        return self._id

    def find_successor(self, node_id: int, sender_invite: str):
        self._mutex.acquire()
        if self._id == self.successor and node_id == self.successor:  # first connection to the ring
            self.predecessor = self._ids[0]
            self._mutex.release()
            self.send(self._ids[0], str(self._id), CommandCodes.SUCCESSOR_RESPONSE)
        elif self.inrange(node_id, self._id, self.successor):
            self._mutex.release()
            self.send(self.successor, sender_invite, CommandCodes.RETURN_SUCCESSOR)
        else:
            self._mutex.release()
            next_node = self.closest_preceding_node(node_id)
            if next_node != self._id:
                self.send(next_node, str(node_id) + " " + sender_invite, CommandCodes.FIND_SUCCESSOR)
            else:
                is_connected, node = self.establish_connection(sender_invite)
                if is_connected:
                    self.send(self._ids[-1], str(self._id), CommandCodes.SUCCESSOR_RESPONSE)
                else:
                    self.send(node, str(self._id), CommandCodes.SUCCESSOR_RESPONSE)

    def notify(self, node_id):
        self._mutex.acquire()
        if self.predecessor is None or self.inrange(node_id, self.predecessor, self._id):
            self.predecessor = node_id
        self._mutex.release()

    @execute_periodically(3)
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
            self.send(self.successor, str(self._id) + " " + invite, CommandCodes.PREDECESSOR_REQUEST)

    def continue_stabilizing(self, s_predecessor):
        if s_predecessor and (self.inrange(s_predecessor, self._id, self.successor) or
                              self.predecessor == self.successor):
            self._mutex.acquire()
            self.successor = s_predecessor
            self._mutex.release()
        self.send(self.successor, str(self._id), CommandCodes.NOTIFY)

    @execute_periodically(5)
    def fix_fingers(self):
        self._mutex.acquire()
        if self.successor != self._id:
            self.fixing_fingers = True
            self._mutex.release()
            if self._invite:
                invite = self._invite
            else:
                invite = self.generate_invite()
            self.send(self.successor, str(int(self._id + 2 ** (self.finger_num - 1))) + " " + invite,
                      CommandCodes.FIND_SUCCESSOR)
        if self._mutex.locked():
            self._mutex.release()

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

            sid = int(sha1(nickname).hexdigest(), 16) % 2 ** self._m

            self._mutex.acquire()
            self._ids.append(sid)
            self._ciphers[sid] = ChatCipher(self._token_dict[key][0], self._token_dict[key][1], self._nickname)
            self._peers[sid] = connection
            thread = threading.Thread(target=self._receive,
                                      args=(sid, connection[0], self._ciphers[sid]))
            thread.start()
            self._threads.append(thread)
            self._mutex.release()

    def establish_connection(self, token: str) -> Tuple[bool, Any]:
        address, port, key, nickname = self._parse_invite_token(token)
        hashed_nickname = int(sha1(nickname.encode()).hexdigest(), 16) % 2 ** self._m
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
        else:
            if self._nickname is None:
                is_reg = True
                socket_client.send("REG".encode())
                return_code = ""
                while return_code != "CODE: 100":  # nickname accepted
                    q = input("Your nickname:\n")
                    socket_client.send(str(q).encode())
                    return_code = socket_client.recv(9).decode()
                self._nickname = q
                self._id = int(sha1(q.encode()).hexdigest(), 16) % 2 ** self._m
            else:
                socket_client.send("CON".encode())
                socket_client.send(str(self._nickname).encode())
            iv, message_token = self._parse_chat_token(socket_client.recv(96).decode())

        self._mutex.acquire()
        self._ids.append(hashed_nickname)
        self._ciphers[hashed_nickname] = ChatCipher(message_token, iv, self._nickname)
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

    def send(self, sid: int, message: str, code: int = CommandCodes.TEXT_MESSAGE):
        self.send_bytes(sid, message.encode(), code)

    def send_bytes(self, sid: int, message: bytes, code: int = CommandCodes.TEXT_MESSAGE):
        if sid == self._id:
            self.log("sending to itself")
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
            print(ans[1])

    def _receive(self, sid: int, sock: socket.socket, cipher: ChatCipher):
        while True:
            msg = bytearray()
            buf = sock.recv(4)
            if buf == b"":
                self._delete_user(sid)
                sys.exit(0)
            true_msg = bytearray()
            leni = int.from_bytes(buf[:4], "little")
            while len(true_msg) != leni:
                buf = sock.recv(leni - len(msg))
                true_msg += buf
            msg = true_msg
            data = cipher.deserialize(msg)
            code = data[2]

            self.command_handler.handle_commands(code, data)

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
        invite += self._nickname
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
            log_file.write("{}:{} - ".format(self._nickname, self._id) + msg + '\n')

    def print_info(self):
        print("Id: ", self._id)
        print("Successor: ", self.successor)
        print("Predecessor", self.predecessor)
        print("Connections", self._peers.keys())

    def get_connections(self):
        ans = self._peers.keys()
        return ans
