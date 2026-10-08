import asyncio
import logging
import multiprocessing
import multiprocessing.connection
import os
import queue
import threading
import time
from collections.abc import Awaitable, Callable
from pathlib import Path

from mitmproxy import ctx, log, optmanager

from gfl2logger.gui import window
from gfl2logger.gui.command import Command, CommandType
from gfl2logger.utils import asyncio_utils
from gfl2logger.utils.optmanager_wrapper import GFL2OptManagerWrapper
from gfl2logger.utils.paths import CONFIG_FILENAME

logger = logging.getLogger(__name__)

GUI_POLL_SECONDS = 1.0
MAX_PENDING_GUI_COMMANDS = 2048
EXIT_GRACE_SECONDS = 3.0


def wait_for_exit(process: multiprocessing.Process) -> None:
    # Waiting on the sentinel does not reap the process, so it cannot race with the
    # join() and is_alive() calls made from the event loop thread.
    multiprocessing.connection.wait([process.sentinel])


def exit_when_window_is_gone(
    process: multiprocessing.Process,
    *,
    grace: float = EXIT_GRACE_SECONDS,
    wait: Callable[[multiprocessing.Process], None] = wait_for_exit,
    terminate: Callable[[int], None] = os._exit,
) -> None:
    """End this process shortly after the window process ends, whatever the reason.

    The program must never keep capturing without a window. Normal shutdown finishes
    well inside the grace period; this is the backstop for a shutdown that hangs, a
    proxy still stuck in start-up, or a command loop that has stopped.
    """
    wait(process)
    time.sleep(grace)
    terminate(0)


def start_exit_watchdog(process: multiprocessing.Process) -> threading.Thread:
    # A plain thread rather than a task: it has to work when the event loop is blocked.
    watchdog = threading.Thread(
        target=exit_when_window_is_gone,
        args=(process,),
        name="WindowExitWatchdog",
        daemon=True,
    )
    watchdog.start()
    return watchdog


def send_nowait(target: "multiprocessing.Queue[Command]", command: Command) -> bool:
    """Queue a command for the window without ever blocking the proxy on a stuck GUI."""
    try:
        target.put_nowait(command)
    except queue.Full:
        return False
    return True


async def run_with_window(
    gui: "GUIManager", run: Callable[[], Awaitable[None]]
) -> None:
    """Show the window before the proxy starts and take it down when the proxy ends.

    mitmproxy brings its proxy servers up before it fires the running hook, and the
    local redirector can take a while or stall there, for example while macOS waits for
    the Network Extension to be approved. Tying the window to that hook left the app
    running with nothing on screen, so the window is started first instead.
    """
    gui.start()
    try:
        await run()
    finally:
        gui.close()


class GUIManager:
    _loop_task: asyncio.Task | None = None
    _closed = False
    start_exit_watchdog = staticmethod(start_exit_watchdog)

    def __init__(self):
        self.from_gui: "multiprocessing.Queue[Command]" = multiprocessing.Queue()
        # Bounded so a window that stops reading cannot make log records pile up in memory.
        self.to_gui: "multiprocessing.Queue[Command]" = multiprocessing.Queue(
            maxsize=MAX_PENDING_GUI_COMMANDS
        )
        self.subprocess = multiprocessing.Process(
            target=window.draw_window,
            args=(self.from_gui, self.to_gui),
            name="TkWindow",
            daemon=True,
        )
        self.log_handler = GuiLogHandler(self.to_gui)
        self.log_handler.install()

    async def loop(self) -> None:
        self.subprocess.start()
        self.start_exit_watchdog(self.subprocess)
        try:
            # Wake up periodically: if the window process dies without sending SHUTDOWN, a
            # plain blocking read would leave the proxy capturing with no window to quit it.
            while self.subprocess.is_alive():
                try:
                    cmd = await asyncio.to_thread(
                        self.from_gui.get, True, GUI_POLL_SECONDS
                    )
                except queue.Empty:
                    continue
                if cmd.type == CommandType.SHUTDOWN:
                    break
                try:
                    self.handle_command(cmd)
                except Exception as error:
                    # A failed command must not end this loop, or the window could no
                    # longer shut the app down.
                    logger.error(f"Unable to apply {cmd.type.name}, error={error}")
        finally:
            ctx.master.shutdown()

    def handle_command(self, cmd: Command) -> None:
        match cmd.type:
            case CommandType.OPTIONS:
                for opt in cmd.content:
                    setattr(ctx.options, opt, cmd.content[opt])
            case CommandType.SAVE_OPTIONS:
                optmanager.save(
                    self.optmanager_wrapper,
                    Path(ctx.options.confdir).joinpath(CONFIG_FILENAME),
                    defaults=True,
                )
                logger.log(log.ALERT, f"Configurations saved to {CONFIG_FILENAME}")
            case _:
                logger.warning(
                    f"Unrecognized command from gui, cmd.type={cmd.type}, cmd.content={cmd.content}"
                )

    def configure(self, updated: set[str]) -> None:
        send_nowait(
            self.to_gui,
            Command(
                CommandType.OPTIONS,
                {
                    opt: getattr(ctx.options, opt)
                    for opt in updated
                    if opt.startswith("gfl2_")
                },
            ),
        )

    def load(self, _) -> None:
        self.optmanager_wrapper = GFL2OptManagerWrapper(ctx.options)

    def start(self) -> None:
        """Start the window process and the command loop once."""
        if self._loop_task is None:
            self._loop_task = asyncio_utils.create_task(self.loop())

    async def running(self) -> None:
        self.start()

    def close(self) -> None:
        """Ask the window to close and stop waiting for it. Safe to call twice."""
        if self._closed:
            return
        self._closed = True
        send_nowait(self.to_gui, Command(CommandType.SHUTDOWN, None))
        # Signal-driven shutdown can reach here while loop() is blocked in
        # from_gui.get().  Wake that read so asyncio can close its worker thread
        # and the frozen app can exit cleanly.
        self.from_gui.put(Command(CommandType.SHUTDOWN, None))
        self.subprocess.join(timeout=5)
        self.subprocess.terminate()
        self.log_handler.uninstall()
        # Nothing reads this queue any more; do not let undelivered log records hold
        # up interpreter exit.
        self.to_gui.cancel_join_thread()

    async def done(self) -> None:
        self.close()


class GuiLogHandler(log.MitmLogHandler):
    def __init__(self, to_gui: "multiprocessing.Queue[Command]"):
        super().__init__()
        self.to_gui = to_gui
        self.formatter = log.MitmFormatter(False)

    def emit(self, record: logging.LogRecord):
        # Dropping a log line is better than blocking the capture path on the window.
        send_nowait(self.to_gui, Command(CommandType.LOG, self.format(record)))
