#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PIDFILE="${ROOT_DIR}/server.pid"
LOGFILE="${ROOT_DIR}/logs/server.log"
VENV_PY="${ROOT_DIR}/.venv/bin/python"

mkdir -p "${ROOT_DIR}/logs"

load_env() {
  if [[ -f "${ROOT_DIR}/.env" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "${ROOT_DIR}/.env"
    set +a
  fi
}

is_running() {
  if [[ -f "${PIDFILE}" ]]; then
    local pid
    pid="$(cat "${PIDFILE}")"
    if [[ -n "${pid}" ]] && kill -0 "${pid}" 2>/dev/null; then
      return 0
    fi
  fi
  return 1
}

start_server() {
  if is_running; then
    echo "Server already running (pid=$(cat "${PIDFILE}"))."
    exit 0
  fi
  load_env
  local py="python3"
  if [[ -x "${VENV_PY}" ]]; then
    py="${VENV_PY}"
  fi
  nohup "${py}" "${ROOT_DIR}/server.py" -d >> "${LOGFILE}" 2>&1 &
  echo $! > "${PIDFILE}"
  echo "Started (pid=$(cat "${PIDFILE}")), logs: ${LOGFILE}"
}

stop_server() {
  if is_running; then
    local pid
    pid="$(cat "${PIDFILE}")"
    kill "${pid}" || true
    rm -f "${PIDFILE}"
    echo "Stopped (pid=${pid})."
  else
    echo "Server not running."
  fi
}

status_server() {
  if is_running; then
    echo "Running (pid=$(cat "${PIDFILE}"))."
  else
    echo "Not running."
  fi
}

case "${1:-start}" in
  start)
    start_server
    ;;
  stop)
    stop_server
    ;;
  restart)
    stop_server
    start_server
    ;;
  status)
    status_server
    ;;
  *)
    echo "Usage: $0 {start|stop|restart|status}"
    exit 1
    ;;
esac
