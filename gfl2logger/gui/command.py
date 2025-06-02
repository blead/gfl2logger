from enum import Enum, auto
from typing import Any


class CommandType(Enum):
    LOG = auto()
    OPTIONS = auto()
    SAVE_OPTIONS = auto()
    SHUTDOWN = auto()


class Command:
    def __init__(self, type: CommandType, content: Any):
        self.type = type
        self.content = content
