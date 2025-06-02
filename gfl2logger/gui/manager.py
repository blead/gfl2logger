import asyncio
import logging
import multiprocessing
from pathlib import Path

from mitmproxy import ctx, log, optmanager

from gfl2logger.gui import window
from gfl2logger.gui.command import Command, CommandType
from gfl2logger.utils import asyncio_utils
from gfl2logger.utils.optmanager_wrapper import GFL2OptManagerWrapper

logger = logging.getLogger(__name__)


class GUIManager:
    def __init__(self):
        self.from_gui: "multiprocessing.Queue[Command]" = multiprocessing.Queue()
        self.to_gui: "multiprocessing.Queue[Command]" = multiprocessing.Queue()
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
        while self.subprocess.is_alive():
            cmd = await asyncio.to_thread(self.from_gui.get, True)
            match cmd.type:
                case CommandType.OPTIONS:
                    for opt in cmd.content:
                        setattr(ctx.options, opt, cmd.content[opt])
                case CommandType.SAVE_OPTIONS:
                    filename = "gfl2logger.config.yaml"
                    optmanager.save(
                        self.optmanager_wrapper,
                        Path(ctx.options.confdir).joinpath(filename),
                        defaults=True,
                    )
                    logger.log(log.ALERT, f"Configurations saved to {filename}")
                case CommandType.SHUTDOWN:
                    break
                case _:
                    logger.warning(
                        f"Unrecognized command from gui, cmd.type={cmd.type}, cmd.content={cmd.content}"
                    )
        ctx.master.shutdown()

    def configure(self, updated: set[str]) -> None:
        self.to_gui.put(
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

    async def running(self) -> None:
        asyncio_utils.create_task(self.loop())

    async def done(self) -> None:
        self.to_gui.put(Command(CommandType.SHUTDOWN, None))
        self.subprocess.join(timeout=5)
        self.subprocess.terminate()
        self.log_handler.uninstall()


class GuiLogHandler(log.MitmLogHandler):
    def __init__(self, to_gui: "multiprocessing.Queue[Command]"):
        super().__init__()
        self.to_gui = to_gui
        self.formatter = log.MitmFormatter(False)

    def emit(self, record: logging.LogRecord):
        self.to_gui.put(Command(CommandType.LOG, self.format(record)))
