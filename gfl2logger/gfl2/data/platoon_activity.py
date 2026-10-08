import asyncio
import logging
from typing import Any

from google.protobuf import json_format
from mitmproxy import ctx

from generated.platoon_activity_pb2 import PlatoonActivityResponse
from gfl2logger.gfl2.data.base import BaseData

logger = logging.getLogger(__name__)


class PlatoonActivityData(BaseData):
    OPTIONS = [
        {
            "name": "gfl2_platoonactivity",
            "label": "Activity",
            "category": "Platoon",
            "typespec": bool,
            "default": True,
            "help": "Log Platoon objectives and member activity",
        }
    ]

    async def export(self) -> None:
        if ctx.options.gfl2_platoonactivity:
            await asyncio.to_thread(self.to_json)

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, list[dict[str, Any]]] = {
            "objectives": [],
            "entries": [],
        }
        for payload in self.data:
            activity = PlatoonActivityResponse()
            activity.ParseFromString(payload)
            decoded = json_format.MessageToDict(activity)
            result["objectives"].extend(decoded.get("objectives", []))
            result["entries"].extend(decoded.get("entries", []))
        return result

    def to_json(self) -> None:
        self.write_json("platoonactivity", "Platoon activity", self.to_dict())
