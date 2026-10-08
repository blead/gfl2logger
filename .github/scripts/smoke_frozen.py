"""Start the packaged app, check that it stays up without multiplying, then close it.

Used by CI. On Windows the window is asked to close the way its close button does; on
macOS the window process is killed outright, like a crash. Either way every process has
to be gone shortly afterwards: the program must never keep running without a window.
"""

import json
import os
import signal
import subprocess
import sys
import tempfile
import time

STARTUP_SECONDS = 25
SHUTDOWN_SECONDS = 30
# The proxy, the window process and their launcher/helper processes. A frozen build that
# re-launches itself during multiprocessing start-up blows far past this.
MAX_PROCESSES = 8
WINDOWS = sys.platform == "win32"
WINDOW_PROCESS_MARK = "--multiprocessing-fork"


def processes(executable: str) -> list[dict]:
    """Return pid, parent pid and command line of every running app process."""
    if WINDOWS:
        listing = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-CimInstance Win32_Process -Filter \"name='gfl2logger.exe'\" | "
                "Select-Object ProcessId,ParentProcessId,CommandLine | ConvertTo-Json",
            ],
            capture_output=True,
            text=True,
        ).stdout.strip()
        if not listing:
            return []
        found = json.loads(listing)
        found = [found] if isinstance(found, dict) else found
        return [
            {
                "pid": item["ProcessId"],
                "parent": item["ParentProcessId"],
                "command": item["CommandLine"] or "",
            }
            for item in found
        ]

    listing = subprocess.run(
        ["ps", "-axo", "pid=,ppid=,command="], capture_output=True, text=True
    ).stdout
    found = []
    for line in listing.splitlines():
        pid, parent, command = line.split(None, 2)
        # Match the program itself, not tools that merely mention its path.
        if command.startswith(executable):
            found.append({"pid": int(pid), "parent": int(parent), "command": command})
    return found


def describe(found: list[dict]) -> None:
    for item in found:
        print(f"  pid={item['pid']} parent={item['parent']} {item['command']}")


def window_processes(found: list[dict]) -> list[dict]:
    # The window lives in the multiprocessing child.
    return [item for item in found if WINDOW_PROCESS_MARK in item["command"]]


def force_stop(process: subprocess.Popen, executable: str) -> None:
    if WINDOWS:
        subprocess.run(
            ["taskkill", "/F", "/T", "/IM", "gfl2logger.exe"], capture_output=True
        )
    else:
        for item in processes(executable):
            try:
                os.kill(item["pid"], signal.SIGKILL)
            except ProcessLookupError:
                pass
    process.wait(timeout=30)


def close_window(found: list[dict]) -> None:
    for item in window_processes(found):
        if WINDOWS:
            # Without /F, taskkill posts WM_CLOSE, which is what the close button does.
            result = subprocess.run(
                ["taskkill", "/PID", str(item["pid"])], capture_output=True, text=True
            )
            print(f"close request to pid={item['pid']}: {result.stdout.strip()}")
        else:
            os.kill(item["pid"], signal.SIGKILL)
            print(f"killed window process pid={item['pid']}")


def diagnose_windows() -> None:
    report = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            "Get-Process gfl2logger -ErrorAction SilentlyContinue | "
            "Select-Object Id,MainWindowTitle,Responding,StartTime | Format-List; "
            "Get-CimInstance Win32_Process | "
            "Where-Object { $_.Name -match 'redirector|divert' } | "
            "Select-Object ProcessId,ParentProcessId,Name,ExecutablePath | Format-List",
        ],
        capture_output=True,
        text=True,
    )
    print(report.stdout.strip() or report.stderr.strip())


def main(executable: str) -> int:
    executable = os.path.abspath(executable)
    # Windows builds write exports and settings to the working directory.
    workdir = tempfile.mkdtemp(prefix="gfl2logger-smoke-")
    process = subprocess.Popen([executable], cwd=workdir)

    time.sleep(STARTUP_SECONDS)
    started = processes(executable)
    print(f"processes after {STARTUP_SECONDS}s: {len(started)}")
    describe(started)
    if process.poll() is not None:
        print(f"FAIL: exited during start-up with code {process.returncode}")
        return 1
    if not 2 <= len(started) <= MAX_PROCESSES:
        print(f"FAIL: expected 2..{MAX_PROCESSES} processes")
        force_stop(process, executable)
        return 1
    if not window_processes(started):
        print("FAIL: the window process is not running")
        force_stop(process, executable)
        return 1

    close_window(started)
    closed_at = time.monotonic()
    deadline = closed_at + SHUTDOWN_SECONDS
    while time.monotonic() < deadline and processes(executable):
        time.sleep(0.5)
    remaining = processes(executable)
    if remaining:
        print(f"FAIL: {len(remaining)} processes still running after closing")
        describe(remaining)
        if WINDOWS:
            diagnose_windows()
        force_stop(process, executable)
        return 1

    elapsed = time.monotonic() - closed_at
    print(f"OK: window shown, and every process was gone {elapsed:.1f}s after closing")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
