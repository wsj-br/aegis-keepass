#!/usr/bin/env bash
# Upgrade pip and every package named in the repo-root requirements*.txt files.
#
# Uses the project virtualenv when one exists. Does not replace the Python
# interpreter; it upgrades pip for that interpreter, then the requirement sets.
#
#   ./scripts/upgrade-dependencies.sh
#   ./scripts/upgrade-dependencies.sh --python .venv/bin/python
#   ./scripts/upgrade-dependencies.sh --skip-notices
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON=""
SKIP_NOTICES=false

fail() {
  echo "Error: $*" >&2
  exit 1
}

usage() {
  cat <<'EOF'
Usage: ./scripts/upgrade-dependencies.sh [--python=PATH] [--skip-notices]

Upgrade pip, setuptools, and wheel for the selected Python, then upgrade
every package in the repo-root requirements*.txt files
(requirements.txt, requirements-dev.txt, requirements-desktop.txt).

After a successful upgrade, regenerate NOTICES from requirements.txt
unless --skip-notices is set.

Options:
  --python=PATH   Interpreter to upgrade (default: .venv, else python3)
  --skip-notices  Do not run ./scripts/update-notices.sh afterward
  -h, --help      Show this help
EOF
}

for arg in "$@"; do
  case "$arg" in
    --python=*)
      PYTHON="${arg#--python=}"
      ;;
    --skip-notices)
      SKIP_NOTICES=true
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $arg" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ -z "$PYTHON" ]]; then
  if [[ -x "${ROOT}/.venv/bin/python" ]]; then
    PYTHON="${ROOT}/.venv/bin/python"
  elif [[ -x "${ROOT}/.venv/Scripts/python.exe" ]]; then
    PYTHON="${ROOT}/.venv/Scripts/python.exe"
  else
    PYTHON="$(command -v python3 || true)"
  fi
fi

[[ -n "$PYTHON" && -x "$PYTHON" ]] || fail "Python not executable: ${PYTHON:-<none>}"

shopt -s nullglob
REQ_FILES=("${ROOT}"/requirements*.txt)
shopt -u nullglob
[[ ${#REQ_FILES[@]} -gt 0 ]] || fail "No requirements*.txt files in ${ROOT}"

REQ_ARGS=()
for req in "${REQ_FILES[@]}"; do
  REQ_ARGS+=(-r "$req")
done

echo "Python: $("$PYTHON" -c 'import sys; print(sys.version.split()[0], sys.executable)')"
echo "Requirement files:"
printf '  %s\n' "${REQ_FILES[@]}"

echo "Upgrading pip, setuptools, and wheel..."
"$PYTHON" -m pip install --upgrade pip setuptools wheel

echo "Upgrading packages from requirements*.txt..."
"$PYTHON" -m pip install --upgrade "${REQ_ARGS[@]}"

if [[ "$SKIP_NOTICES" == "true" ]]; then
  echo "Skipped NOTICES regeneration."
  exit 0
fi

echo "Regenerating NOTICES from requirements.txt..."
# No --python: update-notices.sh builds a clean env from requirements.txt
# and installs pip-licenses there. The project venv does not have that tool,
# and scanning it would also list dev and desktop packages.
"${ROOT}/scripts/update-notices.sh"
