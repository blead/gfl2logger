import multiprocessing
import os
import time
import unittest

from gfl2logger.gui import window
from gfl2logger.gui.command import Command, CommandType


@unittest.skipUnless(
    os.environ.get("GFL2LOGGER_GUI_TESTS") == "1",
    "opens a real window; set GFL2LOGGER_GUI_TESTS=1 to run",
)
class WindowProcessTests(unittest.TestCase):
    def test_window_process_applies_commands_and_exits_on_shutdown(self) -> None:
        from_gui: multiprocessing.Queue = multiprocessing.Queue()
        to_gui: multiprocessing.Queue = multiprocessing.Queue(maxsize=2048)
        process = multiprocessing.Process(
            target=window.draw_window,
            args=(from_gui, to_gui),
            daemon=True,
        )
        process.start()
        try:
            for index in range(300):
                to_gui.put(Command(CommandType.LOG, f"line {index}\nsecond row"))
            to_gui.put(Command(CommandType.OPTIONS, {"gfl2_weapons": False}))
            time.sleep(3)
            self.assertTrue(process.is_alive(), "window process exited early")

            to_gui.put(Command(CommandType.SHUTDOWN, None))
            process.join(20)

            self.assertEqual(process.exitcode, 0)
        finally:
            if process.is_alive():
                process.terminate()
                process.join(5)


if __name__ == "__main__":
    unittest.main()
