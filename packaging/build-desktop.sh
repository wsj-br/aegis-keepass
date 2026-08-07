#!/usr/bin/env bash
# Build a local desktop executable with PyInstaller.
# Run from the repo root (or any cwd; script cds to root).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -f requirements.txt || ! -f requirements-desktop.txt ]]; then
  echo "Missing requirements files in ${ROOT}" >&2
  exit 1
fi

PYTHON="${PYTHON:-python3}"
if [[ -x "${ROOT}/.venv/bin/python" ]]; then
  PYTHON="${ROOT}/.venv/bin/python"
fi

echo "Using Python: ${PYTHON}"
"${PYTHON}" -m pip install -q -r requirements.txt -r requirements-desktop.txt

case "$(uname -s)" in
  Linux*)
    echo "Note: Linux builds need WebKitGTK at build and runtime."
    echo "  Debian/Ubuntu: sudo apt-get install -y gir1.2-webkit2-4.1 gir1.2-gtk-3.0 libwebkit2gtk-4.1-dev"
    ;;
  Darwin*)
    echo "Note: macOS build targets universal2 (requires a universal2 Python)."
    ;;
  MINGW*|MSYS*|CYGWIN*|Windows_NT)
    echo "Note: Windows builds need Edge WebView2 Runtime (usually preinstalled)."
    ;;
esac

rm -rf build dist
"${PYTHON}" -m PyInstaller --noconfirm --clean packaging/aegis-keepass.spec

echo ""
echo "Build complete. Artifacts under: ${ROOT}/dist/"
ls -la dist || true
