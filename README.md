# gfl2logger

## Installation

### For Regular Users
Executable binaries can be downloaded from [Releases](https://github.com/blead/gfl2logger/releases).

### Build from Source
The instruction below uses [PDM](https://pdm-project.org/en/latest/#installation) to manage dependencies and run scripts. It is also possible to build the project without it.

```sh
git clone https://github.com/blead/gfl2logger
cd gfl2logger
pdm install
pdm run pyinstaller
```

## Usage

1. Run gfl2logger. A console window will show up with a message indicating that it is running.
2. In GFL2, navigate to the Platoon page then click the Member button at the bottom left.
3. A CSV file with relevant data of members and their contributions will be created next to the executable.
