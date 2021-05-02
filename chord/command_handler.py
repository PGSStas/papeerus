from chord.command_codes import CommandCodes
from hashlib import sha1
import threading


class CommandHandler:

    def __init__(self, node):
        self.node = node

    def _successor_response(self, successor):
        self.node._mutex.acquire()
        if not self.node.fixing_fingers:
            self.node.successor = successor
            self.node.successors.append(self.node.successor)
            if self.node.stabilization_thread is None:
                thread = threading.Thread(target=self.node.stabilize)
                thread.start()
            if self.node.finger_thread is None:
                thread = threading.Thread(target=self.node.fix_fingers)
                thread.start()
            self.node.log("Got successor - {}".format(self.node.successor))
        else:
            if len(self.node.finger_table) < self.node._m:
                self.node.finger_table.append(successor)
            else:
                self.node.finger_table[self.node.finger_num] = successor
            self.node.finger_num += 1
            self.node.finger_num %= self.node._m
            self.fixing_fingers = False
        self.node._mutex.release()

    def _return_successor(self, data):
        invite = data[1].decode()
        _, _, _, nickname = self.node._parse_invite_token(invite)
        sid = int(sha1(nickname.encode()).hexdigest(), 16)
        if sid != self.node._id:
            if sid in self.node._peers:
                self.node.send(sid, str(self.node._id), CommandCodes.SUCCESSOR_RESPONSE)
            else:
                self.node.establish_connection(invite)
                self.node.send(self.node._ids[-1], str(self.node._id), CommandCodes.SUCCESSOR_RESPONSE)
            self.node.log("I'm predecessor of {}".format(self.node.predecessor))

    def _predecessor_request(self, data):
        self.node_id, invite = data[1].decode().split()
        if self.node.predecessor:
            self.node.send(self.node.predecessor, self.node_id + " " + invite,
                           CommandCodes.PREDECESSOR_CALLBACK)
        else:
            self.node.send(int(self.node_id), "None", CommandCodes.PREDECESSOR_RESPONSE)

    def _find_successor(self, data):
        self.node_id, invite = data[1].decode().split()
        self.node_id = int(self.node_id)
        self.node.find_successor(self.node_id, invite)

    def _predecessor_callback(self, data):
        dst_id, invite = data[1].decode().split()
        self.node.establish_connection(invite)
        self.node.send(int(dst_id), str(self.node._id), CommandCodes.PREDECESSOR_RESPONSE)

    def _predecessor_response(self, data):
        self.node_id = data[1].decode()
        if self.node_id == 'None':
            self.node.continue_stabilizing(None)
        else:
            self.node.continue_stabilizing(int(self.node_id))

    def handle_commands(self, code, data):
        if code == CommandCodes.TEXT_MESSAGE:
            self.node.receive_message(data)

        elif code == CommandCodes.FIND_SUCCESSOR:
            self._find_successor(data)

        elif code == CommandCodes.RETURN_SUCCESSOR:
            self._return_successor(data)

        elif code == CommandCodes.SUCCESSOR_RESPONSE:
            self._successor_response(int(data[1].decode()))

        elif code == CommandCodes.PREDECESSOR_REQUEST:
            self._predecessor_request(data)

        elif code == CommandCodes.PREDECESSOR_CALLBACK:
            self._predecessor_callback(data)

        elif code == CommandCodes.PREDECESSOR_RESPONSE:
            self._predecessor_response(data)

        elif code == CommandCodes.NOTIFY:
            self.node.notify(int(data[1].decode()))

