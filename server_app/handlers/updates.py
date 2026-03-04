import glob
import os
import zipfile

from aiohttp import web

import modules.logger as logger


def _get_update_dir(platform=None):
    base_dir = os.getenv("UPDATE_DIR", "updates")
    if platform:
        platform_dir = os.path.join(base_dir, platform)
        if os.path.isdir(platform_dir):
            return platform_dir
    return base_dir


def _parse_version_key(version):
    parts = version.split(".")
    if len(parts) < 3:
        return None
    try:
        day = int(parts[0])
        month = int(parts[1])
        year = int(parts[2])
        build = int(parts[3]) if len(parts) > 3 else 0
    except ValueError:
        return None
    return (year, month, day, build)


def _find_latest_update(platform=None):
    update_dir = _get_update_dir(platform)
    candidates = glob.glob(os.path.join(update_dir, "update_*.zip"))
    legacy = "update_v2.zip"
    if not candidates and os.path.exists(legacy) and update_dir == os.getenv("UPDATE_DIR", "updates"):
        return legacy
    if not candidates and platform is None:
        linux_dir = _get_update_dir("linux")
        candidates = glob.glob(os.path.join(linux_dir, "update_*.zip"))
        if not candidates:
            return None
    def _candidate_key(path):
        version = _get_version_from_zip(path)
        parsed = _parse_version_key(version) if version else None
        if parsed is None:
            return (0, 0, 0, 0, os.path.getmtime(path))
        return (*parsed, os.path.getmtime(path))

    return max(candidates, key=_candidate_key)


def _get_version_from_zip(zip_filename):
    base = os.path.basename(zip_filename)
    if base.startswith("update_") and base.endswith(".zip"):
        return base[len("update_") : -len(".zip")]
    try:
        with zipfile.ZipFile(zip_filename, "r") as zip_file:
            comment_bytes = zip_file.comment
            if comment_bytes:
                return comment_bytes.decode("utf-8")
    except Exception:
        pass
    return ""


async def get_update_v2(request):
    data = await request.post()
    version = data.get("version")
    platform = data.get("platform")
    if version:
        versioned = os.path.join(_get_update_dir(platform), f"update_{version}.zip")
        if os.path.exists(versioned):
            return web.FileResponse(versioned)
        if not platform:
            linux_versioned = os.path.join(_get_update_dir("linux"), f"update_{version}.zip")
            if os.path.exists(linux_versioned):
                return web.FileResponse(linux_versioned)
    latest = _find_latest_update(platform)
    if not latest:
        return web.Response(status=404)
    return web.FileResponse(latest)


async def get_update_v2_sig(request):
    data = await request.post()
    version = data.get("version")
    platform = data.get("platform")
    if version:
        sig_path = os.path.join(_get_update_dir(platform), f"update_{version}.zip.asc")
        if os.path.exists(sig_path):
            return web.FileResponse(sig_path)
        if not platform:
            linux_sig = os.path.join(_get_update_dir("linux"), f"update_{version}.zip.asc")
            if os.path.exists(linux_sig):
                return web.FileResponse(linux_sig)
    latest = _find_latest_update(platform)
    if not latest:
        return web.Response(status=404)
    sig_path = f"{latest}.asc"
    if not os.path.exists(sig_path):
        return web.Response(status=404)
    return web.FileResponse(sig_path)


async def check_update_v2(request):
    try:
        await logger.debug("Поступил запрос на актуальную версию ПО v2")
        data = await request.post()
        platform = data.get("platform")
        latest = _find_latest_update(platform)
        if not latest:
            return web.Response(status=303, text="")
        update_version = _get_version_from_zip(latest)
        return web.Response(status=303, text=update_version)
    except Exception as error:
        await logger.error(f"Ошибка в check_update_v2: {error}")
