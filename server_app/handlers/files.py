import os
import threading
import time

from aiohttp import web

import modules.logger as logger
from server_app import config, state
from server_app.security import is_safe_component, is_valid_auth
from server_app.services.file_scan import collect_file_info
from server_app.services.redis_queue import enqueue_scan, get_scan_result


async def get_files_list(request):
    data = await request.post()
    username = data.get("username")
    room = data.get("room")
    auth_key = data.get("auth_key")
    route = data.get("route")

    if (
        not is_safe_component(username)
        or not is_safe_component(room)
        or not is_safe_component(route)
    ):
        await logger.debug(
            f'Невалидные параметры пути: username="{username}", room="{room}", route="{route}"'
        )
        return web.Response(status=400)

    if not is_valid_auth(username, auth_key):
        await logger.debug(f'Ключ пользователя "{username}" невлидный!')
        return web.Response(status=301)

    if config.REDIS_ENABLED:
        result = get_scan_result(username)
        if result is not None:
            return web.Response(status=400, text=str(result))
        enqueue_scan(username, room, route)
        return web.Response(status=300)

    if username not in state.USERS_FILES:
        state.USERS_FILES[username] = None
        thread = threading.Thread(target=scan_files, args=(username, room, route))
        thread.daemon = True
        thread.start()
        return web.Response(status=300)

    if state.USERS_FILES[username] is None:
        return web.Response(status=300)

    files_list = state.USERS_FILES[username]
    del state.USERS_FILES[username]
    return web.Response(status=400, text=str(files_list))


def scan_files(username, room, route):
    start_time = time.perf_counter()
    file_info = collect_file_info(username, room, route)

    end_time = time.perf_counter()
    execution_time = end_time - start_time
    logger.sync_debug(
        f"Время просчёта файлов рук для {username}: {execution_time} сек. Файлов: {len(file_info)}"
    )

    state.USERS_FILES[username] = file_info


async def get_file_names(path):
    try:
        file_info = []
        if not os.path.exists(path):
            os.makedirs(path)
        subfolders = [f.path for f in os.scandir(path) if f.is_dir()]
        for subfolder in subfolders:
            if os.path.exists(subfolder):
                for root, dirs, files in os.walk(subfolder):
                    for file in files:
                        relative_path = os.path.relpath(os.path.join(root, file), subfolder)
                        file_path = os.path.normpath(os.path.join(root, file))
                        with open(file_path, mode="rb") as f:
                            md5_hash = hashlib.md5()
                            while chunk := f.read(4096):
                                md5_hash.update(chunk)
                            checksum = md5_hash.hexdigest()

                        file_info.append([relative_path, checksum])
        return file_info
    except Exception as error:
        await logger.error(f"Ошибка в get_file_names: {error}")
