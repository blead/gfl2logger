from collections.abc import Generator
from typing import Any

from mitmproxy import addonmanager

from gfl2logger.gfl2.data.attachments import AttachmentsData
from gfl2logger.gfl2.data.base import BaseData
from gfl2logger.gfl2.data.common_keys import CommonKeysData
from gfl2logger.gfl2.data.formations import FormationsData
from gfl2logger.gfl2.data.guild_members import GuildMembersData
from gfl2logger.gfl2.data.weapons import WeaponsData

DATA_TYPES: dict[int, type[BaseData]] = {
    11021: WeaponsData,
    11061: AttachmentsData,
    11138: CommonKeysData,
    21917: GuildMembersData,
    23201: FormationsData,
}


def get_options() -> Generator[dict[str, Any]]:
    for d in DATA_TYPES.values():
        for o in d.OPTIONS:
            yield o


def add_options(loader: addonmanager.Loader) -> None:
    for DataClass in DATA_TYPES.values():
        DataClass.add_options(loader)
