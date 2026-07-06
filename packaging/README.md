# Building Hollowreach

Hollowreach ships as a single self-contained executable built with
[PyInstaller](https://pyinstaller.org). The 2D tile art is drawn in code
and the game uses pygame's built-in font, so there are **no external
asset files** to bundle — the build is just the Python code + pygame.

> PyInstaller is **not** a cross-compiler: build the Windows `.exe` **on
> Windows**, the macOS app on macOS, and the Linux binary on Linux.

## Windows (produces `Hollowreach.exe`)

1. Install [Python 3.10+](https://www.python.org/downloads/) and tick
   **"Add python.exe to PATH"** in the installer.
2. Open a terminal in the repository root and run:

   ```bat
   packaging\build_windows.bat
   ```

   This creates a build virtualenv, installs `pygame` + `pyinstaller`,
   and builds the game. When it finishes you'll have:

   ```
   dist\Hollowreach.exe
   ```

   Double-click it to play, or run it from a terminal. It's a windowed
   app — no console window appears.

### Manual build (any OS)

```bash
python -m venv .buildenv
# Windows:  .buildenv\Scripts\activate
# macOS/Linux:  source .buildenv/bin/activate
pip install -r requirements-dev.txt
pyinstaller --clean --noconfirm packaging/hollowreach.spec
```

On macOS/Linux, `packaging/build.sh` does the same steps automatically.

## Verifying a build

Run the frozen binary headlessly to confirm the bundle is complete:

```bash
# Windows
dist\Hollowreach.exe --demo 60
# macOS/Linux
./dist/Hollowreach --demo 60
```

It should play 60 AI turns and print a summary.

## Options

* **Icon** — drop a `hollowreach.ico` next to the spec and uncomment the
  `icon=` line in `packaging/hollowreach.spec` for a custom taskbar icon.
* **One-folder build** — a one-folder bundle starts faster than the
  single-file default (which unpacks to a temp dir on launch). Change the
  spec to add a `COLLECT(...)` step, or pass `--onedir` to a plain
  `pyinstaller main.py` invocation.
* **Command-line flags** still work on the built binary: `--ascii` for the
  terminal client, `--demo N` for the headless AI demo, `--seed N` for a
  reproducible run, `--no-blight` to disable the Hollowing.

## Toward Steam

The executable is what a Steam depot ships. Remaining store-side steps
(outside this repo): the $100 Steam Direct fee, a store page with
capsule art and screenshots, and optional Steamworks integration
(achievements, cloud saves) via a library such as `steamworks-py`.
