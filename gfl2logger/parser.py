import logging
import re
from collections.abc import Callable
from enum import Enum, auto
from typing import Any

logger = logging.getLogger(__name__)


class GuildMembersParser:
    GUILD_MEMBERS_REQ_PATTERN = re.compile(
        b"(...)\x04\x00\x98\x55\x00\x00(...)\x04\x00\x9c\x55\x00\x00"
    )
    GUILD_MEMBERS_RES_HEADER = b"\x9d\x55"

    class State(Enum):
        INIT = auto()
        APPLICATIONS_SEQ = auto()
        MEMBERS_SEQ = auto()
        MEMBERS_HEADER = auto()
        MEMBERS_BODY = auto()

    def __init__(self, on_save: Callable[[bytes], Any]) -> None:
        self.on_save = on_save
        self.data = bytearray()
        self.state = GuildMembersParser.State.INIT
        self.position = 0
        self.guild_applications_seq: bytes | None = None
        self.guild_members_seq: bytes | None = None
        self.guild_members_remaining_size = 0

    def is_from_client_expected(self) -> bool:
        """True if the parser currently expects to parse messages sent by the client instead of the server."""
        return self.state == GuildMembersParser.State.INIT

    def on_message(self, content: bytes) -> None:
        while self.position < len(content):
            self.position += self._parse(content[self.position :])
        self.position -= len(content)

        if self.position != 0:
            logger.warning("parser position was not reset properly")
            self.position = 0

    def _parse(self, content: bytes) -> int:
        """Returns the number of parsed bytes."""
        match self.state:
            case GuildMembersParser.State.INIT:
                matches = GuildMembersParser.GUILD_MEMBERS_REQ_PATTERN.search(content)
                if matches is None:
                    return len(content)

                logger.debug(f"{self.state.name}: guild members request matched")

                self.guild_applications_seq = matches.group(1)
                self.guild_members_seq = matches.group(2)
                self.state = GuildMembersParser.State.APPLICATIONS_SEQ
                return 18
            case GuildMembersParser.State.APPLICATIONS_SEQ:
                if self.guild_applications_seq and content.startswith(
                    self.guild_applications_seq
                ):
                    guild_applications_size = int.from_bytes(content[3:5], "little")

                    logger.debug(
                        f"{self.state.name}: applications section found, len={guild_applications_size}"
                    )

                    # skip applications section entirely as it is not needed
                    self.state = GuildMembersParser.State.MEMBERS_SEQ
                    return 5 + guild_applications_size
                return len(content)
            case GuildMembersParser.State.MEMBERS_SEQ:
                if self.guild_members_seq and content.startswith(
                    self.guild_members_seq
                ):
                    self.guild_members_remaining_size = int.from_bytes(
                        content[3:5], "little"
                    )

                    logger.debug(
                        f"{self.state.name}: members section found, remaining len={self.guild_members_remaining_size}"
                    )
                    self.state = GuildMembersParser.State.MEMBERS_HEADER
                    return 5
                return len(content)
            case GuildMembersParser.State.MEMBERS_HEADER:
                if content.startswith(GuildMembersParser.GUILD_MEMBERS_RES_HEADER):
                    self.guild_members_remaining_size = int.from_bytes(
                        content[2:4], "little"
                    )

                    logger.debug(
                        f"{self.state.name}: members section header found, remaining len={self.guild_members_remaining_size}"
                    )
                    self.state = GuildMembersParser.State.MEMBERS_BODY
                    return 4
                return len(content)
            case GuildMembersParser.State.MEMBERS_BODY:
                members_data_len = len(content[: self.guild_members_remaining_size])
                self.data += content[: self.guild_members_remaining_size]
                self.guild_members_remaining_size -= members_data_len

                logger.debug(
                    f"{self.state.name}: members section parsed, data len={members_data_len}, remaining len={self.guild_members_remaining_size}"
                )

                if self.guild_members_remaining_size < 0:
                    logger.warning(f"{self.state.name}: remaining size < 0")
                    self.guild_members_remaining_size = 0

                if self.guild_members_remaining_size == 0:
                    self.state = GuildMembersParser.State.INIT
                    self.guild_applications_seq = None
                    self.guild_members_seq = None
                    self._save_data()

                return members_data_len

    def _save_data(self) -> None:
        logger.debug(f"{self.state.name}: saving data, len={len(self.data)}")

        self.on_save(self.data)
        self.data = bytearray()
