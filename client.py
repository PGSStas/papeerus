import os
import socket
import threading


class Client:
    def __init__(self):
        print("Started client")

        self._socket_listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket_listener.bind(("localhost", 0))
        self._socket_listener.listen()
        print(f"Listening on 127.0.0.1:{self._socket_listener.getsockname()[1]}")
        self._mutex = threading.Lock()

        self._peers = []
        self._ciphers = []
        self._threads = []

        self._accept_thread = threading.Thread(target=self._accept_connection)
        self._accept_thread.start()

    def input_cycle(self):
        while True:
            q = input()
            ls = q.split(' ')
            if ls[0] == "quit":
                os._exit(0)
            elif ls[0] == "ls":
                for i in range(0, len(self._peers)):
                    print(f"#{i} {self._peers[i][1][0]}:{self._peers[i][1][1]}")
            elif ls[0] == "connect":
                self._establish_connection(ls[1], ls[2])
            else:
                self._send(self._peers[int(ls[0])][0], q.split(' ', 1)[1])

    def _accept_connection(self):
        while True:
            connection = self._socket_listener.accept()

            self._mutex.acquire()
            self._peers.append(connection)
            thread = threading.Thread(target=self._receive,
                                      args=(connection[0],
                                            connection[1][0] + ":" + str(connection[1][1])))
            thread.start()
            self._threads.append(thread)
            self._mutex.release()

    def _establish_connection(self, address, port):
        socket_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        socket_client.connect((address, int(port)))

        self._mutex.acquire()
        self._peers.append((socket_client, (address, port)))
        thread = threading.Thread(target=self._receive,
                                  args=(socket_client, address + ":" + port))
        thread.start()
        self._threads.append(thread)
        self._mutex.release()

    def _send(self, sock, message):
        data = message.encode()
        sock.send(data)

    def _receive(self, sock, address):
        while True:
            msg = sock.recv(4096)
            print(f"{address}: {msg.decode()}")


if __name__ == '__main__':
    client = Client()
    client.input_cycle()
