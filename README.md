# gfl2logger

## Installation

### For Regular Users
Executable binaries can be downloaded from [Releases](https://github.com/blead/gfl2logger/releases).

### Build from Source
The instruction below uses [PDM](https://pdm-project.org/en/latest/#installation) to manage dependencies and run scripts.

```sh
git clone https://github.com/blead/gfl2logger
cd gfl2logger
pdm install
pdm run pyinstaller
```

Without PDM, check dependencies and scripts in `pyproject.toml` and install/run them manually.

## How It Works

It reads data transmitted by the client in real-time and logs any data of interest to local files. It does not attempt to initiate or change any connections.

## Support

### Platforms and Regions

This is made for Windows PC client and has been confirmed to work in both DW and HP regions. It is very possible to support other regions but the author currently does not have a good way to test.

There are currently no plans to support other platforms, but emulator is technically close enough to PC that it might be a possibility in the future.

### Data

Support for other data can be added in the future especially if there are valid use cases for them. Mapping between different data is likely the next milestone for future releases.

| Name | Description | Occurrences | Log Format |
| --- | --- | --- | --- |
| `Weapons` | Weapons owned. | login | CSV |
| `Attachments` | Attachments owned. | login | CSV |
| `CommonKeys` | Common Keys owned. | login | CSV |
| `GuildMembers` | Platoon members and their contributions/scores. | login (twice?), reconnection , Platoon pages | CSV |
| `Formations` | Saved Formations. This currently needs to be mapped with weapons, attachments, and common keys to give complete information. | login, reconnection | JSON |

Any opinions and suggestions regarding usage, data, and format will be very welcome.
