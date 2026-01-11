#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="${1:-}"
if [[ -z "${VERSION}" ]]; then
  VERSION="$(date +%d.%m.%Y)"
fi

DIST_DIR="${ROOT_DIR}/dist"
OUT_DIR="${ROOT_DIR}/dist_installer/macos"
STAGE_DIR="${ROOT_DIR}/dist_installer/macos_stage"
APP_NAME="FireStorm"

rm -rf "${DIST_DIR}" "${OUT_DIR}" "${STAGE_DIR}"
mkdir -p "${OUT_DIR}" "${STAGE_DIR}"

python -m pip install --upgrade pip pyinstaller
python setup.py build_ext --inplace
echo "${VERSION}" > "${ROOT_DIR}/FireStorm/ver"

pyinstaller \
  --noconfirm \
  --clean \
  --name "${APP_NAME}" \
  --windowed \
  --hidden-import=tkinter \
  --hidden-import=PIL._tkinter_finder \
  --collect-submodules PIL \
  --add-data "FireStorm/settings:settings" \
  --add-data "FireStorm/layouts:layouts" \
  --add-data "FireStorm/img:img" \
  --add-data "FireStorm/update_installer.py:update_installer.py" \
  --add-data "FireStorm/ver:ver" \
  "FireStorm/FireStorm.py"

pyinstaller \
  --noconfirm \
  --clean \
  --name "FireStormUploader" \
  --windowed \
  --hidden-import=tkinter \
  --hidden-import=PIL._tkinter_finder \
  --collect-submodules PIL \
  "FireStorm/uploader.py"

cp -R "${DIST_DIR}/${APP_NAME}.app" "${STAGE_DIR}/"
cp -R "${DIST_DIR}/FireStormUploader.app" "${STAGE_DIR}/"

DMG_PATH="${OUT_DIR}/FireStorm-${VERSION}.dmg"
hdiutil create -volname "FireStorm" -srcfolder "${STAGE_DIR}" -ov -format UDZO "${DMG_PATH}"

echo "OK: ${DMG_PATH}"
