import datetime
import os
import uuid
from urllib.parse import unquote

from aiohttp import web
import aiofiles

import modules.logger as logger
from server_app import config, state
from server_app.security import is_safe_component, normalize_relpath, is_valid_auth
from server_app.services.antivirus import scan_file_async, quarantine_file
from server_app.services.redis_queue import enqueue_antivirus


async def handle_upload(request):
    username = None
    try:
        reader = await request.multipart()
        field = await reader.next()
        if field is None:
            return web.Response(status=400)

        filename = None
        room = None
        auth_key = None
        subdirs = ""
        bytes_written = 0
        tmp_path = None

        while field is not None:
            if field.name == "file":
                if not field.filename:
                    return web.Response(status=400)
                filename = unquote(field.filename)
                if os.path.basename(filename) != filename:
                    await logger.debug(f'Невалидное имя файла от "{username}": {filename}')
                    return web.Response(status=400)
                content_length_header = field.headers.get("Content-Length")
                if content_length_header:
                    try:
                        content_length = int(content_length_header)
                        if content_length > config.MAX_UPLOAD_SIZE:
                            return web.Response(status=413)
                    except ValueError:
                        return web.Response(status=400)

                tmp_dir = os.path.join(config.FILES_DIR, "_tmp")
                os.makedirs(tmp_dir, exist_ok=True)
                tmp_name = f"{uuid.uuid4().hex}_{filename}"
                tmp_path = os.path.join(tmp_dir, tmp_name)

                async with aiofiles.open(tmp_path, mode="wb") as f:
                    while True:
                        chunk = await field.read_chunk()
                        if not chunk:
                            break
                        bytes_written += len(chunk)
                        if bytes_written > config.MAX_UPLOAD_SIZE:
                            await f.close()
                            try:
                                os.remove(tmp_path)
                            except OSError:
                                pass
                            return web.Response(status=413)
                        await f.write(chunk)
            else:
                value = await field.text()
                if field.name == "username":
                    username = value
                elif field.name == "room":
                    room = value
                elif field.name == "auth_key":
                    auth_key = value
                elif field.name == "subdirs":
                    subdirs = value

            field = await reader.next()

        if not filename or not username or not room:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
            return web.Response(status=400)

        if not is_safe_component(username) or not is_safe_component(room):
            await logger.debug(
                f'Невалидные параметры пути: username="{username}", room="{room}"'
            )
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
            return web.Response(status=400)
        subdirs = normalize_relpath(subdirs)
        if subdirs is None:
            await logger.debug(
                f'Невалидные параметры пути subdirs="{subdirs}" от "{username}"'
            )
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
            return web.Response(status=400)

        if not is_valid_auth(username, auth_key):
            await logger.debug(f'Ключ пользователя "{username}" невлидный!')
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
            return web.Response(status=301)

        route = state.AUTH_USERS[username.lower()]["route"]
        current_date = datetime.date.today()
        date = current_date.strftime("%Y-%m-%d")

        path = os.path.join(config.FILES_DIR, route, username, room, date, subdirs)
        os.makedirs(path, exist_ok=True)

        async with state.semaphore:
            file_path = os.path.join(path, filename)
            try:
                os.replace(tmp_path, file_path)
            except OSError:
                if tmp_path and os.path.exists(tmp_path):
                    try:
                        os.remove(tmp_path)
                    except OSError:
                        pass
                return web.Response(status=400)
            if config.CLAMAV_ENABLED:
                if config.REDIS_ENABLED:
                    enqueue_antivirus(
                        {
                            "file_path": file_path,
                            "route": route,
                            "username": username,
                            "room": room,
                            "date": date,
                            "subdirs": subdirs,
                        }
                    )
                else:
                    scan_result = await scan_file_async(file_path)
                    if scan_result == "infected":
                        if config.QUARANTINE_ACTION == "ignore":
                            await logger.info(
                                f'Файл "{filename}" от "{username}" отмечен как зараженный, но оставлен по политике'
                            )
                        elif config.QUARANTINE_ACTION == "delete":
                            try:
                                os.remove(file_path)
                            except OSError:
                                pass
                            await logger.info(
                                f'Файл "{filename}" от "{username}" удалён как зараженный'
                            )
                        else:
                            quarantined = quarantine_file(
                                file_path, route, username, room, date, subdirs
                            )
                            await logger.info(
                                f'Файл "{filename}" от "{username}" перемещён в карантин: {quarantined}'
                            )
                        if config.QUARANTINE_ACTION != "ignore":
                            return web.Response(status=422)
                    if scan_result == "error":
                        await logger.error(
                            f'Ошибка антивирусной проверки файла "{filename}" от "{username}"'
                        )
            await logger.debug(
                f'Файл "{filename}" от "{username}" принят! Размер файла: {bytes_written} байт!'
            )

        return web.Response(status=200)
    except Exception as e:
        await logger.error(f"Ошибка при загрузке файла от юзера {username}: {e}")
        return web.Response(status=205)
