#!/usr/bin/env bash
set -euo pipefail

# Generate / update the repo-root NOTICES file.
#
# Includes a fixed Alpine base-image notice (Dockerfile uses python:*-alpine),
# then Python dependency notices from requirements.txt via pip-licenses
# (https://pypi.org/project/pip-licenses/).
#
# Usage (from repository root):
#   ./scripts/update-notices.sh
#   ./scripts/update-notices.sh --output NOTICES
#   ./scripts/update-notices.sh --python .venv/bin/python

OUTPUT="NOTICES"
PYTHON=""

for arg in "$@"; do
  case "$arg" in
    --output=*)
      OUTPUT="${arg#--output=}"
      ;;
    --python=*)
      PYTHON="${arg#--python=}"
      ;;
    -h|--help)
      cat <<'EOF'
Usage: ./scripts/update-notices.sh [--output=NOTICES] [--python=PATH]

Regenerate third-party Python license/NOTICE text with pip-licenses.

Options:
  --output=PATH   Output file (default: NOTICES at repo root)
  --python=PATH   Python interpreter whose site-packages to scan
                  (default: temporary venv with requirements.txt)
  -h, --help      Show this help

Always install deps into a clean env (temp venv or your project venv)
before scanning so the NOTICES file matches what the app ships.
EOF
      exit 0
      ;;
    *)
      echo "Unknown argument: $arg" >&2
      exit 1
      ;;
  esac
done

fail() {
  echo "Error: $*" >&2
  exit 1
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "Missing required command: $1"
}

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

require_cmd python3
[[ -f requirements.txt ]] || fail "requirements.txt not found in repository root."

TMP_DIR=""
cleanup() {
  if [[ -n "${TMP_DIR}" && -d "${TMP_DIR}" ]]; then
    rm -rf "${TMP_DIR}"
  fi
}
trap cleanup EXIT

if [[ -z "${PYTHON}" ]]; then
  require_cmd python3
  TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/aegis-notices.XXXXXX")"
  python3 -m venv "${TMP_DIR}/venv"
  # shellcheck disable=SC1091
  source "${TMP_DIR}/venv/bin/activate"
  python -m pip install --upgrade pip >/dev/null
  python -m pip install -r requirements.txt "pip-licenses>=5.0" >/dev/null
  PYTHON="$(command -v python)"
else
  [[ -x "${PYTHON}" ]] || fail "Python not executable: ${PYTHON}"
  "${PYTHON}" -m pip show pip-licenses >/dev/null 2>&1 || \
    fail "pip-licenses is not installed for ${PYTHON}. Install with: ${PYTHON} -m pip install pip-licenses"
fi

TMP_JSON="$(mktemp)"
TMP_BODY="$(mktemp)"
"${PYTHON}" -m piplicenses \
  --from=mixed \
  --format=json \
  --with-license-file \
  --with-notice-file \
  --no-license-path \
  --output-file="${TMP_JSON}"

"${PYTHON}" - "${TMP_JSON}" "${TMP_BODY}" <<'PY'
import json
import sys

src, dst = sys.argv[1], sys.argv[2]
packages = json.loads(open(src, encoding="utf-8").read())
divider = "-" * 80
blocks = []
for pkg in packages:
    name = pkg.get("Name") or "UNKNOWN"
    version = pkg.get("Version") or ""
    license_name = pkg.get("License") or "UNKNOWN"
    license_text = (pkg.get("LicenseText") or "").strip()
    notice_text = (pkg.get("NoticeText") or "").strip()
    if notice_text.upper() == "UNKNOWN":
        notice_text = ""

    lines = [name, version, license_name, ""]
    if license_text and license_text.upper() != "UNKNOWN":
        lines.append(license_text)
        lines.append("")
    if notice_text:
        lines.append("NOTICE:")
        lines.append(notice_text)
        lines.append("")
    blocks.append("\n".join(lines).rstrip() + "\n")

open(dst, "w", encoding="utf-8").write(("\n" + divider + "\n\n").join(blocks))
PY

{
  cat <<EOF
Third-party notices for Aegis-KeePass OTP Sync
==============================================

This file lists third-party notices for:
  1. The Alpine Linux base used by the published Docker image (Dockerfile)
  2. Python packages from requirements.txt (and transitive deps), via pip-licenses

Regenerate with:

  ./scripts/update-notices.sh

Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")

--------------------------------------------------------------------------------

Alpine Linux (Docker base image)
python:*-alpine (official Docker Hub image)
Mixed (distribution + package licenses)

The published container image (\`ghcr.io/wsj-br/aegis-keepass\`) is built \`FROM
python:*-alpine\`, which is based on Alpine Linux.

Alpine Linux is a community-developed Linux distribution built around musl libc
and BusyBox. See: https://www.alpinelinux.org/about/

Key components commonly present in Alpine / python-alpine images include (not
exhaustive; package set varies by tag):

  - Alpine aports / packaging infrastructure — often MIT / OSI-permissive for
    Alpine project material; individual packages keep their own licenses.
  - musl libc — MIT
    https://musl.libc.org/
  - BusyBox — GPL-2.0-only
    https://busybox.net/license.html
  - apk-tools and other Alpine packages — see each package license

For the exact package list and licenses inside a built image:

  docker run --rm --entrypoint sh IMAGE -c 'apk info -v && apk info -a busybox'

Package index: https://pkgs.alpinelinux.org/

This section is a distribution attribution for the Docker base OS. It does not
reproduce every Alpine system package license text (that set is defined by the
base image tag, not by this repository's requirements.txt).

--------------------------------------------------------------------------------

EOF
  cat "${TMP_BODY}"
} > "${OUTPUT}"

rm -f "${TMP_JSON}" "${TMP_BODY}"

echo "Wrote ${OUTPUT}"
