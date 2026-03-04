from modules.asyncdb_pool import AsyncDatabasePool


async def create_table():
    async with await pool.acquire() as conn:
        await conn.execute('''CREATE TABLE IF NOT EXISTS users (id serial PRIMARY KEY, username TEXT, password TEXT, route TEXT)''')

async def check_user(username):
    # возвращает True, если юзер найден в БД
    # print(f"DB_MANAGER pool object: {pool}")

    async with await pool.acquire() as conn:
        user_route = await conn.fetchval('SELECT route FROM users WHERE LOWER(username)=($1)', username.lower())

    # если такой юзер найден в БД, то
    if user_route:
        # возвращаем истину
        return user_route
    # иначе нет
    return False

async def autorize_user(username, password):
    # print(f"DB_MANAGER pool object: {pool}")
    async with await pool.acquire() as conn:
        valid_password = await conn.fetchval('SELECT password FROM users WHERE LOWER(username)=($1)', username.lower())
    # проверяем, совпал ли пароль
    if password in valid_password:
        return True
    return False

async def add_user(username, password, route):
    async with await pool.acquire() as conn:
        user_id = await conn.fetchval("SELECT id FROM users WHERE LOWER(username) = LOWER($1)", username)
        if user_id:
            return False
        await conn.execute("INSERT INTO users (username, password, route) VALUES ($1, $2, $3)", username, password, route)
        return True

async def delete_user(username):
    async with await pool.acquire() as conn:
        await conn.execute("DELETE FROM users WHERE LOWER(username) = LOWER($1)", username)

async def update_user(user_id, username, password, route):
    async with await pool.acquire() as conn:
        await conn.execute("UPDATE users SET username = $1, password = $2, route = $3 WHERE id = $4", username, password, route, user_id)

async def filter_users(filter_value):
    async with await pool.acquire() as conn:
        if filter_value:
            query = "SELECT * FROM users WHERE LOWER(username) LIKE $1 ORDER BY username"
            rows = await conn.fetch(query, f"%{filter_value}%")
        else:
            rows = await conn.fetch("SELECT * FROM users ORDER BY username")
    return rows

async def main(app):
    # пытаемся подключиться к БД и создать таблицу если её нет
    await pool.create_pool()
    await create_table()


"""
import asyncio
import asyncpg
import os

database_data = {
    "host": '---',
    "port": '8081',
    "user": 'Dragmor',
    "password": '---',
    "database": 'users'
}

class AsyncDatabaseConnection:
    def __init__(self, **params):
        self.connection = None
        self.params = params

    async def __aenter__(self):
        self.connection = await asyncpg.connect(**self.params)
        return self.connection

    async def __aexit__(self, *_):
        await self.connection.close()


# функции для работы с БД авторизационнах данных юзеров

async def create_table():
    async with AsyncDatabaseConnection(**database_data) as conn:
        await conn.execute('''CREATE TABLE IF NOT EXISTS users (id serial PRIMARY KEY, username TEXT, password TEXT, route TEXT)''')

async def check_user(username):
    # возвращает True, если юзер найден в БД
    async with AsyncDatabaseConnection(**database_data) as conn:
        user_route = await conn.fetchval('SELECT route FROM users WHERE LOWER(username)=($1)', username.lower())

    # если такой юзер найден в БД, то
    if user_route:
        # возвращаем истину
        return user_route
    # иначе нет
    return False

async def autorize_user(username, password):
    async with AsyncDatabaseConnection(**database_data) as conn:
        valid_password = await conn.fetchval('SELECT password FROM users WHERE LOWER(username)=($1)', username.lower())
    # проверяем, совпал ли пароль
    if password in valid_password:
        return True
    return False

async def main():
    # пытаемся подключиться создать таблицу если её нет
    await create_table()

"""