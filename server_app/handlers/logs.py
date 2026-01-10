import datetime
import os

from aiohttp import web
import aiofiles
from aiohttp_session import get_session

import modules.logger as logger
from server_app.security import get_real_ip, is_safe_component


async def handle_errorlog(request):
    try:
        data = await request.post()
        current_date = datetime.date.today().strftime("%Y-%m-%d")
        current_time = datetime.datetime.now().strftime("%H:%M:%S")
        username = data.get("username")
        error = data.get("error")
        if not is_safe_component(username):
            return web.Response(status=400)
        await logger.error(f'Ошибка у юзера: "{username}"')
        try:
            await logger.error(error)
        except Exception:
            pass
        try:
            if not os.path.exists("user_logs"):
                os.makedirs("user_logs")
            if not os.path.exists(os.path.join("user_logs", username)):
                os.makedirs(os.path.join("user_logs", username))
            with open(
                f"{os.path.join('user_logs', username, current_date)}.txt",
                mode="ab",
            ) as f:
                f.write(f"{current_time} [{username}] >> {error}\n".encode("cp1251"))
            await logger.info("Лог ошибки записан успешно!")
        except Exception as e:
            await logger.error(f"Не удалось записать лог. Ошибка: {e}")
        return web.Response(status=200)
    except Exception as error:
        await logger.error(f"Ошибка в handle_errorlog: {error}")


async def handle_log(request):
    try:
        data = await request.post()
        username = data.get("username")
        real_ip = get_real_ip(request)
        if username == "":
            username = real_ip
        error = data.get("error")
        try:
            await logger.debug(f'У юзера: "{username}": {error}')
        except Exception:
            pass
        return web.Response(status=200)
    except Exception as error:
        await logger.error(f"Ошибка в handle_log: {error}")


async def handle_logs(request):
    session = await get_session(request)
    if "user" not in session:
        raise web.HTTPUnauthorized(reason="User is not authenticated")
    logs = {}
    for log_type in ["debug", "info", "request", "error"]:
        async with aiofiles.open(
            f"logs/{log_type}.log", mode="r", encoding="utf-8"
        ) as f:
            logs[log_type] = await f.read()
    return web.json_response(logs)
