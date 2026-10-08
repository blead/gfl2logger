import asyncio
import logging
from typing import Any

from mitmproxy import ctx

from gfl2logger.gfl2.data.base import BaseData
from gfl2logger.gfl2.protobuf_wire import WireDecodeError, decode_message

logger = logging.getLogger(__name__)


class PlatoonUpdatesData(BaseData):
    OPTIONS = [
        {
            "name": "gfl2_platoonupdates",
            "label": "Updates",
            "category": "Platoon",
            "typespec": bool,
            "default": True,
            "help": "Log live Platoon update payloads",
        }
    ]

    async def export(self) -> None:
        if ctx.options.gfl2_platoonupdates:
            await asyncio.to_thread(self.to_json)

    def to_dicts(self) -> list[dict[str, Any]]:
        decoded = []
        for payload in self.data:
            item: dict[str, Any] = {"rawHex": payload.hex()}
            try:
                item["fields"] = decode_message(payload)
            except WireDecodeError as error:
                item["decodeError"] = str(error)
            decoded.append(item)
        return decoded

    def to_json(self) -> None:
        self.write_json("platoonupdates", "Platoon updates", self.to_dicts())
