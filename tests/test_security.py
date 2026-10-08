import asyncio
import csv
import io
import unittest
from pathlib import Path

from generated.guild_members_pb2 import GuildMembers
from gfl2logger.gfl2.data import DATA_TYPES
from gfl2logger.gfl2.data.base import BaseData, ReassemblyLimitError
from gfl2logger.gfl2.data.guild_members import GuildMembersData
from gfl2logger.gfl2.parser import (
    MAX_INPUT_CHUNK_BYTES,
    GFL2Parser,
    Payload,
)
from gfl2logger.utils.csv_safety import spreadsheet_safe


TEST_PAYLOAD_TYPE = 65000


def make_payload(data: bytes = b"x", *, msg_id: int = 0) -> Payload:
    encoded = bytearray(
        TEST_PAYLOAD_TYPE.to_bytes(2, "little")
        + len(data).to_bytes(2, "little")
        + data
    )
    payload = Payload(encoded, msg_id=msg_id)
    payload.end_of_msg = True
    return payload


class LimitedTrackingData(BaseData):
    MAX_REASSEMBLY_BYTES = 16
    MAX_REASSEMBLY_FRAGMENTS = 2
    instances: list["LimitedTrackingData"] = []
    exports: list["LimitedTrackingData"] = []

    def __init__(self, b: bytes):
        super().__init__(b)
        self.instances.append(self)

    async def export(self) -> None:
        self.exports.append(self)


class CsvSafetyTests(unittest.TestCase):
    def test_formula_prefixes_are_neutralized(self) -> None:
        for prefix in ("=", "+", "-", "@", "\t", "\r"):
            with self.subTest(prefix=prefix):
                self.assertEqual(
                    spreadsheet_safe(prefix + "payload"),
                    "'" + prefix + "payload",
                )

        self.assertEqual(spreadsheet_safe("ordinary name"), "ordinary name")
        self.assertEqual(spreadsheet_safe(42), 42)

    def test_guild_member_formula_name_is_safe_in_csv(self) -> None:
        members = GuildMembers()
        member = members.members.add()
        member.uid = 42
        member.player.player_info.name = '=WEBSERVICE("https://example.invalid")'
        member.player.player_info.level = 9

        row = next(GuildMembersData(members.SerializeToString()).to_dicts())
        output = io.StringIO(newline="")
        writer = csv.DictWriter(output, fieldnames=row)
        writer.writeheader()
        writer.writerow(row)

        decoded = next(csv.DictReader(io.StringIO(output.getvalue())))
        self.assertEqual(
            decoded["name"],
            "'=WEBSERVICE(\"https://example.invalid\")",
        )


class ParserResourceLimitTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.original_data_type = DATA_TYPES.get(TEST_PAYLOAD_TYPE)
        DATA_TYPES[TEST_PAYLOAD_TYPE] = LimitedTrackingData
        LimitedTrackingData.instances = []
        LimitedTrackingData.exports = []

    async def asyncTearDown(self) -> None:
        if self.original_data_type is None:
            DATA_TYPES.pop(TEST_PAYLOAD_TYPE, None)
        else:
            DATA_TYPES[TEST_PAYLOAD_TYPE] = self.original_data_type

    async def stop_parser(self, parser: GFL2Parser) -> None:
        parser.stop()
        await asyncio.gather(*parser._tasks)

    async def test_zero_id_sequence_is_dropped_at_fragment_limit(self) -> None:
        parser = GFL2Parser()
        try:
            await parser._process_payload(make_payload())
            await parser._process_payload(make_payload())
            await parser._process_payload(make_payload())

            self.assertIsNone(parser._pending_data)
            self.assertEqual(len(LimitedTrackingData.instances), 1)
            self.assertEqual(len(LimitedTrackingData.instances[0].data), 2)
            self.assertEqual(LimitedTrackingData.exports, [])
        finally:
            await self.stop_parser(parser)

    async def test_zero_id_sequence_is_dropped_after_timeout(self) -> None:
        parser = GFL2Parser(reassembly_timeout=0.01)
        try:
            await parser.payload_queue.put(make_payload())
            await asyncio.sleep(0.05)

            self.assertIsNone(parser._pending_data)
            self.assertEqual(LimitedTrackingData.exports, [])
        finally:
            await self.stop_parser(parser)

    async def test_reassembly_byte_budget_is_enforced(self) -> None:
        data = LimitedTrackingData(b"x" * 12)

        with self.assertRaises(ReassemblyLimitError):
            data.append(b"y" * 5)

    async def test_queues_are_bounded_and_oversized_chunks_are_rejected(self) -> None:
        parser = GFL2Parser()
        try:
            self.assertGreater(parser.msg_queue.maxsize, 0)
            self.assertGreater(parser.payload_queue.maxsize, 0)

            await parser.on_message(b"x" * (MAX_INPUT_CHUNK_BYTES + 1))
            self.assertTrue(parser.msg_queue.empty())
        finally:
            await self.stop_parser(parser)


class ReleaseWorkflowTests(unittest.TestCase):
    def test_release_workflow_is_tag_only_and_does_not_overwrite_assets(self) -> None:
        workflow = Path(".github/workflows/release.yml").read_text(encoding="utf-8")

        self.assertNotIn("branches:", workflow)
        self.assertNotIn("github.event.head_commit.message", workflow)
        self.assertIn('tags:\n      - "v*.*.*"', workflow)
        self.assertIn("overwrite_files: false", workflow)
        self.assertIn("${GITHUB_REF_NAME}", workflow)


if __name__ == "__main__":
    unittest.main()
