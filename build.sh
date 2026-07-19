#!/usr/bin/env bash
# Builds a single-file executable of the EPUB -> AZW3 converter into ./dist
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

APP_NAME="epub2azw3"
VENV="$HERE/.venv"

echo "==> Checking system prerequisites"
if ! python3 -c "import tkinter" 2>/dev/null; then
    echo "Tkinter is missing. Install it with:"
    echo "    sudo apt install python3-tk"
    exit 1
fi

if ! command -v ebook-convert >/dev/null 2>&1; then
    echo "WARNING: 'ebook-convert' not found. The app needs Calibre at run time:"
    echo "    sudo apt install calibre"
fi

echo "==> Creating virtualenv at $VENV"
if [ ! -d "$VENV" ]; then
    python3 -m venv "$VENV" || {
        echo "venv creation failed. Install it with: sudo apt install python3-venv"
        exit 1
    }
fi
# shellcheck disable=SC1091
source "$VENV/bin/activate"

echo "==> Installing dependencies"
pip install --upgrade pip
pip install -r requirements.txt

echo "==> Cleaning previous build"
rm -rf build dist "$APP_NAME.spec"

echo "==> Running PyInstaller"
pyinstaller \
    --onefile \
    --windowed \
    --name "$APP_NAME" \
    --hidden-import ebooklib \
    --hidden-import ebooklib.epub \
    --collect-submodules ebooklib \
    epub2azw3.py

deactivate

chmod +x "dist/$APP_NAME"
echo
echo "==> Done: $HERE/dist/$APP_NAME"
echo "    Double-click it, or run: ./dist/$APP_NAME"
