@echo off
REM Build Hollowreach.exe on Windows.
REM Prereqs: Python 3.10+ on PATH. Run this from the repository root:
REM     packaging\build_windows.bat

setlocal
cd /d "%~dp0.."

echo [1/3] Creating build virtual environment...
python -m venv .buildenv || goto :error
call .buildenv\Scripts\activate.bat

echo [2/3] Installing build dependencies...
python -m pip install --upgrade pip >nul
python -m pip install -r requirements-dev.txt || goto :error

echo [3/3] Building the executable...
pyinstaller --clean --noconfirm packaging\hollowreach.spec || goto :error

echo.
echo Done. Your game is at:  dist\Hollowreach.exe
echo Double-click it, or run it from a terminal.
goto :eof

:error
echo.
echo Build failed. See the messages above.
exit /b 1
