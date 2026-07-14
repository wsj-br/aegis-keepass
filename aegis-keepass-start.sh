#!/usr/bin/env bash
# Start Aegis-KeePass OTP Sync from the published Docker image.
#
# One-liner (Linux / macOS):
#   curl -fsSL https://github.com/wsj-br/aegis-keepass/releases/latest/download/aegis-keepass-start.sh | bash
#
# With options:
#   curl -fsSL https://github.com/wsj-br/aegis-keepass/releases/latest/download/aegis-keepass-start.sh | bash -s -- --detach
#   PORT=9090 curl -fsSL ... | bash
#
# Download and run:
#   curl -fsSL -o aegis-keepass-start.sh https://github.com/wsj-br/aegis-keepass/releases/latest/download/aegis-keepass-start.sh
#   chmod +x aegis-keepass-start.sh && ./aegis-keepass-start.sh
#
# Stop a detached container:
#   ./aegis-keepass-start.sh --stop

set -euo pipefail

IMAGE_REPO="${IMAGE_REPO:-ghcr.io/wsj-br/aegis-keepass}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
CONTAINER_NAME="${CONTAINER_NAME:-aegis-keepass}"
HOST_PORT="${PORT:-${HOST_PORT:-8580}}"
DETACH=false
PULL=true
STOP_ONLY=false
OPEN_BROWSER=false

SESSION_TIMEOUT_SECONDS="${SESSION_TIMEOUT_SECONDS:-1800}"
MAX_IN_MEMORY_UPLOAD_BYTES="${MAX_IN_MEMORY_UPLOAD_BYTES:-33554432}"
MAX_UPLOAD_BYTES="${MAX_UPLOAD_BYTES:-52428800}"

usage() {
  cat <<'EOF'
Usage: aegis-keepass-start.sh [options]

Pull and run Aegis-KeePass OTP Sync from ghcr.io (localhost only).

Options:
  -t, --tag TAG       Image tag (default: latest, or IMAGE_TAG)
  -p, --port PORT     Host port (default: 8580, or PORT / HOST_PORT)
  -d, --detach        Run in the background
  -n, --name NAME     Container name (default: aegis-keepass)
      --no-pull       Skip docker pull (use local image if present)
      --open          Open http://127.0.0.1:<port> in a browser when ready
      --stop          Stop and remove the named container, then exit
  -h, --help          Show this help

Environment:
  IMAGE_REPO, IMAGE_TAG, CONTAINER_NAME, PORT / HOST_PORT
  SESSION_TIMEOUT_SECONDS, MAX_IN_MEMORY_UPLOAD_BYTES, MAX_UPLOAD_BYTES
  FLASK_SECRET_KEY (optional)

Examples:
  curl -fsSL https://github.com/wsj-br/aegis-keepass/releases/latest/download/aegis-keepass-start.sh | bash
  curl -fsSL ... | bash -s -- --detach --port 9090
  ./aegis-keepass-start.sh --tag 0.1.1 --open
  ./aegis-keepass-start.sh --stop
EOF
}

fail() {
  echo "Error: $*" >&2
  exit 1
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "Missing required command: $1. Install Docker: https://docs.docker.com/get-docker/"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -t|--tag)
      [[ $# -ge 2 ]] || fail "$1 requires a value"
      IMAGE_TAG="$2"
      shift 2
      ;;
    -p|--port)
      [[ $# -ge 2 ]] || fail "$1 requires a value"
      HOST_PORT="$2"
      shift 2
      ;;
    -d|--detach)
      DETACH=true
      shift
      ;;
    -n|--name)
      [[ $# -ge 2 ]] || fail "$1 requires a value"
      CONTAINER_NAME="$2"
      shift 2
      ;;
    --no-pull)
      PULL=false
      shift
      ;;
    --open)
      OPEN_BROWSER=true
      shift
      ;;
    --stop)
      STOP_ONLY=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      fail "Unknown argument: $1 (try --help)"
      ;;
  esac
