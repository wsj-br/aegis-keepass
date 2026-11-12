#!/usr/bin/env bash
# Wrap dist/aegis-keepass in an AppImage.
# GTK and WebKit stay on the host.
# Run from the repo root after PyInstaller. Needs network on first use
# (appimagetool and the AppImage runtime).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

fail() {
  echo "Error: $*" >&2
  exit 1
}

[[ "$(uname -s)" == "Linux" ]] || fail "AppImages are built on Linux."

BINARY="${ROOT}/dist/aegis-keepass"
[[ -f "$BINARY" ]] || fail "Missing ${BINARY}. Run PyInstaller first."

VERSION="$("${ROOT}/scripts/version")"
case "$(uname -m)" in
  x86_64) APPIMAGE_ARCH="x86_64"; ASSET_ARCH="amd64" ;;
  aarch64|arm64) APPIMAGE_ARCH="aarch64"; ASSET_ARCH="arm64" ;;
  *) fail "Unsupported Linux architecture: $(uname -m)" ;;
esac

APPIMAGETOOL_VERSION="1.9.1"
case "$APPIMAGE_ARCH" in
  x86_64)
    APPIMAGETOOL_SHA256="ed4ce84f0d9caff66f50bcca6ff6f35aae54ce8135408b3fa33abfc3cb384eb0"
    ;;
  aarch64)
    APPIMAGETOOL_SHA256="f0837e7448a0c1e4e650a93bb3e85802546e60654ef287576f46c71c126a9158"
    ;;
esac

TOOL_DIR="${ROOT}/build/appimagetool"
TOOL_PATH="${TOOL_DIR}/appimagetool-${APPIMAGE_ARCH}.AppImage"
mkdir -p "$TOOL_DIR"
if [[ ! -f "$TOOL_PATH" ]] || ! echo "${APPIMAGETOOL_SHA256}  ${TOOL_PATH}" | sha256sum -c - >/dev/null 2>&1; then
  echo "Downloading appimagetool ${APPIMAGETOOL_VERSION} (${APPIMAGE_ARCH}) ..."
  curl -fsSL -o "${TOOL_PATH}.partial" \
    "https://github.com/AppImage/appimagetool/releases/download/${APPIMAGETOOL_VERSION}/appimagetool-${APPIMAGE_ARCH}.AppImage"
  echo "${APPIMAGETOOL_SHA256}  ${TOOL_PATH}.partial" | sha256sum -c -
  mv "${TOOL_PATH}.partial" "$TOOL_PATH"
  chmod +x "$TOOL_PATH"
fi

APP_ID="br.wsj.AegisKeePass"
APPDIR="${ROOT}/build/AppDir"
rm -rf "$APPDIR"
mkdir -p \
  "${APPDIR}/usr/bin" \
  "${APPDIR}/usr/share/applications" \
  "${APPDIR}/usr/share/icons/hicolor/256x256/apps" \
  "${APPDIR}/usr/share/doc/aegis-keepass"

cp "$BINARY" "${APPDIR}/usr/bin/aegis-keepass"
chmod +x "${APPDIR}/usr/bin/aegis-keepass"
[[ -f "${ROOT}/LICENSE" ]] && cp "${ROOT}/LICENSE" "${APPDIR}/usr/share/doc/aegis-keepass/"
[[ -f "${ROOT}/NOTICES" ]] && cp "${ROOT}/NOTICES" "${APPDIR}/usr/share/doc/aegis-keepass/"

ICON_SRC="${ROOT}/app/static/img/logo.png"
[[ -f "$ICON_SRC" ]] || fail "Logo not found: ${ICON_SRC}"
cp "$ICON_SRC" "${APPDIR}/${APP_ID}.png"
cp "$ICON_SRC" "${APPDIR}/usr/share/icons/hicolor/256x256/apps/${APP_ID}.png"
cp "$ICON_SRC" "${APPDIR}/.DirIcon"

cat >"${APPDIR}/${APP_ID}.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Aegis-KeePass OTP Sync
Exec=aegis-keepass
Icon=${APP_ID}
StartupWMClass=${APP_ID}
Categories=Utility;
Terminal=false
X-AppImage-Version=${VERSION}
EOF
cp "${APPDIR}/${APP_ID}.desktop" "${APPDIR}/usr/share/applications/${APP_ID}.desktop"

cat >"${APPDIR}/AppRun" <<'EOF'
#!/bin/sh
set -e
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/usr/bin/aegis-keepass" "$@"
EOF
chmod +x "${APPDIR}/AppRun"

OUTPUT="${ROOT}/dist/aegis-keepass-${VERSION}-linux-${ASSET_ARCH}.AppImage"
rm -f "$OUTPUT"

echo "Building ${OUTPUT} ..."
ARCH="$APPIMAGE_ARCH" VERSION="$VERSION" "$TOOL_PATH" --no-appstream "$APPDIR" "$OUTPUT"
chmod +x "$OUTPUT"

echo ""
echo "AppImage: ${OUTPUT}"
