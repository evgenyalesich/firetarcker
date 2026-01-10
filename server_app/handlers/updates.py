import glob
import os
import zipfile

from aiohttp import web

import modules.logger as logger


def _find_latest_update():
    if os.path.exists("update_v2.zip"):
        return "update_v2.zip"
    candidates = glob.glob("update_*.zip")
    if not candidates:
        return None
    candidates.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return candidates[0]


def _get_version_from_zip(zip_filename):
    try:
        with zipfile.ZipFile(zip_filename, "r") as zip_file:
            comment_bytes = zip_file.comment
            if comment_bytes:
                return comment_bytes.decode("utf-8")
    except Exception:
        pass
    base = os.path.basename(zip_filename)
    if base.startswith("update_") and base.endswith(".zip"):
        return base[len("update_") : -len(".zip")]
    return ""


async def get_update_v2(request):
    data = await request.post()
    version = data.get("version")
    if version:
        versioned = f"update_{version}.zip"
        if os.path.exists(versioned):
            return web.FileResponse(versioned)
    latest = _find_latest_update()
    if not latest:
        return web.Response(status=404)
    return web.FileResponse(latest)


async def get_update_v2_sig(request):
    data = await request.post()
    version = data.get("version")
    if version:
        sig_path = f"update_{version}.zip.asc"
        if os.path.exists(sig_path):
            return web.FileResponse(sig_path)
    latest = _find_latest_update()
    if not latest:
        return web.Response(status=404)
    sig_path = f"{latest}.asc"
    if not os.path.exists(sig_path):
        return web.Response(status=404)
    return web.FileResponse(sig_path)


async def check_update_v2(request):
    try:
        await logger.debug("Поступил запрос на актуальную версию ПО v2")
        latest = _find_latest_update()
        if not latest:
            return web.Response(status=303, text="")
        update_version = _get_version_from_zip(latest)
        return web.Response(status=303, text=update_version)
    except Exception as error:
        await logger.error(f"Ошибка в check_update_v2: {error}")
