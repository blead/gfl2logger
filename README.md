# gfl2logger

English | [한국어](README_KR.md)

`gfl2logger` reads the data that Girls' Frontline 2: Exilium receives from its
servers and saves the parts worth keeping, such as Platoon rosters, activity,
and your inventory, to local CSV and JSON files. It runs on **Windows** and
**macOS** from one codebase, with the same features, options, and window on
both.

## Download

| Platform | Game client | Download (v0.3.0) |
| --- | --- | --- |
| **Windows** (x64) | PC client | [`gfl2logger-v0.3.0-windows-x64.zip`](../../releases/download/v0.3.0/gfl2logger-v0.3.0-windows-x64.zip) |
| **macOS** (Apple silicon) | iPhone/iPad version from the Mac App Store | [`gfl2logger-v0.3.0-macos-arm64.dmg`](../../releases/download/v0.3.0/gfl2logger-v0.3.0-macos-arm64.dmg) · [`gfl2logger-v0.3.0-macos-arm64.zip`](../../releases/download/v0.3.0/gfl2logger-v0.3.0-macos-arm64.zip) |

Older versions and release notes are on the [Releases](../../releases) page.

## Getting Started

Start `gfl2logger` **before** the game. If the game is already running, restart
it once the logger window is open.

### Windows

1. Download the `.zip` and extract it to a folder you can write to. Keep the
   `_internal` folder next to `gfl2logger.exe`.
2. Run `gfl2logger.exe`. It is not code-signed, so Windows SmartScreen may show
   **Windows protected your PC**. If you downloaded it from this repository's
   Releases page, choose **More info > Run anyway**.
3. If Windows asks for administrator permission for mitmproxy's traffic
   redirector, allow it.

Exported files are saved in the folder the program is started from. If Windows
refuses to delete or replace the folder later because `WinDivert64.sys` is in
use, restart Windows first; the capture driver can stay loaded after the
program has closed.

### macOS

1. Open the `.dmg` and drag `gfl2logger.app` to **Applications**, or unzip the
   `.zip`.
2. Open the app. It is ad-hoc signed and not notarized with an Apple Developer
   ID, so the first launch is blocked with a **“gfl2logger” Not Opened** alert.
   Click **Done**, open **System Settings > Privacy & Security**, scroll to
   **Security**, and click **Open Anyway**. The button is available for about
   an hour after the blocked attempt, and macOS remembers the exception
   afterwards. See
   [Apple's instructions](https://support.apple.com/guide/mac-help/MCHLEAB3A043/26/mac/26.6.2)
   for details. Only do this for a copy downloaded from this repository's
   Releases page.
3. Approve **Mitmproxy Redirector** when macOS asks for Network Extension
   permission. If it is not enabled automatically, turn it on under **System
   Settings > General > Login Items & Extensions > Network Extensions** and
   relaunch `gfl2logger`.

The bundled network redirector is signed and notarized separately by the
mitmproxy project.

## Usage

1. Leave the checkboxes for the data you want enabled. **Save config** keeps
   the selection for the next launch.
2. Start the game and log in. Open the Platoon pages to request Platoon data.
3. Each time the game receives one of the supported responses, a new file is
   written and the log on the right shows its path.
4. Closing the window ends the program completely. Nothing keeps running in the
   background.

| Platform | Exports and `gfl2logger.config.yaml` are saved in |
| --- | --- |
| Windows | The folder the program is started from, normally the one containing `gfl2logger.exe` |
| macOS | `~/gfl2logger` |

### Exported Data

The options are organized into two groups in the window.

| Group | Option | Payload | Description | Received on | Format |
| --- | --- | ---: | --- | --- | --- |
| Platoon | Platoon Profile | `21905` | Platoon identity, level, member count, announcements, and recruitment information | Platoon pages | JSON |
| Platoon | Members | `21917` | Member names, UIDs, levels, merit points, scores, and login times | Login, reconnection, Platoon pages | CSV |
| Platoon | Activity | `21935` | Platoon objectives and recent member activity | Platoon pages | JSON |
| Platoon | Updates | `21960` | The Updates tab: member joins, withdrawals, removals, and Daily supply reward triggers | Updates tab | JSON |
| Others | Weapons | `11021` | Weapons owned by the current account | Login | CSV |
| Others | Attachments | `11061` | Attachments owned by the current account | Login | CSV |
| Others | Common Keys | `11138` | Common Keys owned by the current account | Login | CSV |
| Others | Formations | `23201` | Saved formations | Login, reconnection | JSON |

Files are named `gfl2logger_<type>_<UTC timestamp>.csv` or `.json`. Updates are
recorded losslessly by protobuf field number and raw hex.

## How It Works

mitmproxy's local capture mode limits interception to the game executable:
`GF2_Exilium` on Windows and `SnqxExilium` on macOS. The logger only reads what
the server sends to the client. It does not start or change any connection, and
TLS connections pass through without being decrypted, so no certificate has to
be installed.

## Supported Clients

- **Windows:** the PC client, confirmed to work in the Darkwinter and HaoPlay
  regions.
- **macOS:** the iPhone/iPad App Store version running on an Apple-silicon Mac.

Other platforms and regions are untested. Suggestions about additional data,
usage, and formats are welcome.

## Build from Source

The project uses [PDM](https://pdm-project.org/) and Python 3.13. From a clone
of this repository:

```sh
pdm install
pdm run pyinstaller
```

This creates `dist/gfl2logger/gfl2logger.exe` on Windows and
`dist/gfl2logger.app` on macOS. To run from source or run the tests:

```sh
pdm run protoc
pdm run python main.py
pdm run python -m unittest discover -s tests
```

Pushing a `v*.*.*` tag builds both platforms and publishes them as one release.

## Credits

`gfl2logger` was created by [blead](https://github.com/blead): the packet
parser, the data exporters, and the original Windows application. macOS
support, the Platoon Profile, Activity, and Updates exports, and the parser and
export hardening were developed in the
[1window2/gf2logger](https://github.com/1window2/gf2logger) fork.

## License

MIT, as declared in `pyproject.toml`.
