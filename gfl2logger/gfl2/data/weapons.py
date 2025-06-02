import asyncio
import csv
import logging
from collections.abc import Generator
from typing import Any

from google.protobuf import json_format
from mitmproxy import ctx, log

from embed import WEAPONS
from generated.weapons_pb2 import Weapons
from gfl2logger.gfl2.data.base import BaseData

logger = logging.getLogger(__name__)


class WeaponsData(BaseData):
    OPTIONS = [
        {
            "name": "gfl2_weapons",
            "label": "Weapons",
            "typespec": bool,
            "default": True,
            "help": "Log weapons on login",
        }
    ]

    async def export(self) -> None:
        if ctx.options.gfl2_weapons:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self.to_csv)

    def to_raw_dicts(self) -> Generator[dict[str, Any]]:
        for b in self.data:
            weapons = Weapons()
            weapons.ParseFromString(b)
            yield json_format.MessageToDict(weapons)

    def to_dicts(self) -> Generator[dict[str, Any]]:
        for data in self.to_raw_dicts():
            for row in data["weapons"]:
                yield {
                    "uid": row.get("uid"),
                    "name": WEAPONS.get(row.get("id")),
                    "level": row.get("level"),
                    "rank": row.get("rank"),
                }

    def to_csv(self) -> None:
        filename = f"gfl2logger_weapons_{self.log_time.strftime('%Y%m%dT%H%M%SZ')}.csv"
        cols = [
            "uid",
            "name",
            "level",
            "rank",
        ]
        data = self.to_dicts()

        try:
            with open(filename, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(data)
            logger.log(log.ALERT, f"Weapons data written to {filename}")
        except OSError as e:
            logger.error(f"Failed to write to {filename}, error={e}")
