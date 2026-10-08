import asyncio
import logging
from collections.abc import Generator
from typing import Any

from google.protobuf import json_format
from mitmproxy import ctx

from embed import KEYS
from generated.common_keys_pb2 import CommonKeys
from gfl2logger.gfl2.data.base import BaseData

logger = logging.getLogger(__name__)


class CommonKeysData(BaseData):
    OPTIONS = [
        {
            "name": "gfl2_commonkeys",
            "label": "Common Keys",
            "category": "Others",
            "typespec": bool,
            "default": True,
            "help": "Log Common Keys on login",
        }
    ]

    async def export(self) -> None:
        if ctx.options.gfl2_commonkeys:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self.to_csv)

    def to_raw_dicts(self) -> Generator[dict[str, Any]]:
        for b in self.data:
            keys = CommonKeys()
            keys.ParseFromString(b)
            yield json_format.MessageToDict(keys)

    def to_dicts(self) -> Generator[dict[str, Any]]:
        for data in self.to_raw_dicts():
            for row in data.get("keys", []):
                yield {
                    "uid": row.get("uid"),
                    "name": KEYS.get(row.get("keyId")),
                }

    def to_csv(self) -> None:
        cols = [
            "uid",
            "name",
        ]
        self.write_csv("commonkeys", "Common Keys", cols, self.to_dicts())
