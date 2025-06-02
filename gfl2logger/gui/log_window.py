from tkinter.scrolledtext import ScrolledText


class LogWindow(ScrolledText):
    def __init__(self, master=None, maxlines=200, **kw):
        self.maxlines = maxlines
        super().__init__(master, **kw)
        self.configure(state="disabled")

    def write(self, msg) -> None:
        lines = int(self.index("end - 1 line").split(".")[0])
        self.configure(state="normal")
        if lines > self.maxlines:
            self.delete(1.0, 2.0)
        if self.index("end-1c") != "1.0":
            self.insert("end", "\n")
        self.insert("end", msg)
        self.configure(state="disabled")
        self.see("end")
