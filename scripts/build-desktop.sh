#!/usr/bin/env bash
# Build a local desktop executable with PyInstaller.
# On macOS, also write a drag-to-Applications DMG under dist/.
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
elif [[ -x "${ROOT}/.venv/Scripts/python.exe" ]]; then
  PYTHON="${ROOT}/.venv/Scripts/python.exe"
fi

fail() {
  echo "Error: $*" >&2
  exit 1
}

echo "Using Python: ${PYTHON}"
"${PYTHON}" -m pip install -q -r requirements.txt -r requirements-desktop.txt

case "$(uname -s)" in
  Linux*)
    echo "Note: Linux desktop needs host GTK + WebKitGTK (not bundled in the binary)."
    echo "  Run:  sudo apt-get install -y gir1.2-gtk-3.0 gir1.2-webkit2-4.1 libgtk-3-0 libwebkit2gtk-4.1-0"
    echo "  Build/dev also needs python3-gi for this Python (or: pip install 'PyGObject>=3.48,<3.52')."
    ;;
  Darwin*)
    echo "Note: macOS build matches this Mac (Intel or Apple Silicon) and then writes a DMG."
    ;;
  MINGW*|MSYS*|CYGWIN*|Windows_NT)
    echo "Note: Windows builds need Edge WebView2 Runtime (usually preinstalled)."
    ;;
esac

rm -rf build dist
"${PYTHON}" -m PyInstaller --noconfirm --clean packaging/aegis-keepass.spec

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo ""
  echo "Build complete. Artifacts under: ${ROOT}/dist/"
  ls -lha dist || true
  exit 0
fi

APP_BUNDLE="${ROOT}/dist/Aegis-KeePass OTP Sync.app"
[[ -d "$APP_BUNDLE" ]] || fail "PyInstaller did not produce ${APP_BUNDLE}"

command -v python3 >/dev/null 2>&1 || fail "python3 is required to lay out the macOS DMG."

VERSION="$("${ROOT}/scripts/version")"
case "$(uname -m)" in
  arm64|aarch64) MAC_ARCH="arm64" ;;
  x86_64) MAC_ARCH="intel" ;;
  *) fail "Unsupported macOS architecture: $(uname -m)" ;;
esac

VOLUME_NAME="Aegis-KeePass"
BACKGROUND_TIFF="${ROOT}/packaging/dmg-background.tiff"
[[ -f "$BACKGROUND_TIFF" ]] || fail "DMG background not found: ${BACKGROUND_TIFF}"

if [[ -d "/Volumes/${VOLUME_NAME}" ]]; then
  fail "/Volumes/${VOLUME_NAME} is already mounted. Unmount it and retry."
fi

DMGBUILD_VERSION="1.6.5"
PY_TARGET="${ROOT}/build/dmg-py"
mkdir -p "$PY_TARGET"
if ! PYTHONPATH="$PY_TARGET" python3 -c 'import dmgbuild' >/dev/null 2>&1; then
  echo "Installing dmgbuild ${DMGBUILD_VERSION} ..."
  pip_args=(install --disable-pip-version-check --target "$PY_TARGET" "dmgbuild==${DMGBUILD_VERSION}")
  if python3 -m pip install --help 2>/dev/null | grep -q -- '--break-system-packages'; then
    pip_args+=(--break-system-packages)
  fi
  python3 -m pip "${pip_args[@]}"
fi

SETTINGS="${ROOT}/build/dmg-settings.py"
python3 - "$SETTINGS" "$APP_BUNDLE" "$BACKGROUND_TIFF" <<'PY'
import sys

settings_path, app_path, background_path = sys.argv[1:]
app_name = "Aegis-KeePass OTP Sync.app"
with open(settings_path, "w", encoding="utf-8") as handle:
    handle.write(
        "files = [(%r, %r)]\n"
        "symlinks = {'Applications': '/Applications'}\n"
        "icon_locations = {\n"
        "    %r: (130, 220),\n"
        "    'Applications': (410, 220),\n"
        "}\n"
        "background = %r\n"
        "window_rect = ((200, 120), (540, 380))\n"
        "icon_size = 80\n"
        "text_size = 12\n"
        "format = 'UDZO'\n"
        "filesystem = 'HFS+'\n" % (app_path, app_name, app_name, background_path)
    )
PY

ARCHIVE_NAME="aegis-keepass-${VERSION}-macos-${MAC_ARCH}.dmg"
ARCHIVE_PATH="${ROOT}/dist/${ARCHIVE_NAME}"
rm -f "$ARCHIVE_PATH" "${ARCHIVE_PATH}.sha256"

# dmgbuild 1.6 also writes a pBBk bookmark. Finder then ignores the background
# picture and shows the system window color instead. Skip that record so the
# arrow background stays visible.
PYTHONPATH="${PY_TARGET}${PYTHONPATH:+:$PYTHONPATH}" python3 - "$SETTINGS" "$VOLUME_NAME" "$ARCHIVE_PATH" <<'PY'
import sys

import dmgbuild
import ds_store.store as store

settings_path, volume_name, output_path = sys.argv[1:]
original = store.DSStore.Partial.__setitem__


def skip_background_bookmark(self, code, value):
    if code in ("pBBk", b"pBBk"):
        return
    original(self, code, value)


store.DSStore.Partial.__setitem__ = skip_background_bookmark
dmgbuild.build_dmg(output_path, volume_name, settings_path, lookForHiDPI=False)
PY

if command -v shasum >/dev/null 2>&1; then
  HASH="$(shasum -a 256 "$ARCHIVE_PATH" | awk '{print toupper($1)}')"
elif command -v sha256sum >/dev/null 2>&1; then
  HASH="$(sha256sum "$ARCHIVE_PATH" | awk '{print toupper($1)}')"
else
  fail "Need shasum or sha256sum to write the DMG checksum."
fi

HASH_PATH="${ARCHIVE_PATH}.sha256"
printf '%s  %s\n' "$HASH" "$ARCHIVE_NAME" >"$HASH_PATH"

echo ""
echo "Build complete."
echo "App bundle: ${APP_BUNDLE}"
echo "DMG:        ${ARCHIVE_PATH}"
echo "SHA256:     ${HASH}"
echo "Checksum:   ${HASH_PATH}"
