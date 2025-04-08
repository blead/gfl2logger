import logging
from datetime import datetime, timezone
from typing import Any

from google.protobuf import json_format

from generated.guild_members_pb2 import GuildMembers

logger = logging.getLogger(__name__)

GUILD_MEMBERS_DATA_COLS = [
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


def decode_guild_members_data(data: bytes) -> dict[str, Any]:
    members = GuildMembers()
    members.ParseFromString(data)
    return json_format.MessageToDict(members)


def format_guild_members_data(
    data: dict[str, Any], log_time: datetime = datetime.now(timezone.utc)
) -> list[dict[str, Any]]:
    logger.debug(str(data))

    log_time_8601 = log_time.strftime("%Y-%m-%dT%H:%M:%SZ")

    return [
        {
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
        for row in data["members"]
    ]
