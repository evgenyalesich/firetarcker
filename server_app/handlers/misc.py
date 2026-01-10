from aiohttp import web

import modules.logger as logger
import modules.dashboard as dashboard
import modules.file_counter as file_counter
import modules.db_manager as db_manager
from server_app import config, state
from server_app.security import get_real_ip
from server_app.security import parse_structured_data


async def update_send_date(request):
    try:
        data = await request.post()
        username = data.get("username")
        auth_key = data.get("auth_key")

        if username.lower() in state.AUTH_USERS:
            if state.AUTH_USERS[username.lower()]["key"] == auth_key:
                await dashboard.update_send_date(username=username)
                return web.Response(status=200)
        await logger.debug(
            f"{username} не прошёл проверку ключа аутентификации, дата отправки обновлена не будет"
        )
        return web.Response(status=404)
    except Exception as error:
        await logger.error(
            f"Ошибка при попытке обновить дату отправки файлов юзером в БД дешборда: {error}!"
        )


async def get_files_count(request):
    data = await request.post()

    client_secret_key = data.get("secret_key", "")
    if config.SECRET_KEY != client_secret_key:
        real_ip = get_real_ip(request)
        await logger.debug(
            f"Поступил запрос от {real_ip}, но secret_key невалидный: {client_secret_key}"
        )
        return web.Response(status=404)

    if data.get("finish", ""):
        count = int(data.get("count", 0))
        if count > 0:
            route = data.get("route", "")
            await logger.debug(
                f"Количество файлов для {count} юзеров направления {route} успешно приняты и записаны в БД!"
            )
        return web.Response(status=400)

    str_dict = data.get("str_dict")
    folder_files_count = parse_structured_data(str_dict)
    if folder_files_count is None:
        return web.Response(status=400)

    async with await request.app["pool"].acquire() as conn:
        for route, files_data in folder_files_count.items():
            not_in_db = []
            for username, files_info in files_data.items():
                user_id = await file_counter.get_user_id(conn, username)
                if user_id is None:
                    async with await db_manager.pool.acquire() as connection:
                        user = await file_counter.is_registered(connection, username)
                    if user:
                        await file_counter.add_user_to_db(conn, user)
                        user_id = await file_counter.get_user_id(conn, username)
                    else:
                        not_in_db.append(username)
                else:
                    real_route = await file_counter.get_route(conn, username)
                    if route.lower() != real_route.lower():
                        await logger.debug(
                            f"Пришел запрос обновить инфу для юзера {username} с направлением {route}, но реальное направление юзера: {real_route}!"
                        )
                        continue

                    await conn.execute("DELETE FROM gamers_files WHERE user_id = ($1)", user_id)
                    for room_name, date_info in files_info["rooms"].items():
                        for date_name, files_count in date_info.items():
                            await conn.execute(
                                """
                                INSERT INTO gamers_files(user_id, room, date, files) 
                                VALUES ($1, $2, $3, $4)
                                ON CONFLICT(user_id, room, date) 
                                DO UPDATE SET files = excluded.files
                            """,
                                user_id,
                                room_name,
                                date_name.replace("-", "."),
                                files_count,
                            )
            if not_in_db:
                not_in_db = ", ".join(not_in_db)
                await logger.debug(f"Юзеры [{not_in_db}] для [{route}] не найдены в БД!")
                not_in_db = []

    return web.Response(status=400)


async def handle_ping(request):
    return web.Response(status=200)
