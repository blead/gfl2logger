import asyncio
import json
import logging
from collections.abc import Generator, Iterable
from typing import Any

from google.protobuf import json_format
from mitmproxy import ctx, log

from embed import DOLLS, KEYS
from generated.formations_pb2 import FormationsResponse
from gfl2logger.gfl2.data.base import BaseData

logger = logging.getLogger(__name__)


class FormationsData(BaseData):
    OPTIONS = [
        {
            "name": "gfl2_formations",
            "label": "Formations",
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
            for row in data["formations"]["formations"]:
                output = {
                    "name": row.get("name"),
                    "dolls": list(FormationsData.map_dolls(row.get("dolls", []))),
                }
                yield {k: output[k] for k in output if output[k]}

    def to_json(self) -> None:
        filename = (
            f"gfl2logger_formations_{self.log_time.strftime('%Y%m%dT%H%M%SZ')}.json"
        )
        data = list(self.to_dicts())

        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.log(log.ALERT, f"Formations data written to {filename}")
        except OSError as e:
            logger.error(f"Failed to write to {filename}, error={e}")
