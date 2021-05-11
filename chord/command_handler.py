from chord.command_codes import CommandCodes
from hashlib import sha1
import threading


class CommandHandler:
    def __init__(self, node):
        self.node = node

    def _find_successor(self, data):
        node_id, sender, key, invite = data[1].decode().split()
        self.node.find_successor(int(node_id), int(sender), key, invite)

    def _return_successor(self, data):
        successor, key = data[1].decode().split()
        self.node.return_successor(int(successor), key)

    def _predecessor_request(self, data):
        node_id, invite = data[1].decode().split()
        if self.node.predecessor:
            self.node.send(self.node.predecessor, f"{node_id} {invite}", CommandCodes.PREDECESSOR_CALLBACK)
        else:
            self.node.send(int(node_id), "None", CommandCodes.PREDECESSOR_RESPONSE)

    def _predecessor_callback(self, data):
        dst_id, invite = data[1].decode().split()
        self.node.establish_connection(invite)
        self.node.send(int(dst_id), str(self.node._id), CommandCodes.PREDECESSOR_RESPONSE)

    def _predecessor_response(self, data):
        node_id = data[1].decode()
        if node_id == 'None':
            self.node.continue_stabilizing(None)
        else:
            self.node.continue_stabilizing(int(node_id))

    def _establish_with(self, data):
        self.node.establish_connection(data[1].decode())

    def _pass_message(self, data):
        x, message = data[1].decode().split(" ", 1)
        self.node.pass_message(int(x), message)

    def _store_message(self, data):
        x, message = data[1].decode().split(" ", 1)
        self.node.store_message(int(x), message)

    def _chat_request(self, data):
        node_id, key = data[1].decode().split(" ", 1)
        self.node.chat_request(int(node_id), int(key))

    def _chat_response(self, data):
        key, messages = data[1].decode().split(" ", 1)
        self.node.chat_response(int(key), bytes.fromhex(messages))

    def _receive_chat_copy(self, data):
        self.node.receive_chat_copy(data[1])

    def handle_commands(self, code, data):
        if code == CommandCodes.TEXT_MESSAGE:
            self.node.receive_message(data)

        elif code == CommandCodes.FIND_SUCCESSOR:
            self._find_successor(data)

        elif code == CommandCodes.RETURN_SUCCESSOR:
            self._return_successor(data)

        elif code == CommandCodes.PREDECESSOR_REQUEST:
            self._predecessor_request(data)

        elif code == CommandCodes.PREDECESSOR_CALLBACK:
            self._predecessor_callback(data)

        elif code == CommandCodes.PREDECESSOR_RESPONSE:
            self._predecessor_response(data)

        elif code == CommandCodes.NOTIFY:
            self.node.notify(int(data[1].decode()))

        elif code == CommandCodes.ESTABLISH_WITH:
            self._establish_with(data)

        elif code == CommandCodes.PASS_MESSAGE:
            self._pass_message(data)

        elif code == CommandCodes.STORE_MESSAGE:
            self._store_message(data)

        elif code == CommandCodes.CHAT_REQUEST:
            self._chat_request(data)

        elif code == CommandCodes.CHAT_RESPONSE:
            self._chat_response(data)

        elif code == CommandCodes.RECEIVE_CHAT_COPY:
            self._receive_chat_copy(data)
