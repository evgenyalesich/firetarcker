import random
from aiohttp import web

import modules.db_manager as db_manager
import modules.logger as logger
import modules.dashboard as dashboard
from server_app import config, state
from server_app.security import get_real_ip


async def get_server(request):
    try:
        data = await request.post()
        username = data.get("username")
        route = state.AUTH_USERS[username.lower()]["route"]

        auth_key = data.get("auth_key")
        if username.lower() not in state.AUTH_USERS:
            await logger.debug(f'Ключ пользователя "{username}" невлидный!')
            return web.Response(status=301)
        if state.AUTH_USERS[username.lower()]["key"] != auth_key:
            await logger.debug(f'Ключ пользователя "{username}" невлидный!')
            return web.Response(status=301)

        if route in state.SERVERS:
            if state.SERVERS[route]:
                return web.Response(status=200, text=str([state.SERVERS[route], route]))
        return web.Response(status=404)
    except Exception as error:
        await logger.error(f"Ошибка в get_server: {error}")


async def handle_login(request):
    try:
        data = await request.post()
        username = data.get("username")
        password = data.get("password")
        user_timezone_offset = data.get("time_offset", None)
        await logger.debug(f'Попытка авторизации юзера: "{username}" - "{password}"')
        route = await db_manager.check_user(username)
        if route:
            if await db_manager.autorize_user(username=username, password=password):
                auth_key = "".join(
                    list(
                        map(
                            lambda sym: list(
                                map(
                                    chr,
                                    list(range(48, 58))
                                    + list(range(65, 91))
                                    + list(range(97, 123)),
                                )
                            )[random.randint(0, 61)],
                            list(range(16)),
                        )
                    )
                )
                await logger.debug(f"Сгенерирован ключ аутентификации: {auth_key}")
                state.AUTH_USERS[username.lower()] = {"key": auth_key, "route": route}
                await logger.info(f"Авторизован юзер: {username}. Направление: {route}")
                try:
                    await dashboard.set_launch_date(username=username, route=route)
                    if user_timezone_offset:
                        await dashboard.update_time_offset(
                            username=username, offset=user_timezone_offset
                        )
                except Exception as error:
                    await logger.error(
                        f"Ошибка в handle_login при обновлении данных юзера: {error}"
                    )

                state.MANAGER.AUTH_USERS = state.AUTH_USERS
                return web.Response(status=205, text=auth_key)
            return web.Response(status=505)
        return web.Response(status=506)
    except Exception as error:
        await logger.error(f"Ошибка в handle_login: {error}")


async def get_key(request):
    data = await request.post()
    real_ip = get_real_ip(request)

    client_secret_key = data.get("secret_key", "")
    if config.SECRET_KEY != client_secret_key:
        await logger.debug(
            f"Поступил запрос от {real_ip}, но secret_key невалидный: {client_secret_key}"
        )
        return web.Response(status=520)

    username = data.get("username")

    await logger.debug(f"Запрос на проверку ключа юзера {username}")
    if username.lower() in state.AUTH_USERS:
        try:
            key = state.AUTH_USERS[username.lower()]["key"]
            await logger.debug(f"Ключ {username} был успешно отправлен!")
            return web.Response(status=200, text=key)
        except Exception as error:
            await logger.error(f"Ошибка в get_key: {error}")
            return web.Response(status=520)

    await logger.debug(f"{username} не был авторизован!")
    return web.Response(status=401)
