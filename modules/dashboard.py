import aiohttp_jinja2
import modules.logger as logger
import hashlib
#
from aiohttp import web
from aiohttp_session import setup, get_session
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from datetime import datetime
from multiprocessing import Process
#
import modules.file_counter as file_counter
# import modules.ds_mailer.notifier as notifier
from modules.asyncdb_pool import AsyncDatabasePool
import modules.db_manager as db_manager

# роли юзеров
roles = {
        0: "support",
        1: "moderator",
        2: "admin"
    }

async def init_db(app):
    # print(f"DASHBOARD pool object: {pool}")
    await pool.create_pool()
    async with await pool.acquire() as conn:
        await conn.execute('''CREATE TABLE IF NOT EXISTS users 
                                (id serial PRIMARY KEY, 
                                username TEXT, 
                                password TEXT, 
                                route TEXT, 
                                role TEXT)''')

        await conn.execute('''CREATE TABLE IF NOT EXISTS gamers 
                                (id serial PRIMARY KEY, 
                                username TEXT, 
                                password TEXT, 
                                route TEXT,
                                timezone TEXT, 
                                last_launch TEXT, 
                                last_send TEXT)''')

        # таблица содержит записи по каждому юзеру (рум, дата (равное имени папки), кол-во файлов в ней)
        await conn.execute('''CREATE TABLE IF NOT EXISTS gamers_files 
                                (id serial PRIMARY KEY, 
                                user_id INTEGER NOT NULL, 
                                room TEXT NOT NULL, date DATE NOT NULL, 
                                files INTEGER NOT NULL, 
                                CONSTRAINT gamers_files_user_room_date_unq UNIQUE (user_id, room, date), 
                                CONSTRAINT gamers_files_user_id_fkey FOREIGN KEY (user_id)
                                REFERENCES public.gamers (id)
                                ON UPDATE NO ACTION
                                ON DELETE NO ACTION)''')

        
    # запуск процесса для подчсёта файлов
    counter_process = Process(target=file_counter.start_process, args=(FILES_DIR, dashboard_db_data, users_db_data))
    counter_process.start()

    # 06.06.2024 Машерчик попросила отключить этот функционал
    # ds_mailer = Process(target=notifier.start)
    # ds_mailer.start()

async def fetch_user_rooms(gamer_id):
    # print(f"DASHBOARD pool object: {pool}")
    """Загрузка уникальных значений room из БД для определенного юзера."""
    async with await pool.acquire() as conn:
        data = await conn.fetch('''SELECT DISTINCT room FROM gamers_files WHERE user_id = ($1)''', gamer_id)
    return [row['room'] for row in data]

async def fetch_gamers():
    """Загрузка данных игроков из БД."""
    async with await pool.acquire() as conn:
        data = await conn.fetch('''SELECT * FROM gamers ORDER BY id''')
    return [dict(row) for row in data]

async def update_time_offset(username, offset):
    async with await pool.acquire() as conn:
        await conn.execute("UPDATE gamers SET timezone = $1 WHERE LOWER(username) = LOWER($2)", offset, username)

# возвращает JSON всех юзеров из БД (для дешборда) /get_data
async def get_data(request):
    session = await get_session(request)
    gamers_with_rooms_and_files = []  # Это список, который в конечном итоге будет конвертирован в JSON
    async with await pool.acquire() as conn:
        gamers = await fetch_gamers() 
        for gamer in gamers:
            # Получаем данные о комнатах и файлах
            rooms_records = await conn.fetch('''SELECT DISTINCT room, date, files FROM gamers_files WHERE user_id = ($1)''', gamer['id'])
            rooms = [{"name": rec['room'], "date": rec['date'], "files": rec['files']} for rec in rooms_records]

            total_files_info = await conn.fetch('''SELECT SUM(files) as total_files FROM gamers_files WHERE user_id = ($1)''', gamer['id'])
            total_files = total_files_info[0]['total_files'] if total_files_info[0]['total_files'] else 0
            last_launch = gamer['last_launch'] if gamer['last_launch'] else 0
            last_send = gamer['last_send'] if gamer['last_send'] else 0

            gamers_with_rooms_and_files.append({
                'id': gamer['id'],
                'username': gamer['username'],
                'route': gamer['route'],
                'last_launch': last_launch,
                'last_send': last_send,
                'rooms': rooms,
                'total_files': total_files,
                'timezone': gamer['timezone']
            })
    return web.json_response(gamers_with_rooms_and_files)

async def fetch_gamers_with_rooms_and_files():
    """Загрузка данных игроков из БД, включая уникальные room и сумму файлов."""
    async with await pool.acquire() as conn:
        gamers_with_files = []
        gamers = await fetch_gamers()
        for gamer in gamers:
            rooms = await fetch_user_rooms(gamer['id'])
            total_files_info = await conn.fetch('''SELECT SUM(files) as total_files FROM gamers_files WHERE user_id = ($1)''', gamer['id'])
            total_files = total_files_info[0]['total_files'] if total_files_info[0]['total_files'] else 0
            last_launch = gamer['last_launch'] if gamer['last_launch'] else 0
            last_send = gamer['last_send'] if gamer['last_send'] else 0

            gamers_with_files.append({
                'id': gamer['id'],
                'username': gamer['username'],
                'route': gamer['route'],
                'last_launch': last_launch,
                'last_send': last_send,
                'rooms': rooms,
                'total_files': total_files,
                'timezone': gamer['timezone'] or ""
            })

        return gamers_with_files

