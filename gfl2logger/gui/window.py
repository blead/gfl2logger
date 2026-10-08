import functools
import multiprocessing
import queue
import signal
import sys
import tkinter
import ctypes
from idlelib import tooltip
from tkinter import ttk

from embed import ICON_PNG
from gfl2logger.gfl2 import data
from gfl2logger.gui.command import Command, CommandType
from gfl2logger.gui.log_window import LogWindow

logger = multiprocessing.get_logger()

POLL_INTERVAL_MS = 50
MAX_COMMANDS_PER_POLL = 100


class TkWindow(tkinter.Tk):
    def __init__(self, from_gui: "multiprocessing.Queue[Command]"):
        self.from_gui = from_gui
        self.active = True
        self.options: dict[str, tkinter.Variable] = {}

        if windll := getattr(ctypes, "windll", None):
            try:
                windll.shcore.SetProcessDpiAwareness(1)
            except Exception:
                pass

        super().__init__()
        self.title("gfl2logger")
        self.minsize(600, 240)

        if ICON_PNG is not None:
            self.iconphoto(True, tkinter.PhotoImage(data=ICON_PNG))

        # Closing the window ends the program: quit() tells the proxy process and then
        # closes at once without waiting for an answer. The proxy shuts down on that
        # message, or on noticing this process is gone, and force-exits if that stalls.
        # A shutdown started by the proxy arrives through pump() as SHUTDOWN instead.
        self.protocol("WM_DELETE_WINDOW", self.quit)
        if sys.platform == "darwin":
            # Cmd+Q and the Dock's Quit make Tk exit on the spot by default, which skips
            # the shutdown exchange with the proxy process. Route them through quit().
            self.createcommand("::tk::mac::Quit", self.quit)

        opt_frame = ttk.Frame(self, padding=10)
        opt_frame.pack(side="left", fill="y")
        style = ttk.Style(self)
        style.configure("OptionGroup.TLabel", foreground="dim gray")

        current_category = None
        for opt in data.get_options():
            if "name" not in opt:
                continue

            category = opt.get("category", "Options")
            if category != current_category:
                header = ttk.Frame(opt_frame)
                header.pack(
                    fill="x",
                    pady=(0 if current_category is None else 10, 4),
                )
                header.columnconfigure(0, weight=1)
                header.columnconfigure(2, weight=1)
                ttk.Separator(header).grid(row=0, column=0, sticky="ew")
                ttk.Label(
                    header,
                    text=category,
                    anchor="center",
                    style="OptionGroup.TLabel",
                ).grid(row=0, column=1, padx=7)
                ttk.Separator(header).grid(row=0, column=2, sticky="ew")
                current_category = category

            match opt.get("default"):
                case bool():
                    self.options[opt["name"]] = tkinter.BooleanVar(
                        self, name=opt["name"], value=opt.get("default", True)
                    )
                    cb = ttk.Checkbutton(
                        opt_frame,
                        text=opt.get("label", opt["name"]),
                        variable=self.options[opt["name"]],
                        onvalue=True,
                        offvalue=False,
                        command=functools.partial(self.cmd_change_options, opt["name"]),
                    )
                    cb.pack(anchor="w")
                    if "help" in opt:
                        tooltip.Hovertip(cb, opt["help"], hover_delay=500)
                case _:
                    pass
        ttk.Button(opt_frame, command=self.cmd_save_options, text="Save config").pack(
            side="bottom", anchor="e"
        )

        self.log_win = LogWindow(self, width=50, height=10, wrap="word")
        self.log_win.pack(fill="both", expand=True)

    def cmd_change_options(self, opt: str) -> None:
        self.from_gui.put(Command(CommandType.OPTIONS, {opt: self.options[opt].get()}))

    def cmd_save_options(self) -> None:
        self.from_gui.put(Command(CommandType.SAVE_OPTIONS, None))

    def rpc_write_log(self, msg: str) -> None:
        self.log_win.write(msg)

    def rpc_set_options(self, options: dict[str, bool]) -> None:
        for opt in options:
            if opt in self.options:
                self.options[opt].set(options[opt])

    def quit(self) -> None:
        if not self.active:
            return
        self.active = False
        self.from_gui.put(Command(CommandType.SHUTDOWN, None))
        self.destroy()

    def destroy(self, *_) -> None:
        super().destroy()


def parent_is_alive() -> bool:
    parent = multiprocessing.parent_process()
    return parent is None or parent.is_alive()


def pump(window: TkWindow, to_gui: "multiprocessing.Queue[Command]") -> None:
    """Apply queued commands on the Tk main thread.

    Tk must only be driven from the thread that created it, which matters most on
    macOS, so the queue is polled from a timer instead of a reader thread.
    """
    if not parent_is_alive():
        # The proxy is gone, so nothing will ever answer SHUTDOWN: closing the window
        # would only hide it and leave this process behind.
        window.active = False
        window.destroy()
        return

    for _ in range(MAX_COMMANDS_PER_POLL):
        try:
            cmd = to_gui.get_nowait()
        except queue.Empty:
            break
        match cmd.type:
            case CommandType.LOG:
                window.rpc_write_log(cmd.content)
            case CommandType.OPTIONS:
                window.rpc_set_options(cmd.content)
            case CommandType.SHUTDOWN:
                window.active = False
                window.destroy()
                return
            case _:
                logger.warning(
                    f"Unrecognized command to gui, cmd.type={cmd.type}, cmd.content={cmd.content}"
                )

    window.after(POLL_INTERVAL_MS, pump, window, to_gui)


def draw_window(
    from_gui: "multiprocessing.Queue[Command]",
    to_gui: "multiprocessing.Queue[Command]",
) -> None:
    window = TkWindow(from_gui)

    def _sigint(*_):
        window.quit()

    def _sigterm(*_):
        window.quit()

    signal.signal(signal.SIGINT, _sigint)
    signal.signal(signal.SIGTERM, _sigterm)

    window.after(0, pump, window, to_gui)
    window.mainloop()
