import asyncio
import os
import subprocess

from server_app import config


def scan_file(path):
    if not config.CLAMAV_CMD:
        return "skipped"
    try:
        result = subprocess.run(
            [config.CLAMAV_CMD, "--no-summary", path],
            capture_output=True,
            text=True,
            timeout=config.CLAMAV_TIMEOUT_SEC,
        )
    except Exception:
        return "error"
    if result.returncode == 0:
        return "clean"
    if result.returncode == 1:
        return "infected"
    return "error"


async def scan_file_async(path):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, scan_file, path)


def quarantine_file(src_path, route, username, room, date, subdirs):
    quarantine_path = os.path.join(
        config.QUARANTINE_DIR, route, username, room, date, subdirs or ""
    )
    os.makedirs(quarantine_path, exist_ok=True)
    dst_path = os.path.join(quarantine_path, os.path.basename(src_path))
    os.replace(src_path, dst_path)
    return dst_path
