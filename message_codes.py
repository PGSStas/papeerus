from enum import Enum


class MessageCodes(Enum):
    TEXT = 0
    FILE = 1
    PATH = 2

    def __str__(self):
        return self.name

    @property
    def counter(self):
        return self.value
