import os
from chord.table_node import TableNode
from message.message import MessageSerializer
from message.split import Split


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
                    print(self.client_node.generate_invite())
                elif ls[0] == "info":
                    self.client_node.print_info()
                elif ls[0] == "picture":
                    parser = MessageSerializer()
                    mess = parser.serializeMessage(ls[1], 'picture')
                    splitter = Split()
                    obj = splitter.split(mess)
                    self.client_node.send_all(obj)
                elif ls[0] == "video":
                    parser = MessageSerializer()
                    mess = parser.serializeMessage(ls[1], 'video')
                    splitter = Split()
                    obj = splitter.split(mess)
                    self.client_node.send_all(obj)
                else:
                    parser = MessageSerializer()
                    mess = parser.serializeMessage(q, 'text')
                    splitter = Split()
                    obj = splitter.split(mess)
                    self.client_node.send_all(obj)
