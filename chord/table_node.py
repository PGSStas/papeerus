import os
import pickle
import socket
import threading
import time
from typing import Any, Tuple

from chord.message_container import MessageContainer
from security.chat_cipher import ChatCipher
from hashlib import sha1
from chord.command_codes import CommandCodes
from chord.decorators import execute_periodically
from chord.command_handler import CommandHandler


# TODO: sort methods to different classes

class TableNode:
    # Temp id for sockets
    _m = 160

    # List of sockets, ciphers and threads for receive
    _ids = []
    _peers = {}
    _ciphers = {}
    _token_dict = {}
    _successor_query = {}
    _key_to_chat = {}
    local_chats = {}

    RECEIVE_TIMEOUT = 0.2
    REQUEST_TIMEOUT = 20
    SUCCESSOR_COUNT = 3

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
        self.successors = [None] * self.SUCCESSOR_COUNT
        self._command_handler = CommandHandler(self)
        self._fingers = []
        self._finger_num = 0
        self._successor_num = 0
        self._fixing_fingers = False, -1
        self._fixing_successors = False, -1
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
        self._accept_thread.daemon = True
        self._accept_thread.start()
        self._receive_thread = threading.Thread(target=self._receive)
        self._receive_thread.daemon = True
        self._receive_thread.start()
        self._balance_thread = None

    @staticmethod
    def in_range(c: int, a: int, b: int):
        if a < b:
            return a < c <= b
        return a < c or c <= b

    def _start_threads(self):
        self._balance_thread = threading.Thread(target=self.fix_dht_structure)
        self._balance_thread.daemon = True
        self._balance_thread.start()

    def create(self, nickname: str):
        self.nickname = nickname
        self._id = self.bytes_to_hash(nickname.encode())

        self.successors = [self._id] * len(self.successors)
        self.predecessor = None
        self._fingers = [self._id] * self._m

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
            if -99 - self.SUCCESSOR_COUNT <= sender <= -100:
                self.successors[- sender - 100] = successor
                self._fixing_successors = False, -1
                if not self._is_started:
                    self._is_started = True
                    self._start_threads()
                print(f"Successor {- sender - 100} received")
            elif sender == -200:
                self._fixing_fingers = False, -1
                self._fingers[self._finger_num] = successor
                self._finger_num = (self._finger_num + 1) % self._m

        if sender > 0:
            self.send(sender, str(successor) + " " + key, CommandCodes.RETURN_SUCCESSOR)
        elif sender == -300:
            self.send(successor, f"{self._id} {self._key_to_chat.pop(key)}", CommandCodes.CHAT_REQUEST)

    def update_successors(self):
        with self._mutex:
            self.find_and_delete_missing()
            if None not in self.successors or self._fixing_successors[0]:
                return
            if self.successors[0] is None:
                self.successors = [self._id] * len(self.successors)
                return
            first_none = next(i for i, v in enumerate(self.successors) if v is None)
            key = os.urandom(32).hex()
            self._successor_query[key] = -first_none - 100
            self._fixing_successors = True, self.successors[first_none - 1]
        if self._fixing_successors[0]:
            self.send(self.successors[first_none - 1],
                      f"{self.successors[first_none - 1]} {self._id} {key} {self._invite}",
                      CommandCodes.FIND_SUCCESSOR)

    @execute_periodically(0.5)
    def fix_dht_structure(self):
        with self._mutex:
            self.find_and_delete_missing()
        self.fix_fingers()
        self.stabilize()

    def notify(self, node_id):
        with self._mutex:
            if self.predecessor is None or self.in_range(node_id, self.predecessor, self._id):
                self.predecessor = node_id

    def stabilize(self):
        with self._mutex:
            if self.successors[0] == self._id:
                if self.predecessor:
                    self.successors[0] = self.predecessor
        if not self._fixing_successors[0] and self.successors[0] != self._id:
            invite = self.get_invite()
            with self._mutex:
                self.find_and_delete_missing()
            if self.successors[self._successor_num] is not None:
                with self._mutex:
                    self._fixing_successors = True, self.successors[self._successor_num]
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
            is_stabilized = False
            if s_predecessor != send_id and s_predecessor is not None and \
                    self.successors[self._successor_num] is not None \
                    and (self.in_range(s_predecessor, send_id, self.successors[self._successor_num])
                         or self.predecessor == self.successors[0]):
                print(f"Successor {self._successor_num} received: stabilized")
                self.successors = self.successors[:self._successor_num] + [s_predecessor] + self.successors[
                                                                                            self._successor_num + 1:]
                is_stabilized = True
        self.send(self.successors[self._successor_num], str(send_id), CommandCodes.NOTIFY)
        with self._mutex:
            self._successor_num = (self._successor_num + 1) % len(self.successors)
            if is_stabilized:
                self._successor_num = 0
            self._fixing_successors = False, -1

    def fix_fingers(self):
        with self._mutex:
            boolean = self.successors[0] != self._id and not self._fixing_fingers[0]
            self.find_and_delete_missing()
        if boolean:
            with self._mutex:
                self._fixing_fingers = True, self.successors[0]
                key = os.urandom(32).hex()
                self._successor_query[key] = -200
                finger = int(self._id + 2 ** self._finger_num) % (2 ** self._m)
            invite = self.get_invite()
            self.send(self.successors[0], f"{finger} {self._id} {key} {invite}",
                      CommandCodes.FIND_SUCCESSOR)

    def distribute_chats(self):
        if self.predecessor is not None:
            with self._mutex:
                m1, _ = self._message_container.split_by(self.predecessor)
            self.send_bytes(self.predecessor, pickle.dumps(m1), CommandCodes.RECEIVE_CHAT_COPY)
        if self.successors[0] is not None:
            with self._mutex:
                full_chat = self._message_container.get_chat()
            self.send_bytes(self.successors[0], pickle.dumps(full_chat), CommandCodes.RECEIVE_CHAT_COPY)

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
        x = self.bytes_to_hash(x)
        return self._message_container.get_messages(x)

    def reload_chat(self, x: bytes):
        x = self.bytes_to_hash(x)
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
        self.local_chats[key] = messages

    def receive_chat_copy(self, messages: bytes):
        messages = pickle.loads(messages)
        self._message_container.merge_chats(messages)

    def _accept_connection(self):
        while True:
            connection = self._socket_listener.accept()
            key = connection[0].recv(32)
            print("KEY:", key, self._token_dict.keys())
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

            sid = self.bytes_to_hash(nickname)

            with self._mutex:
                print("TUP")
                self._ids.append(sid)
                self._ciphers[sid] = ChatCipher(self._token_dict[key][0], self._token_dict[key][1], self.nickname)
                self._peers[sid] = connection

    def establish_connection(self, token: str, our_nickname: str = "") -> Tuple[bool, Any]:
        address, port, key, nickname = self._parse_invite_token(token)
        hashed_nickname = self.bytes_to_hash(nickname.encode())

        if key in self._token_dict.keys() or hashed_nickname in self._ids:
            self.log("Already connected")
            return False, hashed_nickname

        socket_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            socket_client.connect((address, port))
        except ConnectionRefusedError:
            print(f"Failed to connect {nickname}")
            return False, None

        self.log("Sending key - " + str(key))
        try:
            socket_client.send(key)
        except BrokenPipeError:
            print(f"Failed to connect {nickname}")
            return False, None
        return_code = socket_client.recv(9).decode()
        is_reg = False
        print(return_code)
        if return_code != "CODE: 000":
            print("ERROR: Connection is not established")
            return False, None

        try:
            if self.nickname is None:
                is_reg = True
                socket_client.send("REG".encode())
                print("GG")
                socket_client.send(str(our_nickname).encode())
                return_code = socket_client.recv(9).decode()
                if return_code != "CODE: 100":
                    return False, None
                self.nickname = our_nickname
                self._id = self.bytes_to_hash(our_nickname.encode())
            else:
                socket_client.send("CON".encode())
                socket_client.send(str(self.nickname).encode())
        except BrokenPipeError:
            print(f"Failed to connect {nickname}")
            return False, None

        iv, message_token = self._parse_chat_token(socket_client.recv(96).decode())

        with self._mutex:
            self._ids.append(hashed_nickname)
            self._ciphers[hashed_nickname] = ChatCipher(message_token, iv, self.nickname)
            self._peers[hashed_nickname] = (socket_client, (address, port))

        if is_reg:
            self.join(hashed_nickname)
            print("Success! You connected to user {}".format(nickname))

        return True, None

    def send_chat_message(self, key: bytes, message: bytes):
        key = self.bytes_to_hash(key)
        self.send(self._id, f"{key} {message.hex()}", CommandCodes.PASS_MESSAGE)

    def send(self, sid: int, message: str, code: CommandCodes = CommandCodes.TEXT_MESSAGE):
        self.send_bytes(sid, message.encode(), code)

    def send_bytes(self, sid: int, message: bytes, code: CommandCodes = CommandCodes.TEXT_MESSAGE):
        if sid == self._id:
            self._command_handler.handle_commands(code, (self.nickname, message, code, None))
            return

        with self._mutex:
            if sid not in self._ids:
                self._fixing_successors = False, -1
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
        print(data)

    def _receive(self):
        while True:
            with self._mutex:
                ids = self._ids.copy()

            for i in range(len(ids)):
                try:
                    with self._mutex:
                        if ids[i] not in self._ids:
                            continue
                        sid = ids[i]
                        sock = self._peers[sid][0]
                        cipher = self._ciphers[sid]
                    sock.settimeout(self.RECEIVE_TIMEOUT)
                    buf = sock.recv(4)
                    if buf == b"":
                        sock.settimeout(0)
                        self._delete_user(sid)
                        continue

                    leni = int.from_bytes(buf, "little")
                    true_msg = b""
                    while leni != 0:
                        read_sz = min(leni, 4096)
                        buf = sock.recv(read_sz)
                        if buf == b"":
                            self._delete_user(sid)
                            break
                        true_msg += buf
                        leni -= len(buf)
                    if leni != 0:
                        sock.settimeout(0)
                        continue
                    data = cipher.deserialize(true_msg)
                    code = data[2]
                    self.log(str(data))
                    self._command_handler.handle_commands(code, data)
                except ConnectionResetError:
                    self._delete_user(sid)
                    continue
                except socket.timeout:
                    continue

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
        print(self._token_dict)
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

        parsed_ip = str(int(token[0:2], 16)) + "." + str(int(token[2:4], 16)) + "." + \
                    str(int(token[4:6], 16)) + "." + str(int(token[6:8], 16))
        return parsed_ip, port, key, nickname

    @staticmethod
    def _parse_chat_token(token):
        iv = bytes.fromhex(token[:32])
        message_token = bytes.fromhex(token[32:])

        return iv, message_token

    def find_and_delete_missing(self):
        if self._fixing_successors[0] and (self._fixing_successors[1] not in self._ids \
                or self._fixing_successors[1] == -1):
            self._fixing_successors = False, -1
        if self._fixing_fingers[0] and (self._fixing_fingers[1] not in self._ids or self._fixing_fingers[1] == -1):
            self._fixing_fingers = False, -1

        if self.predecessor not in self._ids:
            self.predecessor = None

        is_needed_to_fix = False
        for i in range(len(self.successors)):
            if not is_needed_to_fix and self.successors[i] is not None \
                    and self.successors[i] not in self._ids and self.successors[i] != self._id:
                is_needed_to_fix = True
                self._successor_num = i
                self._fixing_successors = False, -1
            if is_needed_to_fix:
                self.successors[i] = None
        if is_needed_to_fix:
            print("Successor missing. Rebuilding list")
            print(self.successors, self._id, self._ids)

        is_needed_to_fix = False
        for i in range(len(self._fingers)):
            if not is_needed_to_fix and self._fingers[i] is not None \
                    and self._fingers[i] not in self._ids and self._fingers[i] != self._id:
                is_needed_to_fix = True
                break
        if is_needed_to_fix:
            self._fingers = [None] * self._m
            print("Finger missing. Rebuilding list")

    def _delete_user(self, sid: int):
        with self._mutex:
            if sid not in self._ids:
                return
            index = self._ids.index(sid)

            self._ids.pop(index)
            del self._peers[sid]
            del self._ciphers[sid]

            self.find_and_delete_missing()
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

    @staticmethod
    def bytes_to_hash(x: bytes):
        return int(sha1(x).hexdigest(), 16) % (2 ** 160)
