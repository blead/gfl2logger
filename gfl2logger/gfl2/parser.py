import asyncio
import logging
from collections.abc import Generator
from typing import Self

from gfl2logger.gfl2.data import DATA_TYPES
from gfl2logger.utils import asyncio_utils

logger = logging.getLogger(__name__)


class Payload:
    def __init__(self, b: bytearray, msg_id=-1):
        if len(b) < 4:
            raise Exception(
                f"cannot construct payload with less than 4 bytes, b={b.hex()}"
            )
        self.msg_id = msg_id
        self.end_of_msg = False
        self.type = int.from_bytes(b[0:2], "little")
        self.len = int.from_bytes(b[2:4], "little") + 4
        if self.len > len(b):
            raise Exception(
                f"not enough data to construct payload, expected_len={self.len}, len(b)={len(b)}, b={b.hex()}"
            )
        self.data = bytes(b[4 : self.len])

    @classmethod
    def from_sequence(cls, b: bytearray, msg_id=-1) -> Generator[Self]:
        i = 0
        try:
            while i < len(b):
                payload = cls(b[i:], msg_id)
                i += payload.len
                if i >= len(b):
                    payload.end_of_msg = True
                yield payload
        except Exception as e:
            logger.error(f"Malformed payload, exception={e}")


class GFL2Parser:
    def __init__(self):
        self.msg_queue: asyncio.Queue[bytes] = asyncio.Queue()
        self.payload_queue: asyncio.Queue[Payload] = asyncio.Queue()
        self.active = True

        asyncio_utils.create_task(self.parse_message())
        asyncio_utils.create_task(self.parse_payload())

    def stop(self) -> None:
        self.active = False
        self.msg_queue.shutdown()
        self.payload_queue.shutdown()

    async def on_message(self, content: bytes) -> None:
        await self.msg_queue.put(content)

    async def parse_message(self) -> None:
        buffer = bytearray()
        total_len = 0
        msg_id = -1

        while self.active:
            try:
                content = await self.msg_queue.get()
            except asyncio.QueueShutDown:
                break

            buffer.extend(content)

            while True:
                if total_len == 0 and len(buffer) < 5:
                    logger.warning(
                        f"Message skipped due to insufficient length, buffer={buffer.hex()}"
                    )
                    buffer.clear()
                    break

                # start of new messsage
                if total_len == 0:
                    msg_id = int.from_bytes(buffer[0:3], "little")
                    total_len = int.from_bytes(buffer[3:5], "little") + 5

                # wait for more data
                if total_len > len(buffer):
                    break

                for payload in Payload.from_sequence(buffer[5:total_len], msg_id):
                    await self.payload_queue.put(payload)

                # end of mesage
                if total_len == len(buffer):
                    buffer.clear()
                    total_len = 0
                    msg_id = -1
                    break

                # jump to next message
                buffer = buffer[total_len:]
                total_len = 0
                msg_id = -1

    async def parse_payload(self) -> None:
        prev_payload: Payload | None = None
        prev_data = None
        while self.active:
            try:
                payload = await self.payload_queue.get()
            except asyncio.QueueShutDown:
                break

            logger.debug(
                f"PLD: msg_id={payload.msg_id}, eom={payload.end_of_msg}, type={payload.type}, len={payload.len}"
            )

            # prev_payload exists
            if prev_payload is not None and prev_data is not None:
                # can append
                if prev_payload.type == payload.type and (
                    prev_payload.msg_id == 0 or prev_payload.msg_id == payload.msg_id
                ):
                    prev_payload = payload
                    prev_data.append(payload.data)

                    # end of message, export
                    if payload.msg_id != 0 and payload.end_of_msg:
                        await prev_data.export()
                        prev_payload = None
                        prev_data = None
                    continue

                # cannot append, export prev_data
                await prev_data.export()
                prev_payload = None
                prev_data = None

            # no prev_payload

            # ignore unrecognized payload
            if payload.type not in DATA_TYPES:
                continue

            data = DATA_TYPES[payload.type](payload.data)

            # end of message, export
            if payload.msg_id != 0 and payload.end_of_msg:
                try:
                    await data.export()
                except Exception as e:
                    logger.error(f"Unable to export data, exception={e}")
                continue

            prev_payload = payload
            prev_data = data
