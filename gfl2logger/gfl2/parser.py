import asyncio
import logging
from collections.abc import Generator
from typing import Self

from gfl2logger.gfl2.data import DATA_TYPES
from gfl2logger.gfl2.data.base import BaseData, ReassemblyLimitError
from gfl2logger.utils import asyncio_utils

logger = logging.getLogger(__name__)

MAX_MESSAGE_QUEUE_ITEMS = 16
MAX_PAYLOAD_QUEUE_ITEMS = 128
MAX_INPUT_CHUNK_BYTES = 1024 * 1024
REASSEMBLY_TIMEOUT_SECONDS = 30.0
MESSAGE_HEADER_BYTES = 5
PAYLOAD_HEADER_BYTES = 4
LOG_PREVIEW_BYTES = 32


class PayloadError(ValueError):
    """Raised when a payload header does not describe the bytes that follow it."""


def _preview(b: bytes | bytearray | memoryview) -> str:
    # Malformed input can be a whole 64 KiB message; logging all of it would flood the GUI.
    head = bytes(b[:LOG_PREVIEW_BYTES]).hex()
    return head + "..." if len(b) > LOG_PREVIEW_BYTES else head


class Payload:
    def __init__(self, b: bytes | bytearray | memoryview, msg_id=-1):
        if len(b) < PAYLOAD_HEADER_BYTES:
            raise PayloadError(
                f"cannot construct payload with less than 4 bytes, b={_preview(b)}"
            )
        self.msg_id = msg_id
        self.end_of_msg = False
        self.type = int.from_bytes(b[0:2], "little")
        self.len = int.from_bytes(b[2:4], "little") + PAYLOAD_HEADER_BYTES
        if self.len > len(b):
            raise PayloadError(
                f"not enough data to construct payload, expected_len={self.len}, len(b)={len(b)}, b={_preview(b)}"
            )
        self.data = bytes(b[PAYLOAD_HEADER_BYTES : self.len])

    @classmethod
    def from_sequence(
        cls, b: bytes | bytearray | memoryview, msg_id=-1
    ) -> Generator[Self]:
        # A view lets each payload be cut out without first copying the rest of the message.
        view = memoryview(b)
        i = 0
        try:
            while i < len(view):
                payload = cls(view[i:], msg_id)
                i += payload.len
                if i >= len(view):
                    payload.end_of_msg = True
                yield payload
        except PayloadError as e:
            logger.error("Malformed payload, exception=%s", e)


