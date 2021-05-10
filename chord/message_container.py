import threading
import time
from threading import Thread
from chord.decorators import execute_periodically


class MessageContainer:
    MESSAGE_LIFETIME = 86400
    _messages = {}

    def __init__(self):
        self.mutex = threading.Lock()
        thread = Thread(target=self._delete_old_messages)
        thread.start()

    def add_message(self, key: int, message: str):
        with self.mutex:
            if key not in self._messages.keys():
                self._messages[key] = []
            self._messages[key].append((time.time(), message))

    def get_messages(self, key: int):
        with self.mutex:
            if key not in self._messages.keys():
                return []
            return self._messages[key]

    def set_chat(self, key: int, chat):
        with self.mutex:
            self._messages[key] = chat

    def split_by(self, sid):
        m1 = {}
        m2 = {}
        for key in self._messages.keys():
            if key <= sid:
                m1[key] = self._messages[key]
            else:
                m2[key] = self._messages[key]
        return m1, m2

    @execute_periodically(3600)
    def _delete_old_messages(self):
        with self.mutex:
            cur_time = time.time()
            for key in self._messages.keys():
                self._messages[key] = [x for x in self._messages[key] if cur_time - x[0] < self.MESSAGE_LIFETIME]
