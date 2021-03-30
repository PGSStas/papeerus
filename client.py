import os
import socket
import threading
import sys


class Client:
    # Temp id for sockets
    _sid = 0
    # List of sockets, ciphers and threads for receive
    _ids = []
    _peers = []
    _ciphers = []
    _threads = []

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
                self._establish_connection(ls[1], ls[2])
            else:
                # Send message to Client with specific ID
                self._send(self._peers[int(ls[0])][0], q.split(' ', 1)[1])

    def _accept_connection(self):
        while True:
            connection = self._socket_listener.accept()

            self._mutex.acquire()
            self._sid += 1
            self._ids.append(self._sid)
            self._peers.append(connection)
            thread = threading.Thread(target=self._receive,
                                      args=(self._sid, connection[0],
                                            connection[1][0] + ":" + str(connection[1][1])))
            thread.start()
            self._threads.append(thread)
            self._mutex.release()

    def _establish_connection(self, address: str, port: str):
        socket_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        socket_client.connect((address, int(port)))

        self._mutex.acquire()
        self._sid += 1
        self._ids.append(self._sid)
        self._peers.append((socket_client, (address, port)))
        thread = threading.Thread(target=self._receive,
                                  args=(self._sid,
                                        socket_client, address + ":" + port))
        thread.start()
        self._threads.append(thread)
        self._mutex.release()

    def _send(self, sock: socket.socket, message: str):
        data = message.encode()
        sock.send(data)

    def _receive(self, sid: int, sock: socket.socket, address: str):
        while True:
            msg = sock.recv(4096)
            if msg == b"":
                self._mutex.acquire()
                index = self._ids.index(sid)

                self._ids.pop(index)
                self._peers.pop(index)
                self._threads.pop(index)
                self._mutex.release()
                sys.exit(0)
            print(f"{address}: {msg.decode()}")
