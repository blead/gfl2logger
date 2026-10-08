# gfl2logger v0.3.0

This release brings the Windows and macOS versions together. Both are now built
from the same code, share one version number, and have the same features,
options, and window. Windows continues from v0.2.5; the macOS line, previously
published as v0.1.x, joins the same numbering.

## Downloads

| Platform | Game client | Download |
| --- | --- | --- |
| **Windows** (x64) | PC client | [`gfl2logger-v0.3.0-windows-x64.zip`](../../releases/download/v0.3.0/gfl2logger-v0.3.0-windows-x64.zip) |
| **macOS** (Apple silicon) | iPhone/iPad version from the Mac App Store | [`gfl2logger-v0.3.0-macos-arm64.dmg`](../../releases/download/v0.3.0/gfl2logger-v0.3.0-macos-arm64.dmg) · [`gfl2logger-v0.3.0-macos-arm64.zip`](../../releases/download/v0.3.0/gfl2logger-v0.3.0-macos-arm64.zip) |

## Changes

### Both platforms

- Closing the window now ends the program completely and at once. The window no
  longer waits for the capture process to answer, **Cmd+Q** on macOS takes the
  same path as the close button, and the capture process exits within a few
  seconds of the window going away for any reason. Nothing is left running in
  the background.
- The window opens before the capture set-up starts instead of after it. When
  that set-up was slow or stalled, the program previously ran with nothing on
  screen.
- Every change is now tested and built on Windows and macOS, including starting
  and closing the packaged program, and a release publishes both platforms
  together.

### Windows, since v0.2.5

- Added Platoon Profile (`21905`), Activity (`21935`), and Updates (`21960`)
  exports alongside Members, and grouped the options into **Platoon** and
  **Others**.
- The download is now a `.zip` containing a folder instead of a single `.exe`.
  The single-file form unpacks itself to a temporary folder on every start and
  could not remove it on exit, because the capture driver file inside stays in
  use; it ended with a warning dialog and left the folder behind.
- Kept message bytes that arrive split across TCP chunks and finished parsing
  data already received when a connection closes, so responses are no longer
  dropped or misread at chunk boundaries.
- Released forwarded TCP messages instead of keeping every one for the life of
  the game connection, which grew memory for as long as the logger ran.
- Bounded packet queues and payload reassembly by size, fragment count, and
  timeout.
- Wrote exports to a temporary file and published them only when complete, and
  neutralized formula-leading member names in CSV exports.
- Started with default options when `gfl2logger.config.yaml` is unreadable.
- Updated mitmproxy to 12.2.3.

The capture path on Windows is unchanged from v0.2.5. This build was verified
on Windows by automated tests and by starting and closing the packaged program;
it has not yet been run against a live game session. Please report any
problems.

### macOS, since v0.1.2

- Fixed the app sometimes not showing a window when its icon was clicked. An
  earlier session whose window had been closed with **Cmd+Q** kept running
  without a window, so the next click only activated that leftover process.
- Renamed the app from `gf2logger.app` to `gfl2logger.app` to match the
  project. Replace the old app with the new one; exports and settings stay in
  `~/gfl2logger`.
- The version number moves to v0.3.0 to match Windows.

## Installation

**Windows:** download the `.zip`, extract it to a folder you can write to, and
run `gfl2logger.exe` inside it. If SmartScreen shows **Windows protected your
PC**, choose **More info > Run anyway**. Allow the administrator prompt for
mitmproxy's traffic redirector if Windows shows one.

**macOS:** open the `.dmg` and drag `gfl2logger.app` to **Applications**, or
unzip the `.zip`. The application remains ad-hoc signed and is not yet
Developer ID-notarized. If macOS blocks the first launch, follow the **Open
Anyway** instructions in the [README](../../#macos). Approve **Mitmproxy
Redirector** when macOS requests Network Extension permission.

Start `gfl2logger` before the game on either platform.