done

[[ "$HOST_PORT" =~ ^[0-9]+$ ]] || fail "Port must be a number: $HOST_PORT"
(( HOST_PORT >= 1 && HOST_PORT <= 65535 )) || fail "Port out of range: $HOST_PORT"

require_cmd docker
docker info >/dev/null 2>&1 || fail "Docker is installed but not running (or not reachable). Start Docker and try again."

IMAGE="${IMAGE_REPO}:${IMAGE_TAG}"
URL="http://127.0.0.1:${HOST_PORT}"

container_exists() {
  docker ps -a --format '{{.Names}}' | grep -Fxq "$CONTAINER_NAME"
}

stop_container() {
  if container_exists; then
    echo "Stopping container '${CONTAINER_NAME}'..."
    docker stop "$CONTAINER_NAME" >/dev/null 2>&1 || true
    docker rm "$CONTAINER_NAME" >/dev/null 2>&1 || true
    echo "Removed '${CONTAINER_NAME}'."
  else
    echo "No container named '${CONTAINER_NAME}' found."
  fi
}

if [[ "$STOP_ONLY" == "true" ]]; then
  stop_container
  exit 0
fi

if container_exists; then
  echo "Removing existing container '${CONTAINER_NAME}'..."
  docker stop "$CONTAINER_NAME" >/dev/null 2>&1 || true
  docker rm "$CONTAINER_NAME" >/dev/null 2>&1 || true
fi

if [[ "$PULL" == "true" ]]; then
  echo "Pulling ${IMAGE}..."
  docker pull "$IMAGE"
fi

RUN_ARGS=(
  --name "$CONTAINER_NAME"
  --rm
  -p "127.0.0.1:${HOST_PORT}:8580"
  --read-only
  --tmpfs "/tmp:size=64M,mode=1777"
  -e "SESSION_TIMEOUT_SECONDS=${SESSION_TIMEOUT_SECONDS}"
  -e "MAX_IN_MEMORY_UPLOAD_BYTES=${MAX_IN_MEMORY_UPLOAD_BYTES}"
  -e "MAX_UPLOAD_BYTES=${MAX_UPLOAD_BYTES}"
)

if [[ -n "${FLASK_SECRET_KEY:-}" ]]; then
  RUN_ARGS+=(-e "FLASK_SECRET_KEY=${FLASK_SECRET_KEY}")
fi

if [[ "$DETACH" == "true" ]]; then
  RUN_ARGS+=(-d)
fi

wait_healthy() {
  local i
  for i in $(seq 1 30); do
    if curl -fsS "$URL/health" >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.5
  done
  return 1
}

open_url() {
  if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$URL" >/dev/null 2>&1 || true
  elif command -v open >/dev/null 2>&1; then
    open "$URL" >/dev/null 2>&1 || true
  fi
}

echo "Starting ${IMAGE} on ${URL} ..."

if [[ "$DETACH" == "true" ]]; then
  docker run "${RUN_ARGS[@]}" "$IMAGE"
  if wait_healthy; then
    echo "Ready at ${URL}"
  else
    echo "Container started; health check not ready yet. Try: ${URL}"
  fi
  echo "Logs:  docker logs -f ${CONTAINER_NAME}"
  echo "Stop:  curl -fsSL https://github.com/wsj-br/aegis-keepass/releases/latest/download/aegis-keepass-start.sh | bash -s -- --stop"
  echo "       (or: docker stop ${CONTAINER_NAME})"
  if [[ "$OPEN_BROWSER" == "true" ]]; then
    open_url
  fi
else
  echo "Open ${URL} in your browser. Press Ctrl+C to stop."
  if [[ "$OPEN_BROWSER" == "true" ]]; then
    (sleep 1; open_url) &
  fi
  docker run "${RUN_ARGS[@]}" "$IMAGE"
fi
