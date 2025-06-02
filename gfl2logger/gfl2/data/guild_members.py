import asyncio
import csv
import logging
from collections.abc import Generator
from typing import Any

from google.protobuf import json_format
from mitmproxy import ctx, log

from generated.guild_members_pb2 import GuildMembers
from gfl2logger.gfl2.data.base import BaseData

logger = logging.getLogger(__name__)


class GuildMembersData(BaseData):
    OPTIONS = [
        {
            "name": "gfl2_guildmembers",
            "label": "Platoon members",
            "typespec": bool,
            "default": True,
            "help": "Log Platoon members on login/Platoon page",
        }
    ]

    async def export(self) -> None:
        if ctx.options.gfl2_guildmembers:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self.to_csv)

    def to_raw_dicts(self) -> Generator[dict[str, Any]]:
        for b in self.data:
            members = GuildMembers()
            members.ParseFromString(b)
            yield json_format.MessageToDict(members)

    def to_dicts(self) -> Generator[dict[str, Any]]:
        log_time_8601 = self.log_time.strftime("%Y-%m-%dT%H:%M:%SZ")

        for data in self.to_raw_dicts():
            for row in data["members"]:
                yield {
                    "uid": row.get("uid"),
                    "name": row.get("player", {}).get("playerInfo", {}).get("name"),
                    "level": row.get("player", {}).get("playerInfo", {}).get("level"),
                    "weeklyMerit": row.get("weeklyMerit"),
                    "totalMerit": row.get("totalMerit"),
                    "highScore": row.get("highScore"),
                    "totalScore": row.get("totalScore"),
                    "lastLogin": row.get("lastLogin"),
                    "logTime": log_time_8601,
                }

    def to_csv(self) -> None:
        filename = (
            f"gfl2logger_guildmembers_{self.log_time.strftime('%Y%m%dT%H%M%SZ')}.csv"
        )
        cols = [
            "uid",
            "name",
            "level",
            "weeklyMerit",
            "totalMerit",
            "highScore",
            "totalScore",
            "lastLogin",
            "logTime",
        ]
        data = self.to_dicts()

        try:
            with open(filename, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(data)
            logger.log(log.ALERT, f"Guild members data written to {filename}")
        except OSError as e:
            logger.error(f"Failed to write to {filename}, error={e}")
