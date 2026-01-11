import os

from aiohttp import web

import modules.logger as logger
from server_app import state
from server_app.security import is_safe_component, is_valid_auth


async def check_notice(request):
    data = await request.post()
    username = data.get("username")
    auth_key = data.get("auth_key")

    if not is_safe_component(username):
        return web.Response(status=400)

    if is_valid_auth(username, auth_key):
        file_path = os.path.join("notice", f"{username}.txt")
        if os.path.exists(file_path):
            with open(file=file_path, mode="r", encoding="utf8") as file:
                notice_text = file.read()
            await logger.info(f"Пользователю {username} отправлено уведомление!")
            return web.Response(status=400, text=notice_text)

    return web.Response(status=404)


async def delete_notice(request):
    data = await request.post()
    username = data.get("username")
    auth_key = data.get("auth_key")
    if not is_safe_component(username):
        return web.Response(status=400)
    if is_valid_auth(username, auth_key):
        file_path = os.path.join("notice", f"{username}.txt")
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                await logger.info(f"Пользователь {username} успешно получил уведомление!")
            except Exception as error:
                await logger.error(
                    f"Ошибка при удалении файла уведомления юзера {username}: {error}"
                )

    return web.Response(status=400)
