#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COUNTER_FILE="${ROOT_DIR}/tools/.build_counter"

VERSION=""
NEWS=""
SIGN=1
GPG_KEY_ID="${GPG_KEY_ID:-}"
VPS_HOST="${VPS_HOST:-176.117.69.41}"
VPS_USER="${VPS_USER:-root}"
VPS_PATH="${VPS_PATH:-/root/prod/server}"

usage() {
  cat <<EOF
Usage: tools/local_deploy.sh [--version X] [--news PATH] [--no-sign] [--gpg-key KEYID] [--host HOST] [--user USER] [--path PATH]

Builds Linux client + update, signs update, builds .deb, and uploads to VPS.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --version) VERSION="$2"; shift 2;;
    --news) NEWS="$2"; shift 2;;
    --no-sign) SIGN=0; shift;;
    --gpg-key) GPG_KEY_ID="$2"; shift 2;;
    --host) VPS_HOST="$2"; shift 2;;
    --user) VPS_USER="$2"; shift 2;;
    --path) VPS_PATH="$2"; shift 2;;
    -h|--help) usage; exit 0;;
    *) echo "Unknown arg: $1" >&2; usage; exit 1;;
  esac
done

if [[ -z "${VERSION}" ]]; then
  today="$(date +%d.%m.%Y)"
  last_date=""
  last_num="0"
  if [[ -f "${COUNTER_FILE}" ]]; then
    read -r last_date last_num < "${COUNTER_FILE}" || true
  fi
  if [[ "${last_date}" == "${today}" ]]; then
    last_num=$((last_num + 1))
  else
    last_num=1
  fi
  VERSION="${today}.${last_num}"
  echo "${today} ${last_num}" > "${COUNTER_FILE}"
fi

SIGN_ARGS=()
if [[ "${SIGN}" -eq 1 ]]; then
  if [[ -z "${GPG_KEY_ID}" ]]; then
    echo "GPG_KEY_ID is required for signing (set env or use --gpg-key)." >&2
    exit 1
  fi
  SIGN_ARGS=(--sign --gpg-key "${GPG_KEY_ID}")
fi

echo "Build version: ${VERSION}"

cd "${ROOT_DIR}"

BUILD_CMD=(python3 tools/autobuild.py --dist dist_client --version "${VERSION}")
if [[ -n "${NEWS}" ]]; then
  BUILD_CMD+=(--news "${NEWS}")
fi
if [[ "${SIGN}" -eq 1 ]]; then
  BUILD_CMD+=("${SIGN_ARGS[@]}")
fi
"${BUILD_CMD[@]}"

bash tools/build_installer_linux.sh "${VERSION}"

UPDATE_ZIP="${ROOT_DIR}/update_${VERSION}.zip"
UPDATE_ASC="${UPDATE_ZIP}.asc"
DEB_PATH="${ROOT_DIR}/dist_installer/linux/firestorm_${VERSION}_amd64.deb"

if [[ ! -f "${UPDATE_ZIP}" ]]; then
  echo "Missing update zip: ${UPDATE_ZIP}" >&2
  exit 1
fi
if [[ "${SIGN}" -eq 1 && ! -f "${UPDATE_ASC}" ]]; then
  echo "Missing update signature: ${UPDATE_ASC}" >&2
  exit 1
fi
if [[ ! -f "${DEB_PATH}" ]]; then
  echo "Missing installer: ${DEB_PATH}" >&2
  exit 1
fi

echo "Uploading to VPS ${VPS_USER}@${VPS_HOST}:${VPS_PATH} ..."
ssh "${VPS_USER}@${VPS_HOST}" "mkdir -p ${VPS_PATH}/updates ${VPS_PATH}/updates/linux ${VPS_PATH}/installers/linux"
rsync -av "${UPDATE_ZIP}" "${VPS_USER}@${VPS_HOST}:${VPS_PATH}/updates/linux/"
rsync -av "${UPDATE_ZIP}" "${VPS_USER}@${VPS_HOST}:${VPS_PATH}/updates/"
if [[ "${SIGN}" -eq 1 ]]; then
  rsync -av "${UPDATE_ASC}" "${VPS_USER}@${VPS_HOST}:${VPS_PATH}/updates/linux/"
  rsync -av "${UPDATE_ASC}" "${VPS_USER}@${VPS_HOST}:${VPS_PATH}/updates/"
fi
rsync -av "${DEB_PATH}" "${VPS_USER}@${VPS_HOST}:${VPS_PATH}/installers/linux/"

echo "OK: local deploy finished"
