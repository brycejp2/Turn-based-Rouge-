#!/usr/bin/env bash
# Build the Hollowreach executable on Linux or macOS.
# Run from anywhere:  ./packaging/build.sh
set -euo pipefail
cd "$(dirname "$0")/.."

echo "[1/3] Creating build virtual environment..."
python3 -m venv .buildenv
# shellcheck disable=SC1091
source .buildenv/bin/activate

echo "[2/3] Installing build dependencies..."
python -m pip install --upgrade pip >/dev/null
python -m pip install -r requirements-dev.txt

echo "[3/3] Building the executable..."
pyinstaller --clean --noconfirm packaging/hollowreach.spec

echo
echo "Done. Your game is at: dist/Hollowreach"
