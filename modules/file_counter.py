import os
import time
import asyncio
#
import modules.logger as logger
from modules.asyncdb_pool import AsyncDatabasePool

class Counter():
    def __init__(self, folder_path, dashboard_db_data, users_db_data):
        self.folder_path = folder_path
        self.dashboard_db_data = dashboard_db_data
        self.users_db_data = users_db_data
        self.pool = AsyncDatabasePool(**self.dashboard_db_data)
        self.users_db_pool = AsyncDatabasePool(**self.users_db_data)
        # print(f"FILE_COUNTER on_startup: Current event loop: {asyncio.get_event_loop()}")
        # print(f"FILE_COUNTER pool object: {self.pool}")

    async def update_database(self, folder_path):
        if not os.path.isdir(folder_path):
            return
        
        # Сохранение имени главной папки в route
        route = os.path.basename(os.path.normpath(folder_path))
        
        count = 0
        not_in_db = []

        folder_files_count = {}
        for folder in os.listdir(folder_path):
            folder_path_full = os.path.join(folder_path, folder)
            if os.path.isdir(folder_path_full):
                folder_files_count[folder] = await count_files_in_directory(folder_path_full)

        async with await self.pool.acquire() as conn:
            for folder_name, files_info in folder_files_count.items():
                user_id = await get_user_id(conn, folder_name)
                if user_id:
                    real_route = await get_route(conn, folder_name)
                    if route.lower() != real_route.lower():
                        await logger.debug(f"[FileCounter] Юзер {folder_name} имеет направление {real_route}, а не {route}! Пропускаю запись данных в БД...")
                        continue
                await conn.execute('''DELETE FROM gamers_files WHERE user_id = ($1)''', user_id)
                if user_id is not None:
                    await update_user_files(conn, user_id, files_info)
                    count += 1
                else:
                    async with await self.users_db_pool.acquire() as connection:
                        user = await is_registered(connection, folder_name)
                    if user:
                        await add_user_to_db(conn, user)
                        user_id = await get_user_id(conn, folder_name)
                    else:
                        not_in_db.append(folder_name)
            # await update_last_send_date(conn, user_id)

        if count:
            await logger.debug(f"[FileCounter] Количество файлов {count} юзеров направления {route} успешно подсчитаны и записаны в БД!")

        if not_in_db:
            not_in_db = ", ".join(not_in_db)
            await logger.debug(f"[FileCounter] Юзеры [{not_in_db}] для [{route}] не найдены в БД!")

    async def count_and_update_loop(self):
        await self.pool.create_pool()
        await self.users_db_pool.create_pool()
        await logger.info("[FileCounter] Счётчик файлов успешно запущен!")
        while True:
            try:
                for sub_dir in os.scandir(self.folder_path):
                    await self.update_database(sub_dir)
            except Exception as error:
                await logger.error(f"[FileCounter] Не удалось завершить сканирование файлов: {error}")
            finally:
                # Ждём перед следующим запуском
                time.sleep(300)

async def get_route(connection, username):
    route = await connection.fetchval("SELECT route FROM gamers WHERE LOWER(username) = LOWER($1)", username)
    return route if route else None


async def is_registered(connection, username):
    # проверяем, зареган-ли игрок вообще
    row = await connection.fetchrow("SELECT username, route FROM users WHERE LOWER(username) = LOWER($1)", username)
    if row:
        return (row['username'], row['route'])
    else:
        return None

async def add_user_to_db(conn, user):
    username = user[0]
    route = user[1]
    # Если пользователь существует, обновляем информацию
    await conn.execute("""
        INSERT INTO gamers(username, route) 
        VALUES ($1, $2)
        """, username, route)

async def get_user_id(conn, username):
    data = await conn.fetchval('''SELECT id FROM gamers WHERE LOWER(username) = LOWER($1)''', username)
    return data if data else None

async def update_last_send_date(conn, user_id):
    await conn.execute('''
                UPDATE gamers
                SET last_send = (
                    SELECT date FROM gamers_files
                    WHERE gamers_files.user_id = gamers.id
                    ORDER BY date DESC
                    LIMIT 1
                );
            ''')

async def update_user_files(conn, user_id, files_info):
    for room_name, date_info in files_info["rooms"].items():
        for date_name, files_count in date_info.items():
            await conn.execute('''
                INSERT INTO gamers_files(user_id, room, date, files) 
                VALUES ($1, $2, $3, $4)
                ON CONFLICT(user_id, room, date) 
                DO UPDATE SET files = excluded.files
            ''', user_id, room_name, date_name.replace('-', '.'), files_count)

async def count_files_in_directory(path):
    room_files_count = {}
    for room_name in os.listdir(path):
        room_path = os.path.join(path, room_name)
        if os.path.isdir(room_path):
            room_files_count[room_name] = {}
            for date_name in os.listdir(room_path):
                date_path = os.path.join(room_path, date_name)
                if os.path.isdir(date_path):
                    files_count = len([f for dp, dn, filenames in os.walk(date_path) for f in filenames])
                    room_files_count[room_name][date_name] = files_count
    total_files_count = sum([sum(date_counts.values()) for date_counts in room_files_count.values()])
    return {"total": total_files_count, "rooms": room_files_count}


def start_process(folder_path, dashboard_db_data, users_db_data):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    counter = Counter(folder_path, dashboard_db_data, users_db_data)
    loop.run_until_complete(counter.count_and_update_loop())

"""
СДЕЛАТЬ:
-
"""
