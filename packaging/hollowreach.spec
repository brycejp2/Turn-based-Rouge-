# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Hollowreach.

Builds a single-file, windowed executable that launches the 2D tile
client (``main.py`` with no arguments).  Run from the repository root:

    pyinstaller --clean packaging/hollowreach.spec

The output is ``dist/Hollowreach`` (``dist/Hollowreach.exe`` on Windows).

Notes
-----
* ``SPECPATH`` is injected by PyInstaller and points at this file's
  directory, so paths resolve regardless of the working directory.
* pygame's bundled default font and native libraries are collected by the
  pyinstaller-hooks-contrib hooks automatically; the tile art is drawn in
  code, so there are no image assets to bundle.
* The tile client is imported lazily inside ``main.run_tiles``, so the UI
  modules are listed as hidden imports to be safe.
"""

import os

repo_root = os.path.abspath(os.path.join(SPECPATH, os.pardir))

a = Analysis(
    [os.path.join(repo_root, "main.py")],
    pathex=[repo_root],
    binaries=[],
    datas=[],
    hiddenimports=[
        "hollowreach.ui.pygame_app",
        "hollowreach.ui.tiles",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Hollowreach",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # windowed app: no console window on Windows
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon="packaging/hollowreach.ico",  # add an .ico here when available
)
