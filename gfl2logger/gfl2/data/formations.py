import asyncio
import logging
from collections.abc import Generator, Iterable
from typing import Any

from google.protobuf import json_format
from mitmproxy import ctx

from embed import DOLLS, KEYS
from generated.formations_pb2 import FormationsResponse
from gfl2logger.gfl2.data.base import BaseData

logger = logging.getLogger(__name__)


class FormationsData(BaseData):
    OPTIONS = [
        {
            "name": "gfl2_formations",
            "label": "Formations",
            "category": "Others",
            "typespec": bool,
            "default": True,
            "help": "Log Formations on login",
        }
    ]

    @staticmethod
    def map_dolls(dolls: Iterable[dict[str, Any]]) -> Generator[dict[str, Any]]:
        for doll in dolls:
            if not doll:
                yield doll
                continue

            yield {
                "name": DOLLS.get(doll.get("dollId", -1)),
                "weaponUid": doll.get("weaponUid"),
                "attachmentUids": doll.get("attachmentUids", []),
                "fixedKeys": [
                    KEYS.get(id, "-") for id in doll.get("fixedKeyIds", [0, 0, 0])
                ],
                "expansionKeys": [
                    KEYS.get(id, "-") for id in doll.get("expansionKeyIds", [0])
                ],
                "commonKeyUids": [
                    id for id in doll.get("commonKeyUids", ["0", "0", "0"])
                ],
            }

    async def export(self) -> None:
        if ctx.options.gfl2_formations:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self.to_json)

    def to_raw_dicts(self) -> Generator[dict[str, Any]]:
        for b in self.data:
            formations = FormationsResponse()
            formations.ParseFromString(b)
            yield json_format.MessageToDict(formations)

    def to_dicts(self) -> Generator[dict[str, Any]]:
        for data in self.to_raw_dicts():
            for row in data.get("formations", {}).get("formations", []):
                output = {
                    "name": row.get("name"),
                    "dolls": list(FormationsData.map_dolls(row.get("dolls", []))),
                }
                yield {k: output[k] for k in output if output[k]}

    def to_json(self) -> None:
        self.write_json("formations", "Formations", list(self.to_dicts()))
