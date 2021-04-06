import os
import socket
import sys
import threading

from security.chat_cipher import ChatCipher
from hashlib import sha1
from chord.command_codes import CommandCodes


class TableNode:
    # Temp id for sockets
    _m = 160
    # List of sockets, ciphers and threads for receive
    _ids = []
    _peers = []
    _ciphers = []
    _threads = []
    _token_dict = {}

    def __init__(self):
        # Personal data
        self._id = None
        self._nickname = None
        # Crypto
        self.key = None
        # Chord data
        self.finger_table = []
        self.successors = []
        self.successor = None
        self.predecessor = None
        # Starting listener
        self._socket_listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket_listener.bind(("localhost", 0))
        self._socket_listener.listen()
        print(f"Listening on 127.0.0.1:{self._socket_listener.getsockname()[1]}")
        self._mutex = threading.Lock()

        self._accept_thread = threading.Thread(target=self._accept_connection)
        self._accept_thread.start()

    def create(self):
        self.predecessor = None
        self.successor = self._id
        nickname = input("Your nickname:\n")
        self._nickname = nickname
        self._id = int(sha1(nickname.encode()).hexdigest(), 16) % 2**self._m

    def join(self, node_id: int):
        self.predecessor = None
        invite = self.generate_invite()
        self.send(node_id, str(node_id) + " " + invite, CommandCodes.FIND_SUCCESSOR)

    def closest_preceding_node(self, node_id: int):
        for i in reversed(self.finger_table):
            if self._id < self.finger_table[i] < node_id:
                return self.finger_table[i]
        return self._id

    def find_successor(self, node_id: int, sender_invite: str):
        if self._id < node_id <= self.successor:
            self.send(self.successor, sender_invite, CommandCodes.RETURN_SUCCESSOR)
        else:
            next_node = self.closest_preceding_node(node_id)
            self.send(next_node, str(node_id) + " " + sender_invite, CommandCodes.FIND_SUCCESSOR)

    def stabilize(self):
        ...
        # TODO: page 6, fig. 6 in. Has to start periodically

    def fix_fingers(self):
        ...
        # TODO: page 6, fig. 6 in. Has to start periodically

    def _accept_connection(self):
        while True:
            connection = self._socket_listener.accept()
            key = connection[0].recv(32)
            if key in self._token_dict.keys():
                connection[0].send("CODE: 000".encode())
            else:
                connection[0].send("CODE: 001".encode())
                continue
            status = connection[0].recv(3)
            nickname = connection[0].recv(32)
            if status.decode() == "REG":
                # TODO: check if exists user with the same nickname
                connection[0].send("CODE: 100".encode())

            chat_token = self._generate_chat_token()
            connection[0].send(chat_token.encode())

            sid = int(sha1(nickname).hexdigest(), 16) % 2 ** self._m

            self._mutex.acquire()
            self._ids.append(sid)
            self._ciphers.append(ChatCipher(self._token_dict[key][0], self._token_dict[key][1], self._nickname))
            self._peers.append(connection)
            thread = threading.Thread(target=self._receive,
                                      args=(sid, connection[0], self._ciphers[-1]))
            thread.start()
            self._threads.append(thread)
            self._mutex.release()

    def establish_connection(self, token: str):
        address, port, key, nickname = self._parse_invite_token(token)
        if key in self._token_dict.keys():
            print("Already connected")
            return

        socket_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        socket_client.connect((address, port))

        socket_client.send(key)
        return_code = socket_client.recv(9).decode()
        if return_code != "CODE: 000":
            print("ERROR: Connection is not established")
            return
        else:
            if self._nickname is None:
                socket_client.send("REG".encode())
                return_code = ""
                while return_code != "CODE: 100":  # nickname accepted
                    q = input("Your nickname:\n")
                    socket_client.send(str(q).encode())
                    return_code = socket_client.recv(9).decode()
                print("Success! You connected to user {}".format(nickname))
                self._nickname = q
                self._id = int(sha1(q.encode()).hexdigest(), 16) % 2 ** self._m
                self.join(self._id)
            else:
                socket_client.send("CON".encode())
                socket_client.send(str(self._id).encode())
            iv, message_token = self._parse_chat_token(socket_client.recv(64).decode())

        self._mutex.acquire()
        hashed_nickname = int(sha1(nickname.encode()).hexdigest(), 16) % 2 ** self._m
        self._ids.append(hashed_nickname)
        self._ciphers.append(ChatCipher(message_token, iv, self._nickname))
        self._peers.append((socket_client, (address, port)))
        thread = threading.Thread(target=self._receive,
                                  args=(hashed_nickname, socket_client, self._ciphers[-1]))
        thread.start()
        self._threads.append(thread)
        self._mutex.release()

    def send(self, sid: int, message: str, code: int = CommandCodes.TEXT_MESSAGE):
        self._mutex.acquire()
        sock = self._peers[sid][0]
        cipher = self._ciphers[sid]
        self._mutex.release()

        data = cipher.serialize(message.encode(), code)
        sock.send(data)

    def _receive(self, sid: int, sock: socket.socket, cipher: ChatCipher):
        while True:
            msg = sock.recv(4096)
            if msg == b"":
                self._delete_user(sid)
                sys.exit(0)
            data = cipher.deserialize(msg)
            code = data[2]
            if code == CommandCodes.TEXT_MESSAGE:
                print(f"{data[0]}: {data[1].decode()}")
            elif code == CommandCodes.FIND_SUCCESSOR:
                node_id, invite = data[1].decode().split()
                node_id = int(node_id)
                self.find_successor(node_id, invite)
            elif code == CommandCodes.RETURN_SUCCESSOR:
                invite = data[1].decode()
                self.establish_connection(invite)
                self.predecessor = self._peers[-1]
                self.send(self._peers[-1], self._id, CommandCodes.SUCCESSOR_RESPONSE)
            elif code == CommandCodes.SUCCESSOR_RESPONSE:
                self.successor = int(data[1].decode())
                self.successors.append(self.successor)

    def generate_invite(self):
        invite = ""
        ip_list = self._socket_listener.getsockname()[0].split('.')
        for i in ip_list:
            invite += format(int(i), '02x')
        invite += format(self._socket_listener.getsockname()[1], '04x')
        invite += self._nickname

        # TODO: Check if token is already taken in global network

        self._mutex.acquire()

        key = os.urandom(32)
        while key in self._token_dict.keys():
            key = os.urandom(32)

        self.key = key
        self._mutex.release()
        invite += key.hex()
        print(invite)
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
        assert (len(token) == 172)
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
        self._peers.pop(index)
        self._threads.pop(index)
        self._ciphers.pop(index)
        self._mutex.release()

    def get_connections(self):
        pass