class GFL2Parser:
    def __init__(self, *, reassembly_timeout: float = REASSEMBLY_TIMEOUT_SECONDS):
        self.msg_queue: asyncio.Queue[bytes] = asyncio.Queue(
            maxsize=MAX_MESSAGE_QUEUE_ITEMS
        )
        self.payload_queue: asyncio.Queue[Payload] = asyncio.Queue(
            maxsize=MAX_PAYLOAD_QUEUE_ITEMS
        )
        self.active = True
        self.reassembly_timeout = reassembly_timeout
        self._pending_payload: Payload | None = None
        self._pending_data: BaseData | None = None
        self._pending_started_at: float | None = None

        self._tasks = (
            asyncio_utils.create_task(self.parse_message()),
            asyncio_utils.create_task(self.parse_payload()),
        )

    def stop(self) -> None:
        # Only the input side is closed here. Chunks that are already queued are still
        # parsed, and parse_message closes the payload queue once it has drained them, so
        # the last message of a flow is not lost when the connection closes right after it.
        self.active = False
        self.msg_queue.shutdown()

    async def on_message(self, content: bytes) -> None:
        if len(content) > MAX_INPUT_CHUNK_BYTES:
            logger.warning(
                "Dropping oversized TCP chunk, len=%d, max=%d",
                len(content),
                MAX_INPUT_CHUNK_BYTES,
            )
            return
        try:
            await self.msg_queue.put(content)
        except asyncio.QueueShutDown:
            pass

    async def parse_message(self) -> None:
        buffer = bytearray()

        try:
            while True:
                content = await self.msg_queue.get()
                buffer.extend(content)

                # TCP chunk boundaries are not message boundaries: a chunk may end inside
                # a header or a body, so incomplete bytes stay buffered for the next chunk.
                while len(buffer) >= MESSAGE_HEADER_BYTES:
                    msg_id = int.from_bytes(buffer[0:3], "little")
                    total_len = (
                        int.from_bytes(buffer[3:5], "little") + MESSAGE_HEADER_BYTES
                    )
                    if total_len > len(buffer):
                        break

                    message = bytes(buffer[MESSAGE_HEADER_BYTES:total_len])
                    del buffer[:total_len]
                    for payload in Payload.from_sequence(message, msg_id):
                        await self.payload_queue.put(payload)
        except asyncio.QueueShutDown:
            pass
        finally:
            self.payload_queue.shutdown()

    async def _export_data(self, data: BaseData) -> None:
        try:
            await data.export()
        except Exception as e:
            logger.error(f"Unable to export data, exception={e}")

    def _clear_pending(self) -> None:
        self._pending_payload = None
        self._pending_data = None
        self._pending_started_at = None

    async def _export_pending(self) -> None:
        data = self._pending_data
        self._clear_pending()
        if data is not None:
            await self._export_data(data)

    async def _next_payload(self) -> Payload | None:
        if self._pending_started_at is None:
            return await self.payload_queue.get()

        deadline = self._pending_started_at + self.reassembly_timeout
        remaining = deadline - asyncio.get_running_loop().time()
        if remaining <= 0:
            logger.warning("Payload reassembly timed out; dropping incomplete sequence")
            self._clear_pending()
            return None

        try:
            return await asyncio.wait_for(self.payload_queue.get(), timeout=remaining)
        except TimeoutError:
            logger.warning("Payload reassembly timed out; dropping incomplete sequence")
            self._clear_pending()
            return None

    async def _process_payload(self, payload: Payload) -> None:
        logger.debug(
            "PLD: msg_id=%d, eom=%s, type=%d, len=%d",
            payload.msg_id,
            payload.end_of_msg,
            payload.type,
            payload.len,
        )

        if self._pending_payload is not None and self._pending_data is not None:
            can_append = self._pending_payload.type == payload.type and (
                self._pending_payload.msg_id == 0
                or self._pending_payload.msg_id == payload.msg_id
            )
            if can_append:
                try:
                    self._pending_data.append(payload.data)
                except ReassemblyLimitError as e:
                    logger.warning(
                        "Dropping oversized payload sequence, type=%d, reason=%s",
                        payload.type,
                        e,
                    )
                    self._clear_pending()
                    return

                self._pending_payload = payload
                if payload.msg_id != 0 and payload.end_of_msg:
                    await self._export_pending()
                return

            await self._export_pending()

        if payload.type not in DATA_TYPES:
            return

        data = DATA_TYPES[payload.type](payload.data)
        if payload.msg_id != 0 and payload.end_of_msg:
            await self._export_data(data)
            return

        self._pending_payload = payload
        self._pending_data = data
        self._pending_started_at = asyncio.get_running_loop().time()

    async def parse_payload(self) -> None:
        try:
            while True:
                try:
                    payload = await self._next_payload()
                except asyncio.QueueShutDown:
                    break
                if payload is None:
                    continue
                try:
                    await self._process_payload(payload)
                except Exception:
                    # One bad payload must not end this task: the queues are bounded, so a
                    # dead consumer would block on_message and stall the game connection.
                    logger.exception(
                        "Unable to process payload, type=%d", payload.type
                    )
                    self._clear_pending()
        finally:
            # If this consumer ever stops, release the producers instead of blocking them.
            self.msg_queue.shutdown(immediate=True)
            self.payload_queue.shutdown(immediate=True)
