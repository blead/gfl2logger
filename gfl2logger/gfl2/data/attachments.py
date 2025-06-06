import asyncio
import csv
import itertools
import logging
from collections.abc import Generator, Iterable
from typing import Any

from google.protobuf import json_format
from mitmproxy import ctx, log

from embed import (
    ATTACHMENT_EFFECTS,
    ATTACHMENTS,
    ATTRIBUTES_IS_PERCENT,
    ATTRIBUTES_NAME_STRIPPED,
)
from generated.attachments_pb2 import Attachments
from gfl2logger.gfl2.data.base import BaseData

logger = logging.getLogger(__name__)


class AttachmentsData(BaseData):
    OPTIONS = [
        {
            "name": "gfl2_attachments",
            "label": "Attachments",
            "typespec": bool,
            "default": True,
            "help": "Log Attachments on login",
        }
    ]

    @staticmethod
    def decode_attributes(attrs: int) -> Generator[dict[str, Any]]:
        for val, attr in itertools.batched(attrs.to_bytes(8, byteorder="little"), n=2):
            if attr == 0:
                break

            attr_name = ATTRIBUTES_NAME_STRIPPED.get(attr, str(attr))
            attr_is_percent = ATTRIBUTES_IS_PERCENT.get(attr, False)

            yield {"name": attr_name, "value": val / 10 if attr_is_percent else val}

    @staticmethod
    def map_attributes_calibrations(
        attributes: Iterable[dict[str, Any]], calibrations: Iterable[dict[str, Any]]
    ) -> Generator[tuple[str, Any]]:
        for attr, calib in itertools.zip_longest(
            attributes, calibrations, fillvalue={}
        ):
            attr_name = attr.get("name")
            if not isinstance(attr_name, str):
                continue

            calib_boost = calib.get("boost")
            if isinstance(calib_boost, int):
                calib_boost /= 10

            yield ("attr" + attr_name, attr.get("value"))
            yield ("calib" + attr_name, calib_boost)

    async def export(self) -> None:
        if ctx.options.gfl2_attachments:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self.to_csv)

    def to_raw_dicts(self) -> Generator[dict[str, Any]]:
        for b in self.data:
            attachments = Attachments()
            attachments.ParseFromString(b)
            yield json_format.MessageToDict(attachments)

    def to_dicts(self) -> Generator[dict[str, Any]]:
        for data in self.to_raw_dicts():
            for row in data["attachments"]:
                part_id = row.get("partId")
                yield {
                    "uid": row.get("uid"),
                    "name": ATTACHMENTS.get(part_id, {}).get("name", part_id),
                    "rarity": ATTACHMENTS.get(part_id, {}).get("rarity"),
                    "type": ATTACHMENTS.get(part_id, {}).get("type"),
                    "effect": ATTACHMENT_EFFECTS.get(row.get("effect", {}).get("id")),
                    "isLocked": row.get("isLocked", False),
                    "weaponUid": row.get("weaponUid"),
                    **dict(
                        AttachmentsData.map_attributes_calibrations(
                            AttachmentsData.decode_attributes(
                                int(row.get("attributes", 0))
                            ),
                            row.get("calibrations", []),
                        ),
                    ),
                }

    def to_csv(self) -> None:
        filename = (
            f"gfl2logger_attachments_{self.log_time.strftime('%Y%m%dT%H%M%SZ')}.csv"
        )
        cols = [
            "uid",
            "name",
            "rarity",
            "type",
            "effect",
            *["attr" + attr for attr in ATTRIBUTES_NAME_STRIPPED.values()],
            *["calib" + attr for attr in ATTRIBUTES_NAME_STRIPPED.values()],
            "isLocked",
            "weaponUid",
        ]
        data = self.to_dicts()

        try:
            with open(filename, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(data)
            logger.log(log.ALERT, f"Attachments data written to {filename}")
        except OSError as e:
            logger.error(f"Failed to write to {filename}, error={e}")
