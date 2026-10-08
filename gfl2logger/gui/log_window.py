from tkinter.scrolledtext import ScrolledText


class LogWindow(ScrolledText):
    def __init__(self, master=None, maxlines=200, **kw):
        self.maxlines = maxlines
        super().__init__(master, **kw)
        self.configure(state="disabled")

    def write(self, msg) -> None:
        self.configure(state="normal")
        if self.index("end-1c") != "1.0":
            self.insert("end", "\n")
        self.insert("end", msg)
        # One record can span several lines, so trim by the real overflow.
        excess = int(self.index("end-1c").split(".")[0]) - self.maxlines
        if excess > 0:
            self.delete("1.0", f"{excess + 1}.0")
        self.configure(state="disabled")
        self.see("end")
