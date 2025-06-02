import functools
import multiprocessing
import signal
import threading
import tkinter
from ctypes import windll
from idlelib import tooltip
from tkinter import ttk

from embed import ICON_PNG
from gfl2logger.gfl2 import data
from gfl2logger.gui.command import Command, CommandType
from gfl2logger.gui.log_window import LogWindow

logger = multiprocessing.get_logger()


class TkWindow(tkinter.Tk):
    def __init__(self, from_gui: "multiprocessing.Queue[Command]"):
        self.from_gui = from_gui
        self.active = True
        self.options: dict[str, tkinter.Variable] = {}

        try:
            windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

        super().__init__()
        self.title("gfl2logger")
        self.minsize(600, 240)

        if ICON_PNG is not None:
            self.iconphoto(True, tkinter.PhotoImage(data=ICON_PNG))

        # exit flow: (tk) self.quit -> (tk) from_gui:SHUTDOWN
        #   -> (main) master.shutdown -> (main) manager.done -> (main) to_gui:SHUTDOWN
        #   -> (tk thread) <<Destroy>> -> (tk) self.destroy
        self.protocol("WM_DELETE_WINDOW", self.quit)
        self.bind("<<Destroy>>", self.destroy)

        opt_frame = ttk.Frame(self, padding=10)
        opt_frame.pack(side="left", fill="y")
        for opt in data.get_options():
            if "name" not in opt:
                continue
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
        self.withdraw()
        self.from_gui.put(Command(CommandType.SHUTDOWN, None))

    def destroy(self, *_) -> None:
        super().destroy()


def loop(window: TkWindow, to_gui: multiprocessing.Queue) -> None:
    while window.active:
        cmd = to_gui.get()
        match cmd.type:
            case CommandType.LOG:
                window.rpc_write_log(cmd.content)
            case CommandType.OPTIONS:
                window.rpc_set_options(cmd.content)
            case CommandType.SHUTDOWN:
                window.active = False
                window.event_generate("<<Destroy>>")
                break
            case _:
                logger.warning(
                    f"Unrecognized command to gui, cmd.type={cmd.type}, cmd.content={cmd.content}"
                )


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

    t = threading.Thread(target=loop, args=(window, to_gui), daemon=True)
    t.start()
    window.mainloop()
    t.join(timeout=3)
