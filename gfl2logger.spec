# -*- mode: python ; coding: utf-8 -*-

import platform
import re
from pathlib import Path


# Single source of truth for the bundle version, so the app's Info.plist cannot drift
# from the version the program reports.
version = re.search(
    r'^VERSION = "([^"]+)"',
    Path(SPECPATH, 'gfl2logger', 'utils', 'version.py').read_text(encoding='utf-8'),
    re.MULTILINE,
).group(1)

is_macos = platform.system() == 'Darwin'
icon = 'embed/icon.png' if is_macos else 'embed/icon.ico'

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('embed', 'embed')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=2,
)
pyz = PYZ(a.pure)

if is_macos:
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='gfl2logger',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=icon,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name='gfl2logger',
    )
    app = BUNDLE(
        coll,
        name='gfl2logger.app',
        icon='embed/icon.png',
        bundle_identifier='org.gf2logger.app',
        info_plist={
            'CFBundleDisplayName': 'gfl2logger',
            'CFBundleShortVersionString': version,
            'CFBundleVersion': version,
        },
    )
else:
    # A folder build rather than a single file. A single-file build unpacks itself into
    # a temporary directory on every start and removes it on exit, but the WinDivert
    # driver file loaded from there stays in use, so the removal fails and the launcher
    # is left showing a warning. A folder build has nothing to clean up.
    exe = EXE(
        pyz,
        a.scripts,
        [('O', None, 'OPTION'), ('O', None, 'OPTION')],
        exclude_binaries=True,
        name='gfl2logger',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=icon,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name='gfl2logger',
    )
