import csv
import json
import logging
import os
import uuid
from collections.abc import Callable, Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TextIO

from mitmproxy import addonmanager, ctx, log

logger = logging.getLogger(__name__)


class ReassemblyLimitError(ValueError):
    """Raised when a payload sequence exceeds its bounded reassembly budget."""


class BaseData:
    OPTIONS: list[dict[str, Any]] = []
    MAX_REASSEMBLY_BYTES = 8 * 1024 * 1024
    MAX_REASSEMBLY_FRAGMENTS = 256

    @classmethod
    def add_options(cls, loader: addonmanager.Loader) -> None:
        for opt in cls.OPTIONS:
            if "name" in opt:
                loader.add_option(
                    name=opt["name"],
                    typespec=opt.get("typespec", bool),
                    default=opt.get("default", True),
                    help=opt.get("help", ""),
                )

    def __init__(self, b: bytes):
        if len(b) > self.MAX_REASSEMBLY_BYTES:
            raise ReassemblyLimitError(
                f"initial payload exceeds {self.MAX_REASSEMBLY_BYTES} bytes"
            )
        self.data = [b]
        self.reassembled_bytes = len(b)
        self.log_time = datetime.now(timezone.utc)

    def append(self, b: bytes) -> None:
        next_size = self.reassembled_bytes + len(b)
        if len(self.data) >= self.MAX_REASSEMBLY_FRAGMENTS:
            raise ReassemblyLimitError(
                f"payload sequence exceeds {self.MAX_REASSEMBLY_FRAGMENTS} fragments"
            )
        if next_size > self.MAX_REASSEMBLY_BYTES:
            raise ReassemblyLimitError(
                f"payload sequence exceeds {self.MAX_REASSEMBLY_BYTES} bytes"
            )
        self.data.append(b)
        self.reassembled_bytes = next_size

    @staticmethod
    def output_path(filename: str) -> Path:
        return Path(ctx.options.confdir).joinpath(filename)

    def export_path(self, kind: str, extension: str) -> Path:
        timestamp = self.log_time.strftime("%Y%m%dT%H%M%SZ")
        return self.output_path(f"gfl2logger_{kind}_{timestamp}.{extension}")

    def write_csv(
        self,
        kind: str,
        label: str,
        columns: list[str],
        rows: Iterable[dict[str, Any]],
    ) -> None:
        # Decode every row before the file exists, so a malformed payload fails the
        # export instead of leaving a truncated file that looks complete.
        materialized = list(rows)

        def write(output: TextIO) -> None:
            writer = csv.DictWriter(output, fieldnames=columns, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(materialized)

        self._write_export(self.export_path(kind, "csv"), label, write, newline="")

    def write_json(self, kind: str, label: str, content: Any) -> None:
        def write(output: TextIO) -> None:
            json.dump(content, output, ensure_ascii=False, indent=2)

        self._write_export(self.export_path(kind, "json"), label, write)

    @staticmethod
    def _write_export(
        filename: Path,
        label: str,
        write: Callable[[TextIO], None],
        *,
        newline: str | None = None,
    ) -> None:
        # Write next to the destination and rename, so tools watching the folder never
        # pick up a half-written export.
        temporary = filename.with_name(f".{filename.name}.{uuid.uuid4().hex}.tmp")
        try:
            try:
                with open(temporary, "w", encoding="utf-8", newline=newline) as output:
                    write(output)
                os.replace(temporary, filename)
            finally:
                temporary.unlink(missing_ok=True)
        except OSError as error:
            logger.error(f"Failed to write to {filename}, error={error}")
            return
        logger.log(log.ALERT, f"{label} data written to {filename}")

    async def export(self) -> None:
        for b in self.data:
            logger.debug(b.hex())