async def fetch_routes():
    """Загрузка уникальных направлений из БД"""
    async with await pool.acquire() as conn:
        data = await conn.fetch('''SELECT DISTINCT route FROM gamers WHERE route IS NOT NULL ORDER BY route''')
    return [row['route'] for row in data]

async def set_launch_date(username, route):
    current_date = datetime.now().strftime('%Y.%m.%d')  # Текущая дата в формате ГГГГ.ММ.ДД
    async with await pool.acquire() as conn:
        user = await conn.fetchval('''SELECT id FROM gamers WHERE LOWER(username) = LOWER($1)''', username)

        if user is None:
            # Если пользователь не найден, добавляем его в базу данных
            await conn.execute("""INSERT INTO gamers 
                (username, route, last_launch, last_send) 
                VALUES ($1, $2, $3, $4)""", 
                username, route, current_date, '0')
        else:
            await conn.execute("""UPDATE gamers 
                SET route = ($1), last_launch = ($2)
                WHERE LOWER(username) = LOWER($3)""", 
                route, current_date, username)

async def update_send_date(username):
    current_date = datetime.now().strftime('%Y.%m.%d')  # Текущая дата в формате ГГГГ.ММ.ДД
    async with await pool.acquire() as conn:
        user = await conn.fetchval('''SELECT id FROM gamers WHERE LOWER(username) = LOWER($1)''', username)
        if user is None:
            return
        else:
            await conn.execute("""UPDATE gamers 
                SET last_send = ($1) 
                WHERE LOWER(username) = LOWER($2)""", 
                current_date, username)

async def update_files_count(username, files_count):
    pass
    # async with aiosqlite.connect(DATABASE) as db:
    #     # Проверяем существование пользователя в базе данных
    #     cursor = await db.execute("SELECT id FROM gamers WHERE username = ?", (username,))
    #     user = await cursor.fetchone()
    #     if user is None:
    #         return
    #     else:
    #         # Если пользователь существует, обновляем информацию
    #         await db.execute("""
    #             UPDATE gamers 
    #             SET hands = ?
    #             WHERE username = ?
    #         """, (files_count, username))
    #         await db.commit()

async def get_files_count(request):
    session = await get_session(request)
    if 'user' not in session:
        raise web.HTTPUnauthorized(reason="User is not authenticated")

    user_id = int(request.query.get('user_id'))
    room = request.query.get('room', '')

    async with await pool.acquire() as conn:
        last_send_query = '''
            SELECT MAX(date) as last_send_date FROM gamers_files
            WHERE user_id = ($1)
            '''
        last_send_params = [user_id]
        if room:
            last_send_query += " AND room = ($2)"
            last_send_params += [room]

        last_send_date_info = await conn.fetchval(last_send_query, *last_send_params)

        total_files_query = """
            SELECT SUM(files) as total_files
            FROM gamers_files
            WHERE user_id = ($1)
            """
        params = [user_id]
        if room:
            total_files_query += " AND room = ($2)"
            params += [room]

        total_files = await conn.fetchval(total_files_query, *params)

        response_data = {
            'total_files': total_files if total_files else 0,
            'last_send': last_send_date_info if last_send_date_info else 0
        }

        return web.json_response(response_data)


@aiohttp_jinja2.template('do_login.html') 
async def do_login(request):
    if request.method == 'POST':
        data = await request.post()
        username = data.get('login')
        password = data.get('password')
        async with await pool.acquire() as conn:
            user = await conn.fetchval("SELECT * FROM users WHERE LOWER(username) = LOWER($1) AND password = ($2)", username, password)
        if user is None:
            # Передаем сообщение о неправильном логине/пароле в контексте
            return {'message': 'Неверный логин или пароль!'}
        await logger.info(f"Пользователь {username} успешно авторизовался.")
        session = await get_session(request)
        sha_password = hashlib.sha256(password.encode()).hexdigest()
        session['user'] = username
        session['password'] = sha_password # записываем хеш пароля в куки
        raise web.HTTPFound('/users')  # Переадресация
    else:
        # Для GET запроса, просто показываем страницу входа без сообщения
        return {'message': ''}

@aiohttp_jinja2.template('login.html')
async def login(request):
    """Страница для авторизации."""
    # Проверяем, есть ли уже установленная сессия
    session = await get_session(request)

    if (user := session.get("user", None)) and (password := session.get("password", None)):
        # извлекаем пароль для юзера из БД
        async with await pool.acquire() as conn:
            valid_password = await conn.fetchval("SELECT password FROM users WHERE LOWER(username) = LOWER($1)", user)
        # если получилось извлечь
        if valid_password:
            # получаем хеш
            sha_password = hashlib.sha256(valid_password.encode()).hexdigest()
            # сравниваем
            if password == sha_password:
                return web.HTTPFound('/users')  # Перенаправление на страницу пользователей
    return

