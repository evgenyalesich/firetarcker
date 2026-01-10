#!/usr/bin/env bash
set -euo pipefail

SRC="/home/evgeny/pokerhub/PROD/server/"
DEST="root@176.117.69.41:/root/prod/server/"

sudo apt-get update -y
sudo apt-get install -y rsync sshpass

read -s -p "VPS password: " VPS_PASS
echo

sshpass -p "$VPS_PASS" rsync -av --delete "$SRC" "$DEST"

echo "OK: перенесено."
