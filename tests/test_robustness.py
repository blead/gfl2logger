import asyncio
import csv
import queue
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from generated.guild_members_pb2 import GuildMembers
from gfl2logger.gfl2.data import DATA_TYPES
from gfl2logger.gfl2.data.base import BaseData
from gfl2logger.gfl2.data.formations import FormationsData
from gfl2logger.gfl2.data.guild_members import GuildMembersData
from gfl2logger.gfl2.data.weapons import WeaponsData
from gfl2logger.gfl2.logger import GFL2Logger
from gfl2logger.gfl2.parser import LOG_PREVIEW_BYTES, GFL2Parser, Payload, PayloadError
from gfl2logger.gui import manager as gui_manager
from gfl2logger.gui import window as gui_window
from gfl2logger.gui.command import Command, CommandType

TRACKED_TYPE = 65001
FAILING_TYPE = 65002


def encode_payload(payload_type: int, data: bytes) -> bytes:
    return payload_type.to_bytes(2, "little") + len(data).to_bytes(2, "little") + data


def encode_message(msg_id: int, *payloads: bytes) -> bytes:
    body = b"".join(payloads)
    return msg_id.to_bytes(3, "little") + len(body).to_bytes(2, "little") + body


class TrackedData(BaseData):
    exported: list[bytes] = []

    async def export(self) -> None:
        self.exported.append(b"".join(self.data))


class FailingData(BaseData):
    def __init__(self, b: bytes):
        raise RuntimeError("decoder exploded")


class ParserStreamTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        DATA_TYPES[TRACKED_TYPE] = TrackedData
        DATA_TYPES[FAILING_TYPE] = FailingData
        TrackedData.exported = []
        self.parser = GFL2Parser()

    async def asyncTearDown(self) -> None:
        self.parser.stop()
        await asyncio.gather(*self.parser._tasks)
        DATA_TYPES.pop(TRACKED_TYPE, None)
        DATA_TYPES.pop(FAILING_TYPE, None)

    async def finish(self) -> None:
        self.parser.stop()
        await asyncio.gather(*self.parser._tasks)

    async def test_header_split_across_tcp_chunks_is_retained(self) -> None:
        first = encode_message(7, encode_payload(TRACKED_TYPE, b"first"))
        second = encode_message(8, encode_payload(TRACKED_TYPE, b"second"))
        stream = first + second

        # The first chunk ends two bytes into the second message's header.
        await self.parser.on_message(stream[: len(first) + 2])
        await self.parser.on_message(stream[len(first) + 2 :])
        await self.finish()

        self.assertEqual(TrackedData.exported, [b"first", b"second"])

    async def test_stream_delivered_one_byte_at_a_time(self) -> None:
        stream = encode_message(
            7, encode_payload(TRACKED_TYPE, b"a")
        ) + encode_message(8, encode_payload(TRACKED_TYPE, b"b"))

        for index in range(len(stream)):
            await self.parser.on_message(stream[index : index + 1])
        await self.finish()

        self.assertEqual(TrackedData.exported, [b"a", b"b"])

    async def test_chunks_queued_before_stop_are_still_exported(self) -> None:
        await self.parser.on_message(
            encode_message(7, encode_payload(TRACKED_TYPE, b"last"))
        )
        # The flow closes before the parser tasks have had a chance to run.
        await self.finish()

        self.assertEqual(TrackedData.exported, [b"last"])

    async def test_messages_after_stop_are_ignored(self) -> None:
        await self.finish()
        await self.parser.on_message(
            encode_message(7, encode_payload(TRACKED_TYPE, b"late"))
        )

        self.assertEqual(TrackedData.exported, [])

    async def test_failing_payload_does_not_stop_the_consumer(self) -> None:
        with self.assertLogs("gfl2logger.gfl2.parser", level="ERROR"):
            await self.parser.on_message(
                encode_message(7, encode_payload(FAILING_TYPE, b"x"))
                + encode_message(8, encode_payload(TRACKED_TYPE, b"ok"))
            )
            await self.finish()

        self.assertEqual(TrackedData.exported, [b"ok"])

    def test_malformed_payload_error_does_not_dump_the_whole_message(self) -> None:
        truncated = bytearray(encode_payload(TRACKED_TYPE, b"x" * 4096)[:-1])

        with self.assertRaises(PayloadError) as raised:
            Payload(truncated)

        self.assertLess(len(str(raised.exception)), LOG_PREVIEW_BYTES * 2 + 200)


class TcpMessageRetentionTests(unittest.IsolatedAsyncioTestCase):
    async def test_forwarded_messages_are_not_retained_on_the_flow(self) -> None:
        received: list[bytes] = []

        async def on_message(content: bytes) -> None:
            received.append(content)

        class Flow:
            def __init__(self) -> None:
                self.messages: list = []

        addon = GFL2Logger()
        flow = Flow()
        addon.active_flows[flow] = SimpleNamespace(on_message=on_message)

        for index in range(3):
            flow.messages.append(
                SimpleNamespace(from_client=False, content=bytes([index]))
            )
            await addon.tcp_message(flow)
        flow.messages.append(SimpleNamespace(from_client=True, content=b"client"))
        await addon.tcp_message(flow)

        self.assertEqual(received, [b"\x00", b"\x01", b"\x02"])
        self.assertEqual(flow.messages, [])


class ExportTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        patcher = mock.patch.object(
            BaseData,
            "output_path",
            staticmethod(lambda filename: self.directory.joinpath(filename)),
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def files(self) -> list[str]:
        return sorted(path.name for path in self.directory.iterdir())

    def test_csv_is_published_whole_without_leftover_temporary_files(self) -> None:
        members = GuildMembers()
        member = members.members.add()
        member.uid = 42
        member.player.player_info.name = "Groza"
        data = GuildMembersData(members.SerializeToString())

        data.to_csv()

        (name,) = self.files()
        self.assertRegex(name, r"^gfl2logger_guildmembers_\d{8}T\d{6}Z\.csv$")
        with open(self.directory / name, encoding="utf-8", newline="") as output:
            rows = list(csv.DictReader(output))
        self.assertEqual([(row["uid"], row["name"]) for row in rows], [("42", "Groza")])

    def test_payloads_without_entries_export_an_empty_table(self) -> None:
        # MessageToDict omits empty repeated fields entirely.
        self.assertEqual(list(GuildMembersData(b"").to_dicts()), [])
        self.assertEqual(list(WeaponsData(b"").to_dicts()), [])
        self.assertEqual(list(FormationsData(b"").to_dicts()), [])

    def test_undecodable_payload_does_not_leave_a_partial_file(self) -> None:
        data = GuildMembersData(b"\xff\xff\xff")

        with self.assertRaises(Exception):
            data.to_csv()

        self.assertEqual(self.files(), [])

    def test_write_failure_is_reported_and_cleans_up(self) -> None:
        data = BaseData(b"")

        def fail(_output) -> None:
            raise OSError("disk full")

        with self.assertLogs("gfl2logger.gfl2.data.base", level="ERROR"):
            data._write_export(self.directory / "out.json", "Test", fail)

        self.assertEqual(self.files(), [])


class FakeWindow:
    def __init__(self) -> None:
        self.active = True
        self.logs: list[str] = []
        self.options: dict[str, bool] = {}
        self.destroyed = False
        self.scheduled = 0

    def rpc_write_log(self, message: str) -> None:
        self.logs.append(message)

    def rpc_set_options(self, options: dict[str, bool]) -> None:
        self.options.update(options)

    def destroy(self) -> None:
        self.destroyed = True

    def after(self, *_args) -> None:
        self.scheduled += 1


class GuiPumpTests(unittest.TestCase):
    def test_commands_are_applied_and_the_pump_is_rescheduled(self) -> None:
        window = FakeWindow()
        to_gui: queue.Queue = queue.Queue()
        to_gui.put(Command(CommandType.LOG, "hello"))
        to_gui.put(Command(CommandType.OPTIONS, {"gfl2_weapons": False}))

        gui_window.pump(window, to_gui)

        self.assertEqual(window.logs, ["hello"])
        self.assertEqual(window.options, {"gfl2_weapons": False})
        self.assertEqual(window.scheduled, 1)
        self.assertFalse(window.destroyed)

    def test_shutdown_destroys_the_window_and_stops_polling(self) -> None:
        window = FakeWindow()
        to_gui: queue.Queue = queue.Queue()
        to_gui.put(Command(CommandType.SHUTDOWN, None))
        to_gui.put(Command(CommandType.LOG, "after shutdown"))

        gui_window.pump(window, to_gui)

        self.assertTrue(window.destroyed)
        self.assertFalse(window.active)
        self.assertEqual(window.scheduled, 0)
        self.assertEqual(window.logs, [])

    def test_closing_the_window_notifies_the_proxy_and_closes_immediately(self) -> None:
        class ClosableWindow:
            def __init__(self) -> None:
                self.active = True
                self.from_gui: queue.Queue = queue.Queue()
                self.destroyed = 0

            def destroy(self) -> None:
                self.destroyed += 1

        closing = ClosableWindow()

        gui_window.TkWindow.quit(closing)
        gui_window.TkWindow.quit(closing)

        self.assertEqual(closing.from_gui.get_nowait().type, CommandType.SHUTDOWN)
        self.assertTrue(closing.from_gui.empty())
        self.assertEqual(closing.destroyed, 1)
        self.assertFalse(closing.active)

    def test_window_closes_itself_when_the_proxy_process_is_gone(self) -> None:
        window = FakeWindow()

        with mock.patch.object(gui_window, "parent_is_alive", return_value=False):
            gui_window.pump(window, queue.Queue())

        self.assertTrue(window.destroyed)
        self.assertEqual(window.scheduled, 0)


class GuiManagerTests(unittest.IsolatedAsyncioTestCase):
    def test_full_gui_queue_drops_instead_of_blocking(self) -> None:
        target: queue.Queue = queue.Queue(maxsize=1)

        self.assertTrue(
            gui_manager.send_nowait(target, Command(CommandType.LOG, "kept"))
        )
        self.assertFalse(
            gui_manager.send_nowait(target, Command(CommandType.LOG, "dropped"))
        )

    async def test_proxy_shuts_down_when_the_window_process_dies(self) -> None:
        class DyingProcess:
            def __init__(self) -> None:
                self.checks = 0

            def start(self) -> None:
                pass

            def is_alive(self) -> bool:
                self.checks += 1
                return self.checks < 3

        manager = gui_manager.GUIManager.__new__(gui_manager.GUIManager)
        manager.from_gui = queue.Queue()
        manager.subprocess = DyingProcess()
        manager.start_exit_watchdog = lambda process: None

        with (
            mock.patch.object(gui_manager, "GUI_POLL_SECONDS", 0.01),
            mock.patch.object(gui_manager, "ctx") as ctx,
        ):
            await asyncio.wait_for(manager.loop(), timeout=5)

        ctx.master.shutdown.assert_called_once()

    def test_process_exits_once_the_window_process_is_gone(self) -> None:
        events: list[object] = []
        window_process = object()

        gui_manager.exit_when_window_is_gone(
            window_process,
            grace=0,
            wait=lambda process: events.append(("waited for", process)),
            terminate=lambda code: events.append(("exit", code)),
        )

        self.assertEqual(events, [("waited for", window_process), ("exit", 0)])

    async def test_watchdog_is_armed_when_the_window_starts(self) -> None:
        class DeadProcess:
            def start(self) -> None:
                pass

            def is_alive(self) -> bool:
                return False

        manager = gui_manager.GUIManager.__new__(gui_manager.GUIManager)
        manager.from_gui = queue.Queue()
        manager.subprocess = DeadProcess()
        watched: list[object] = []
        manager.start_exit_watchdog = watched.append

        with mock.patch.object(gui_manager, "ctx"):
            await asyncio.wait_for(manager.loop(), timeout=5)

        self.assertEqual(watched, [manager.subprocess])

    async def test_window_starts_before_the_proxy_and_closes_after_it(self) -> None:
        events: list[str] = []

        class Gui:
            def start(self) -> None:
                events.append("window started")

            def close(self) -> None:
                events.append("window closed")

        async def run_proxy() -> None:
            # Stands in for mitmproxy's run(), which may sit in server set-up for a
            # long time before the running hook fires.
            events.append("proxy running")

        await gui_manager.run_with_window(Gui(), run_proxy)

        self.assertEqual(events, ["window started", "proxy running", "window closed"])

    async def test_window_is_closed_even_if_the_proxy_fails(self) -> None:
        events: list[str] = []

        class Gui:
            def start(self) -> None:
                events.append("window started")

            def close(self) -> None:
                events.append("window closed")

        async def run_proxy() -> None:
            raise RuntimeError("redirector failed")

        with self.assertRaises(RuntimeError):
            await gui_manager.run_with_window(Gui(), run_proxy)

        self.assertEqual(events, ["window started", "window closed"])

    async def test_window_is_started_only_once(self) -> None:
        manager = gui_manager.GUIManager.__new__(gui_manager.GUIManager)
        started: list[object] = []

        def create_task(coroutine):
            coroutine.close()
            started.append(coroutine)
            return object()

        with mock.patch.object(gui_manager.asyncio_utils, "create_task", create_task):
            manager.start()
            await manager.running()

        self.assertEqual(len(started), 1)

    async def test_failed_command_keeps_the_window_able_to_quit(self) -> None:
        class AliveProcess:
            def start(self) -> None:
                pass

            def is_alive(self) -> bool:
                return True

        manager = gui_manager.GUIManager.__new__(gui_manager.GUIManager)
        manager.from_gui = queue.Queue()
        manager.subprocess = AliveProcess()
        manager.start_exit_watchdog = lambda process: None
        manager.from_gui.put(Command(CommandType.SAVE_OPTIONS, None))
        manager.from_gui.put(Command(CommandType.SHUTDOWN, None))

        with (
            mock.patch.object(gui_manager, "ctx") as ctx,
            mock.patch.object(
                gui_manager.optmanager, "save", side_effect=OSError("read-only")
            ),
            self.assertLogs("gfl2logger.gui.manager", level="ERROR"),
        ):
            manager.optmanager_wrapper = object()
            await asyncio.wait_for(manager.loop(), timeout=5)

        ctx.master.shutdown.assert_called_once()


class BuildWorkflowOrderTests(unittest.TestCase):
    def test_protobuf_modules_are_generated_before_the_tests_run(self) -> None:
        workflow = Path(".github/workflows/build.yml").read_text(encoding="utf-8")

        self.assertLess(
            workflow.index("pdm run protoc"),
            workflow.index("unittest discover"),
        )


if __name__ == "__main__":
    unittest.main()