async def logout(request):
    # для выхода из аккаунта
    session = await get_session(request)
    session['user'] = None
    session['password'] = None
    # перекидываем на страницу авторизации
    return web.HTTPFound('/')

@aiohttp_jinja2.template('dashboard_table.html')
async def users(request):
    """Страница для авторизованных пользователей."""
    # print(f"DASHBOARD pool object: {pool}")
    session = await get_session(request)

    if (user := session.get("user", None)) and (password := session.get("password", None)):
        # извлекаем пароль для юзера из БД
        async with await pool.acquire() as conn:
            creds = await conn.fetch("SELECT password, role FROM users WHERE LOWER(username) = LOWER($1)", user)
        creds = [dict(row) for row in creds][0]
        # если получилось извлечь
        if creds.get("password", None):
            # получаем хеш
            sha_password = hashlib.sha256(creds.get("password").encode()).hexdigest()
            # сравниваем
            if password != sha_password:
                return web.HTTPFound('/')
        else:
            return web.HTTPFound('/')
    else:
        return web.HTTPFound('/')  # Неавторизованных пользователей отправляем на страницу логина
    # получаем роль юзера
    role = int(creds.get('role', 0))

    unique_routes = await fetch_routes()

    # Опции для выпадающего списка
    route_options = [route for route in unique_routes]

    gamers = await fetch_gamers_with_rooms_and_files()

    # получаем всех юзеров для users_manager
    rows = await db_manager.filter_users(filter_value=None)
    # Сортировка результатов по ключу "id" в порядке убывания
    sorted_rows = sorted(rows, key=lambda x: x['id'], reverse=True)

    return {"role": role,
            "gamers": gamers,
            "route_options": route_options,
            'users': [dict(row) for row in sorted_rows]}

async def add_user(request):
    data = await request.post()
    username = data.get('username')
    password = data.get('password')
    route = data.get('route')
    if len(username) < 4 or len(password) < 4:
        return web.Response(text="Имя пользователя или пароль слишком короткий!", status=400)

    result = await db_manager.add_user(username=username, password=password, route=route)
    if not result:
        return web.Response(text="Пользователь с таким никнеймом уже существует!", status=400)

    return web.HTTPFound('/')

async def delete_user(request):
    data = request.query
    username = data.get('username')
    session = await get_session(request)
    if (user := session.get("user", None)) and (password := session.get("password", None)):
        # извлекаем пароль для юзера из БД
        async with await pool.acquire() as conn:
            creds = await conn.fetch("SELECT password, role FROM users WHERE LOWER(username) = LOWER($1)", user)
        creds = [dict(row) for row in creds][0]
        # если получилось извлечь
        if creds.get("password", None):
            # получаем хеш
            sha_password = hashlib.sha256(creds.get("password").encode()).hexdigest()
            # сравниваем пароли и админ-ли это
            if password == sha_password and int(creds.get('role', 0)) == 2:
                await db_manager.delete_user(username=username)
                return web.HTTPFound('/')
    return web.Response(text="У Вас недостаточно прав для выполнения данной операции!", status=400)    


async def update_user(request):
    data = await request.post()
    user_id = int(data.get('user_id'))
    username = data.get('username')
    password = data.get('password')
    route = data.get('route')
    # проверяем длину лоигна и пароля
    if len(username) < 4 or len(password) < 4:
        return web.Response(text="Имя пользователя или пароль слишком короткий!", status=400) 

    session = await get_session(request)
    if (user := session.get("user", None)) and (pas := session.get("password", None)):
        # извлекаем пароль для юзера из БД
        async with await pool.acquire() as conn:
            creds = await conn.fetch("SELECT password, role FROM users WHERE LOWER(username) = LOWER($1)", user)
        creds = [dict(row) for row in creds][0]
        # если получилось извлечь
        if creds.get("password", None):
            # получаем хеш
            sha_password = hashlib.sha256(creds.get("password").encode()).hexdigest()
            # сравниваем пароли и кто это админ/модератор
            if pas == sha_password and int(creds.get('role', 0)) > 0:
                await db_manager.update_user(user_id=user_id, username=username, password=password, route=route)
                async with await pool.acquire() as conn:
                    await conn.execute("UPDATE gamers SET route = $1 WHERE LOWER(username) = LOWER($2)", route, username)
                return web.HTTPFound('/')
    return web.Response(text="У Вас недостаточно прав для выполнения данной операции!", status=400)

async def filter_users(request):
    data = request.query
    filter_value = data.get('search', '').lower()
    rows = await db_manager.filter_users(filter_value=filter_value)
    # Сортировка результатов по ключу "id" в порядке убывания
    sorted_rows = sorted(rows, key=lambda x: x['id'], reverse=True)
    return web.json_response([dict(row) for row in sorted_rows])