import asyncio
import logging
from collections.abc import Generator
from typing import Any

from google.protobuf import json_format
from mitmproxy import ctx

from generated.platoon_profile_pb2 import PlatoonProfileResponse
from gfl2logger.gfl2.data.base import BaseData

logger = logging.getLogger(__name__)


class PlatoonProfileData(BaseData):
    OPTIONS = [
        {
            "name": "gfl2_platoonprofile",
            "label": "Platoon Profile",
            "category": "Platoon",
            "typespec": bool,
            "default": True,
            "help": "Log the Platoon profile",
        }
    ]

    async def export(self) -> None:
        if ctx.options.gfl2_platoonprofile:
            await asyncio.to_thread(self.to_json)

    def to_dicts(self) -> Generator[dict[str, Any]]:
        for payload in self.data:
            profile = PlatoonProfileResponse()
            profile.ParseFromString(payload)
            yield json_format.MessageToDict(profile)

    def to_json(self) -> None:
        self.write_json("platoonprofile", "Platoon profile", list(self.to_dicts()))
