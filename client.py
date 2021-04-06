import os
import socket
import sys
import threading

from security.chat_cipher import ChatCipher
from chord.table_node import TableNode


class Client:

    def __init__(self):
        print("Started client")

        self.client_node = TableNode()

    def input_cycle(self):

        while True:
            q = input("create - create own ring; registration - join to the known ring\n")
            if q == "create":
                self.client_node.create()
            elif q == "registration":
                while True:
                    q = input("Please, write your invite token:\n")
                    self.client_node.establish_connection(q)
                    # try:
                    #     self.client_node.establish_connection(q)
                    #     break
                    # except Exception:
                    #     pass
                    # TODO: exception for existing nickname

            while True:
                q = input()
                ls = q.split(' ')
                if ls[0] == "quit":
                    # Exit from program
                    os._exit(0)
                elif ls[0] == "ls":
                    # Print all connection and their IDs
                    print(self.client_node.get_connections())
                elif ls[0] == "connect":
                    # Connect to new client
                    self.client_node.establish_connection(ls[1])
                elif ls[0] == "invite":
                    self.client_node.generate_invite()
                else:
                    # Send message to Client with specific ID
                    self.client_node.send(int(ls[0]), q.split(' ', 1)[1])

