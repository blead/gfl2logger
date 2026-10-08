import ast
import asyncio
import unittest
from pathlib import Path

from gfl2logger.gui.command import CommandType
from gfl2logger.gui.manager import GUIManager


class FakeQueue:
    def __init__(self) -> None:
        self.items = []

    def put(self, item) -> None:
        self.items.append(item)

    def put_nowait(self, item) -> None:
        self.items.append(item)

    def cancel_join_thread(self) -> None:
        self.join_cancelled = True


class FakeProcess:
    def __init__(self) -> None:
        self.join_timeout = None
        self.terminated = False

    def join(self, timeout=None) -> None:
        self.join_timeout = timeout

    def terminate(self) -> None:
        self.terminated = True


class FakeLogHandler:
    def __init__(self) -> None:
        self.uninstalled = False

    def uninstall(self) -> None:
        self.uninstalled = True


class EntrypointTests(unittest.TestCase):
    def test_proxy_master_is_not_imported_during_frozen_worker_bootstrap(self) -> None:
        tree = ast.parse(Path("main.py").read_text(encoding="utf-8"))

        top_level_imports = [
            node
            for node in tree.body
            if isinstance(node, (ast.Import, ast.ImportFrom))
        ]
        self.assertFalse(
            any(
                isinstance(node, ast.ImportFrom)
                and node.module == "gfl2logger.proxy.master"
                for node in top_level_imports
            )
        )

        run_function = next(
            node
            for node in tree.body
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "run"
        )
        self.assertTrue(
            any(
                isinstance(node, ast.ImportFrom)
                and node.module == "gfl2logger.proxy.master"
                for node in run_function.body
            )
        )

    def test_gui_done_unblocks_both_sides_of_the_queue(self) -> None:
        manager = GUIManager.__new__(GUIManager)
        manager.to_gui = FakeQueue()
        manager.from_gui = FakeQueue()
        manager.subprocess = FakeProcess()
        manager.log_handler = FakeLogHandler()

        asyncio.run(manager.done())

        self.assertEqual(manager.to_gui.items[0].type, CommandType.SHUTDOWN)
        self.assertEqual(manager.from_gui.items[0].type, CommandType.SHUTDOWN)
        self.assertEqual(manager.subprocess.join_timeout, 5)
        self.assertTrue(manager.subprocess.terminated)
        self.assertTrue(manager.log_handler.uninstalled)


if __name__ == "__main__":
    unittest.main()
