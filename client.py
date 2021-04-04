import os
import socket
import sys
import threading

from security.chat_cipher import ChatCipher


class Client:
    # Temp id for sockets
    _sid = 0
    # List of sockets, ciphers and threads for receive
    _ids = []
    _peers = []
    _ciphers = []
    _threads = []
    _token_dict = {}

    # TODO: make registration
    _nickname = "Serega"

    def __init__(self):
        print("Started client")

        # Starting listener
        self._socket_listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket_listener.bind(("localhost", 0))
        self._socket_listener.listen()
        print(f"Listening on 127.0.0.1:{self._socket_listener.getsockname()[1]}")
        self._mutex = threading.Lock()

        self._accept_thread = threading.Thread(target=self._accept_connection)
        self._accept_thread.start()

    def input_cycle(self):
        while True:
            q = input()
            ls = q.split(' ')
            if ls[0] == "quit":
                # Exit from program
                os._exit(0)
            elif ls[0] == "ls":
                # Print all connection and their IDs
                for i in range(0, len(self._peers)):
                    print(f"#{i} {self._peers[i][1][0]}:{self._peers[i][1][1]}")
            elif ls[0] == "connect":
                # Connect to new client
                self._establish_connection(ls[1])
            elif ls[0] == "invite":
                self._generate_invite()
            else:
                # Send message to Client with specific ID
                self._send(int(ls[0]), q.split(' ', 1)[1])

    def _accept_connection(self):
        while True:
            connection = self._socket_listener.accept()
            key = connection[0].recv(32)
            if key in self._token_dict.keys():
                connection[0].send("CODE: 000".encode())
            else:
                connection[0].send("CODE: 001".encode())
                continue

            self._mutex.acquire()
            self._sid += 1
            self._ids.append(self._sid)
            self._ciphers.append(ChatCipher(self._token_dict[key][0], self._token_dict[key][1], self._nickname))
            self._peers.append(connection)
            thread = threading.Thread(target=self._receive,
                                      args=(self._sid, connection[0], self._ciphers[-1]))
            thread.start()
            self._threads.append(thread)
            self._mutex.release()

    def _establish_connection(self, token: str):
        address, port, key, iv, message_token = self._parse_token(token)
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

        self._mutex.acquire()
        self._sid += 1
        self._ids.append(self._sid)
        self._ciphers.append(ChatCipher(message_token, iv, self._nickname))
        self._peers.append((socket_client, (address, port)))
        thread = threading.Thread(target=self._receive,
                                  args=(self._sid, socket_client, self._ciphers[-1]))
        thread.start()
        self._threads.append(thread)
        self._mutex.release()

    def _send(self, sid: int, message: str):
        self._mutex.acquire()
        sock = self._peers[sid][0]
        cipher = self._ciphers[sid]
        self._mutex.release()

        data = cipher.serialize(message.encode())
        sock.send(data)

    def _receive(self, sid: int, sock: socket.socket, cipher: ChatCipher):
        while True:
            msg = sock.recv(4096)
            if msg == b"":
                self._delete_user(sid)
                sys.exit(0)
            data = cipher.deserialize(msg)
            print(f"{data[0]}: {data[1].decode()}")

    def _generate_invite(self):
        invite = ""
        ip_list = self._socket_listener.getsockname()[0].split('.')
        for i in ip_list:
            invite += format(int(i), '02x')
        invite += format(self._socket_listener.getsockname()[1], '04x')

        # TODO: Check if token is already taken in global network

        self._mutex.acquire()
        iv = os.urandom(16)
        token = os.urandom(32)
        while len([item for item in self._token_dict.values() if token == item[0]]) != 0:
            token = os.urandom(32)

        key = os.urandom(32)
        while key in self._token_dict.keys():
            key = os.urandom(32)

        self._token_dict[key] = (token, iv)
        self._mutex.release()
        invite += key.hex() + iv.hex() + token.hex()
        print(invite)

    def _parse_token(self, token: str):
        assert (len(token) == 172)
        ip = token[:8]
        port = int(token[8:12], 16)
        key = bytes.fromhex(token[12:76])
        iv = bytes.fromhex(token[76:108])
        message_token = bytes.fromhex(token[108:])

        parsed_ip = str(int(token[0:2], 16)) + "." + str(int(token[2:4], 16)) + \
                    "." + str(int(token[4:6], 16)) + "." + str(int(token[6:8], 16))
        return parsed_ip, port, key, iv, message_token

    def _delete_user(self, sid: int):
        self._mutex.acquire()
        index = self._ids.index(sid)

        self._ids.pop(index)
        self._peers.pop(index)
        self._threads.pop(index)
        self._ciphers.pop(index)
        self._mutex.release()
