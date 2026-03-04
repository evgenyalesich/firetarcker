from aiohttp import web
from urllib.parse import unquote, urlparse
from multiprocessing import Process, Manager
from aiohttp_session import setup
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from aiohttp_session import setup, get_session

import datetime
import os
import random
import zipfile
import time
import io
import sys
import hashlib
import json
import requests
import threading
import aiohttp_jinja2
import jinja2
import aiofiles
import asyncio
#
import modules.db_manager as db_manager
import modules.logger as logger
import modules.layout_processor as layouts
import modules.dashboard as dashboard
import modules.file_counter as file_counter
from modules.asyncdb_pool import AsyncDatabasePool


async def get_server(request):
    try:
        # возвращает адрес сервера, которому юзер отправит файлы
        data = await request.post()
        username = data.get('username')
        # считываем направление игрока
        route = AUTH_USERS[username.lower()]["route"]

        # проверяем ключ на валидность
        auth_key = data.get('auth_key')
        # если ключ доступа у юзера невалидный
        if username.lower() not in AUTH_USERS:
            await logger.debug(f'Ключ пользователя "{username}" невлидный!')
            return web.Response(status=301)
        else:
            if AUTH_USERS[username.lower()]["key"] != auth_key:
                await logger.debug(f'Ключ пользователя "{username}" невлидный!')
                return web.Response(status=301)

        # если в servers.json есть Ip для данного направления
        if route in SERVERS:
            if SERVERS[route]:
                # возвращаем ip:port куда юзер будет отправлять файлы
                return web.Response(status=200, text=str([SERVERS[route], route]))
        # если не найден - отправляем 404
        return web.Response(status=404)
    except Exception as error:
        await logger.error(f"Ошибка в get_server: {error}")

async def handle_login(request):
    try:
        # для авторизации юзера
        global AUTH_USERS, MANAGER
        data = await request.post()
        username = data.get('username')
        password = data.get('password')
        user_timezone_offset = data.get('time_offset', None)
        await logger.debug(f'Попытка авторизации юзера: "{username}" - "{password}"')
        # если такой юзер есть в БД
        # сразу считываем его направление
        route = await db_manager.check_user(username)
        if route:
            if await db_manager.autorize_user(username=username, password=password):
                auth_key = ''.join(list(map(lambda sym: list(map(chr, list(range(48, 58))+list(range(65, 91))+list(range(97, 123))))[random.randint(0, 61)], list(range(16)))))
                await logger.debug(f"Сгенерирован ключ аутентификации: {auth_key}")
                AUTH_USERS[username.lower()] = {"key": auth_key, "route": route} # добавляем сгенереный ключ в словарь авторизованных юзеров
                await logger.info(f"Авторизован юзер: {username}. Направление: {route}")
                try:
                    # записываем в БД время последнего запуска трекера
                    await dashboard.set_launch_date(username=username, route=route)
                    # offset передается только из аплоадера, чтобы записать временную зону юзера
                    if user_timezone_offset:
                        await dashboard.update_time_offset(username=username, offset=user_timezone_offset)
                except Exception as error:
                    await logger.error(f"Ошибка в handle_login при обновлении данных юзера: {error}")

                MANAGER.AUTH_USERS = AUTH_USERS
                return web.Response(status=205, text=auth_key)
                # Успешная авторизация
            else:
                return web.Response(status=505)
                # Неверный пароль
        else:
            return web.Response(status=506)
            # Данный юзер не зарегистрирован
    except Exception as error:
        await logger.error(f"Ошибка в handle_login: {error}")


async def handle_upload(request):
    username = None
    # хендлер для приёма файла от юзера
    try:
        reader = await request.multipart()
        field = await reader.next()
        filename = unquote(field.filename)  # Декодирование URL-кодированного имени файла
        # Чтение файла в оперативную память
        file_data = await field.read()
        file_size = content_length = int(field.headers['Content-Length'])  # Получение размера файла
        # Создание буферного объекта BytesIO
        buffer = io.BytesIO(file_data)

        # Получение значения дополнительного поля
        data = await request.post()
        username = data.get('username')
        room = data.get('room')
        auth_key = data.get('auth_key')
        subdirs = data.get('subdirs')



        if username.lower() not in AUTH_USERS:
            await logger.debug(f'Ключ пользователя "{username}" невлидный!')
            return web.Response(status=301)
        else:
            if AUTH_USERS[username.lower()]["key"] != auth_key:
                await logger.debug(f'Ключ пользователя "{username}" невлидный!')
                return web.Response(status=301)



        # считываем направление игрока
        route = AUTH_USERS[username.lower()]["route"]
        current_date = datetime.date.today()
        # текущая дата в виде гггг-мм-дд
        date = current_date.strftime("%Y-%m-%d")

        # путь, в котором будем искать файлы
        path = os.path.join(FILES_DIR, route, username, room, date, subdirs)
        os.makedirs(path, exist_ok=True)

        async with semaphore:
            async with aiofiles.open(os.path.join(path, filename), mode='wb') as f:
                await f.write(buffer.getvalue())
            await logger.debug(f'Файл "{filename}" от "{username}" принят! Размер файла: {file_size} байт!')

        return web.Response(status=200)
    except Exception as e:
        await logger.error(f"Ошибка при загрузке файла от юзера {username}: {e}")
        return web.Response(status=205)


async def get_files_list(request):
    global USERS_FILES

    # новая версия сбора данных о файлах юзера на сервере
    data = await request.post()
    username = data.get('username')
    room = data.get('room')
    auth_key = data.get('auth_key')
    route = data.get('route')

    # ТУТ НУЖНО ПРОВЕРИТЬ НАЛИЧИЕ ПАПОК ПОДПАПОК И ФАЙЛОВ. ЕСЛИ ОТСУТСТВУЮТ - ВЕРНУТЬ NONE

    if username.lower() not in AUTH_USERS:
        await logger.debug(f'Ключ пользователя "{username}" невлидный!')
        return web.Response(status=301)
    else:
        if AUTH_USERS[username.lower()]["key"] != auth_key:
            await logger.debug(f'Ключ пользователя "{username}" невлидный!')
            return web.Response(status=301)

    # если для юзера нет списка файлов, и не идёт скан каталогов для него:
    if username not in USERS_FILES:
        # добавляем в словарь юзера со значением None
        USERS_FILES[username] = None


        # запускаем поток сканирования файлов
        thread = threading.Thread(target=scan_files, args=(username, room, route,))
        thread.daemon = True
        thread.start()

        return web.Response(status=300)

    else:
        # если в словаре уже есть юзер, и его значение None
        if USERS_FILES[username] == None:
            # значит уже запущен поток скана файлов
            return web.Response(status=300)
        # если-же значение по ключу не равно None, значит там данные о файлах
        else:
            # записываем данные во временную переменную
            files_list = USERS_FILES[username]
            # удаляем из словаря данные
            del USERS_FILES[username]
            # возвращаем клиенту данные
            return web.Response(status=400, text=str(files_list))


def scan_files(username, room, route):
    # новый метод сбора файлов в потоке
    global USERS_FILES
    # Засекаем начальное время
    start_time = time.perf_counter() #<<=============================================================================================================================

    # путь, в котором будем искать файлы
    path = os.path.join(FILES_DIR, route, username, room)
    logger.sync_debug(f"Поступил запрос от {username} на получение списка файлов рума: {room}")

    # получаем список всех файлов в этой папке и вложенных подпапках
    # Собираем имена файлов и их контрольные суммы
    file_info = []
    if not os.path.exists(path):
        os.makedirs(path)
    subfolders = [f.path for f in os.scandir(path) if f.is_dir()]
    # проходимся по подкаталогам первого уровня вложенности (папка с именем = текущей дате)
    for subfolder in subfolders:
        if os.path.exists(subfolder):
            for root, dirs, files in os.walk(subfolder):
                for file in files:
                    relative_path = os.path.relpath(os.path.join(root, file), subfolder)
                    file_path = os.path.normpath(os.path.join(root, file))

                    # просчитываем хеш только для db-файлов
                    if file.lower().endswith("db"):
                        # Вычисляем MD5 контрольную сумму файла
                        with open(file_path, mode='rb') as f:
                            md5_hash = hashlib.md5()
                            while chunk := f.read(4096):
                                md5_hash.update(chunk)
                            checksum = md5_hash.hexdigest()
                    else:
                        checksum = None

                    file_info.append([relative_path, checksum])

    # Засекаем конечное время#<<=============================================================================================================================
    end_time = time.perf_counter()#<<=============================================================================================================================
    # Вычисляем время выполнения#<<=============================================================================================================================
    execution_time = end_time - start_time#<<=============================================================================================================================
    # Выводим затраченное время#<<=============================================================================================================================
    logger.sync_debug(f"Время просчёта файлов рук для {username}: {execution_time} сек. Файлов: {len(file_info)}")#<<=============================================================================================================================

    USERS_FILES[username] = file_info


async def get_file_names(path):
    try:
        # Собираем имена файлов и их контрольные суммы
        file_info = []
        if not os.path.exists(path):
            os.makedirs(path)
        subfolders = [f.path for f in os.scandir(path) if f.is_dir()]
        # проходимся по подкаталогам первого уровня вложенности (папка с именем = текущей дате)
        for subfolder in subfolders:
            if os.path.exists(subfolder):
                for root, dirs, files in os.walk(subfolder):
                    for file in files:
                        relative_path = os.path.relpath(os.path.join(root, file), subfolder)
                        file_path = os.path.normpath(os.path.join(root, file))
                        # Вычисляем MD5 контрольную сумму файла
                        with open(file_path, mode='rb') as f:
                            md5_hash = hashlib.md5()
                            while chunk := f.read(4096):
                                md5_hash.update(chunk)
                            checksum = md5_hash.hexdigest()

                        file_info.append([relative_path, checksum])
        return file_info
    except Exception as error:
        await logger.error(f"Ошибка в get_file_names: {error}")


async def handle_errorlog(request):
    try:
        # для записи ошибки в лог юзера
        data = await request.post()
        current_date = datetime.date.today().strftime("%Y-%m-%d")
        current_time = datetime.datetime.now().strftime("%H:%M:%S")
        username = data.get('username')
        error = data.get('error')
        await logger.error(f'Ошибка у юзера: "{username}"')
        try:
            await logger.error(error)
        except:
            pass
        #
        try:
            if not os.path.exists("user_logs"):
                os.makedirs("user_logs")
            if not os.path.exists(os.path.join("user_logs", username)):
                os.makedirs(os.path.join("user_logs", username))
            with open(f"{os.path.join('user_logs', username, current_date)}.txt", mode='ab') as f:
                # print(error)
                f.write(f"{current_time} [{username}] >> {error}\n".encode("cp1251"))
            await logger.info("Лог ошибки записан успешно!")
        except Exception as e:
            await logger.error(f"Не удалось записать лог. Ошибка: {e}")
        return web.Response(status=200)
    except Exception as error:
        await logger.error(f"Ошибка в handle_errorlog: {error}")


async def handle_log(request):
    try:
        # для записи ошибки в лог юзера
        data = await request.post()
        username = data.get('username')
        real_ip = request.headers.get('X-Forwarded-For', '').split(',')[0].strip()
        if not real_ip:
            real_ip = request.headers.get('X-Real-IP', '').strip()
        if username == "":
            username = real_ip
        error = data.get('error')
        try:
            await logger.debug(f'У юзера: "{username}": {error}')
        except:
            pass
        return web.Response(status=200)
    except Exception as error:
        await logger.error(f"Ошибка в handle_log: {error}")

async def get_update_v2(request):
    # отправляет файл с обновой клиенту
    filepath = "update_v2.zip"
    return web.FileResponse(filepath)

async def check_update_v2(request):
    try:
        # проверяет файл обновления на сервере
        await logger.debug("Поступил запрос на актуальную версию ПО v2")
        # отправляет актуальную версию ПО и ссылку для её скачивания
        if not os.path.exists("update_v2.zip"):
            # если нет файла с обновой
            return web.Response(status=303, text="")
        # Чтение архива
        zip_filename = 'update_v2.zip'
        with zipfile.ZipFile(zip_filename, 'r') as zip_file:
            # Получение комментария архива в виде байтов
            comment_bytes = zip_file.comment
            # Декодирование комментария в строку
            update_version = comment_bytes.decode('utf-8')
        # возвращаем номер версии
        return web.Response(status=303, text=update_version)
    except Exception as error:
        await logger.error(f"Ошибка в check_update_v2: {error}")

async def get_layout(request):
    try:
        global PATH_LAYOUTS
        #принимает имя рума и имена файлов, которые нужно отправить юзеру. соберает в архив и отправляет.
        # если нет файлов, или ошибка, то оправляет соответствующие status. Можно попробовать через lambda+multiprocessing
        data = await request.post()
        room = data.get('room')

        constructed = data.get('constructed') # словарь в виде строки
        constructed = eval(constructed) # переводим в нормальный словарь
        await logger.debug(f"Поступил запрос на сборку лейаута room: {room}\ndata: {constructed}")

        if room not in PATH_LAYOUTS:
            # ищем файл путей сборки
            if os.path.exists(f"layouts/{room}/paths.json"):
                with open(f"layouts/{room}/paths.json", "r") as file:
                    try:
                        PATH_LAYOUTS[room] = json.load(file)
                    except Exception as error:
                        await logger.error(f"Не удалось прочитать файл путей лейаута. Ошибка: {error}")
                        return web.Response(status=405)
            else:
                await logger.debug("Невозможно собрать данный лейаут, т.к. нет нужных файлов!")
                return web.Response(status=406)

        # архив лейаута в ОЗУ
        zip_layout = await layouts.pack_layout(room_name=room, data=constructed, paths=PATH_LAYOUTS[room])

        # если лейаут удачно собран
        if zip_layout:
            # Создаем HTTP-ответ с файлом в виде архива
            response = web.Response(status=200, body=zip_layout)
            response.content_type = 'application/zip'
            response.headers['Content-Disposition'] = 'attachment; filename="archive.zip"'
            await logger.info(f"Успешно собран и отправлен лейаут для рума {room}")
            return response
        # если не удалось собрать
        else:
            await logger.debug("Не удалось собрать zip-архив лейаута!")
            return web.Response(status=404, text="Can't pack layout!") # если не удалось собрать лейаут
    except Exception as error:
        await logger.error(f"Ошибка в get_layout: {error}")

async def update_send_date(request):
    try:
        data = await request.post()
        username = data.get('username') # имя юзера
        auth_key = data.get('auth_key')

        if username.lower() in AUTH_USERS:
            if AUTH_USERS[username.lower()]["key"] == auth_key:
                await dashboard.update_send_date(username=username)
                return web.Response(status=200)
        await logger.debug(f"{username} не прошёл проверку ключа аутентификации, дата отправки обновлена не будет")
        return web.Response(status=404)
    except Exception as error:
        await logger.error(f"Ошибка при попытке обновить дату отправки файлов юзером в БД дешборда: {error}!")

async def get_key(request):
    data = await request.post()
    real_ip = request.headers.get('X-Forwarded-For', '').split(',')[0].strip()
    if not real_ip:
        real_ip = request.headers.get('X-Real-IP', '').strip()

    client_secret_key = data.get('secret_key', '')
    if secret_key != client_secret_key:
        await logger.debug(f"Поступил запрос от {real_ip}, но secret_key невалидный: {client_secret_key}")
        return web.Response(status=520)

    username = data.get('username') # имя юзера

    await logger.debug(f"Запрос на проверку ключа юзера {username}")
    if username.lower() in AUTH_USERS:
        try:
            route = AUTH_USERS[username.lower()]["route"] # направление юзера
            key = AUTH_USERS[username.lower()]["key"] # ключ юзера
            # возвращаем ключ аутентификации юзера
            await logger.debug(f"Ключ {username} был успешно отправлен!")
            return web.Response(status=200, text=key)
        except Exception as error:
            await logger.error(f"Ошибка в get_key: {error}")
            return web.Response(status=520)

    # если в ОЗУ нет авторизованного юзера с этим никнеймом
    else:
        await logger.debug(f"{username} не был авторизован!")
        return web.Response(status=401)

async def get_files_count(request):
    """для обновления в БД данных о кол-ве файлов на удаленном серваке"""

    data = await request.post()

    client_secret_key = data.get('secret_key', '')
    if secret_key != client_secret_key:
        real_ip = request.headers.get('X-Forwarded-For', '').split(',')[0].strip()
        if not real_ip:
            real_ip = request.headers.get('X-Real-IP', '').strip()
        await logger.debug(f"Поступил запрос от {real_ip}, но secret_key невалидный: {client_secret_key}")
        return web.Response(status=404)

    if data.get("finish", ""):
        count = int(data.get("count", 0))
        if count > 0:
            route = data.get("route", "")
            await logger.debug(f"Количество файлов для {count} юзеров направления {route} успешно приняты и записаны в БД!")
        return web.Response(status=400)

    str_dict = data.get('str_dict')
    folder_files_count = eval(str_dict)

    # Подключаемся к базе данных и обновляем/добавляем информацию

    async with await request.app['pool'].acquire() as conn:
        # conn это БД dashboard_data (база для дешборда (gamers, gamers_files, users(пользователи БД для авторизации в ней)))
        # connection это БД users (БД юзеров для авторизации в ПО)

        # print(f"DASHBOARD pool object: {request.app['pool']}")
        for route, files_data in folder_files_count.items():
            not_in_db = [] # юзеры которых не обнаружено в БД
            # print(route, files_data)
            for username, files_info in files_data.items():
                # print(username, files_info)
                # async with db.execute('SELECT id FROM gamers WHERE username = ? AND route = ?', (username, route,)) as cursor:
                user_id = await file_counter.get_user_id(conn, username)
                if user_id is None:
                    async with await db_manager.pool.acquire() as connection:
                        user = await file_counter.is_registered(connection, username)
                    if user:
                        # print(f"Добавляю юзера {username} в БД")
                        await file_counter.add_user_to_db(conn, user)
                        user_id = await file_counter.get_user_id(conn, username)
                    else:
                        not_in_db.append(username)
                else:
                    real_route = await file_counter.get_route(conn, username)
                    # print(f"real_route={real_route}, username={username}")
                    if route.lower() != real_route.lower():
                        await logger.debug(f"Пришел запрос обновить инфу для юзера {username} с направлением {route}, но реальное направление юзера: {real_route}!")
                        continue

                    await conn.execute('DELETE FROM gamers_files WHERE user_id = ($1)', user_id)
                    for room_name, date_info in files_info["rooms"].items():
                        for date_name, files_count in date_info.items():
                            # print(date_name, files_count)

                            await conn.execute('''
                                INSERT INTO gamers_files(user_id, room, date, files) 
                                VALUES ($1, $2, $3, $4)
                                ON CONFLICT(user_id, room, date) 
                                DO UPDATE SET files = excluded.files
                            ''', user_id, room_name, date_name.replace('-', '.'), files_count)
            # если в списке есть юзеры, которые не обнаружены в БД дешборда, выводим из список и направление
            if not_in_db:
                not_in_db = ", ".join(not_in_db)
                await logger.debug(f"Юзеры [{not_in_db}] для [{route}] не найдены в БД!")
                not_in_db = []

    return web.Response(status=400)

async def check_notice(request):
    """проверяет, есть-ли для юзера уведомление. Если есть - отправляет ему"""
    data = await request.post()
    username = data.get('username') # имя юзера
    auth_key = data.get('auth_key')

    if username.lower() in AUTH_USERS:
        if AUTH_USERS[username.lower()]["key"] == auth_key:

            # проверяем,существует-ли файл уведомления для юзера
            file_path = os.path.join("notice", f"{username}.txt")
            if os.path.exists(file_path):
                with open(file=file_path, mode="r", encoding="utf8") as file:
                    notice_text = file.read()
                await logger.info(f"Пользователю {username} отправлено уведомление!")
                return web.Response(status=400, text=notice_text)

    return web.Response(status=404)

async def delete_notice(request):
    """удаляет файл уведомления"""
    data = await request.post()
    username = data.get('username') # имя юзера
    auth_key = data.get('auth_key')
    if username.lower() in AUTH_USERS:
        if AUTH_USERS[username.lower()]["key"] == auth_key:

            # проверяем,существует-ли файл уведомления для юзера
            file_path = os.path.join("notice", f"{username}.txt")
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    await logger.info(f"Пользователь {username} успешно получил уведомление!")
                except Exception as error:
                    await logger.error(f"Ошибка при удалении файла уведомления юзера {username}: {error}")

    return web.Response(status=400)

async def handle_ping(request):
    # для проверки работы сервера
    return web.Response(status=200)

# async def print_request(app, handler):
#     async def middleware_handler(request):
#         # если в чёрном списке - не выводим инфу о запросе
#         handler_name = handler.keywords['handler'].__name__

#         if handler_name in black_list:
#             return await handler(request)
#         data = await request.post()

#         await logger.request(f"Request from {request.remote} with method {request.method} and path {request.path}. Data: {data}")
#         return await handler(request)

#     return middleware_handler

async def handle_logs(request):
    session = await get_session(request)
    if 'user' not in session:
        raise web.HTTPUnauthorized(reason="User is not authenticated")
    logs = {}
    for log_type in ['debug', 'info', 'request', 'error']:
        async with aiofiles.open(f'logs/{log_type}.log', mode='r', encoding="utf-8") as f:
            logs[log_type] = await f.read()
    return web.json_response(logs)

async def init_conn(app):
    # создаём пул
    await pool.create_pool()







# ВРЕМЕННАЯ ЗАЩИТА ОТ ДДОС-АТАК

import subprocess
async def print_request(app, handler):
    async def middleware_handler(request):
        # если в чёрном списке - не выводим инфу о запросе
        handler_name = handler.keywords['handler'].__name__

        peername = request.transport.get_extra_info('peername') 
        host, port = peername

        # if str(request.method) == "CONNECT" and str(request.path) == '' and host != "127.0.0.1":
        #     print(f"БЛОКИРУЮ IP {host}")
        #     subprocess.call(f'netsh advfirewall firewall add rule name="Block{host}" dir=in action=block remoteip={host}', shell=True)
        #     print(f"ЗАБЛОКИРОВАН IP {host}")
        if handler_name in black_list:
            return await handler(request)

        real_ip = request.headers.get('X-Forwarded-For', '').split(',')[0].strip()
        if not real_ip:
            real_ip = request.headers.get('X-Real-IP', '').strip()

        await logger.request(f"Request from {real_ip} with method {request.method} and path {request.path}")

        return await handler(request)

    return middleware_handler







def start_server(manager):
    global AUTH_USERS, MANAGER
    MANAGER = manager
    AUTH_USERS = manager.AUTH_USERS

    app = web.Application(middlewares=[print_request])
    app['pool'] = pool
    # функции которые будут вызваны после запуска event loop
    app.on_startup.append(dashboard.init_db)
    app.on_startup.append(db_manager.main)
    app.on_startup.append(init_conn)

    # биндим обработчики
    # DashBoard
    app.router.add_get('/', dashboard.login) # страница авторизации
    app.router.add_post('/', dashboard.do_login) # страница авторизации
    app.router.add_get('/users', dashboard.users) # вывод html-таблицы юзеров
    app.router.add_get('/get_data', dashboard.get_data) # возвращает json всех юзеров
    app.router.add_post('/add_user', dashboard.add_user) # добавить юзера
    app.router.add_get('/delete_user', dashboard.delete_user) # удалить юзера
    app.router.add_post('/update_user', dashboard.update_user) # обновить данные юзера
    app.router.add_get('/filter_users', dashboard.filter_users) # рефреш списка юзеров
    app.router.add_get('/logout', dashboard.logout) # выйти из акка

    # Добавление пути для статических файлов
    app.router.add_static('/static/', path='dashboard_data/static', name='static')
    aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader('dashboard_data/templates'))
    # Настройка хранения сессий
    key = b'Team_FireStorm_CreatedBy_Dragmor' 
    setup(app, EncryptedCookieStorage(key))
    #
    app.router.add_get('/get-files-count', dashboard.get_files_count)
    app.router.add_post('/update_send_date', update_send_date)
    app.router.add_post('/files_on_server', get_files_count)
    app.router.add_get('/logs', handle_logs)

    # FireStorm клиентское ПО
    app.router.add_post('/upload', handle_upload) # принять файл от юзера
    app.router.add_get('/ping', handle_ping) # проверка пинга с сервером
    app.router.add_post('/login', handle_login) # авторизация юзера
    app.router.add_post('/get_files_list', get_files_list) # обновлённый алгоритм проверки файлов
    app.router.add_post('/errorlog', handle_errorlog) # записать/вывести лог
    app.router.add_post('/check_notice', check_notice) # проверить наличие уведомления для юзера
    app.router.add_post('/delete_notice', delete_notice) # удалить уведомление для юзера
    app.router.add_post('/get_server', get_server) # получаем адрес сервера для отправки на него файлов
    app.router.add_post('/log', handle_log)
    app.router.add_post('/get_key', get_key) # возвращает ключ аутентификации юзера
    # для работы с лейаутами
    app.router.add_post('/get_layout', get_layout)
    # для клиента ver_2
    app.router.add_post('/checkupdate_v2', check_update_v2)
    app.router.add_post('/getupdate_v2', get_update_v2)
    
    # запускаем
    web.run_app(app, host=host, port=port, print=logger.sync_info(f"Сервер запущен на [{host}:{port}] Путь для сохранения данных: {FILES_DIR}. Ключей передано: {len(AUTH_USERS)}"))









#==========================================================================================================================================================#
# переходим в указанный из окружения путь к корневому каталогу сервера
if (root_path:=os.getenv("SERVER_ROOT")):
    os.chdir(root_path)
secret_key = os.getenv("SECRET_KEY")
# словарь для хранения в оперативе ключа аутентификации юзера в виде "USERNAME": "KEY"
AUTH_USERS = {}

# словарь для списка файлов юзера на сервере
USERS_FILES = {}

# путь к папке, где хранятся файлы рук юзеров [FILES_DIR/route/username/room_name/date]
# можно прописать как относительный так и абсолютный путь
FILES_DIR = "C:\\FSTracker"

# загружаем ip:port удаленных серверов по направлениям
with open("servers.json", "r") as file:
    SERVERS = json.load(file)

# задаёт макс. кол-во потоков одновременного приёма файлов
semaphore = asyncio.Semaphore(256) 

# сюда попадают пути лейаутов в виде рум - словарь путей
PATH_LAYOUTS = {}

# для старта сервера (на каком порте будет запущен)
host = "0.0.0.0"
port = 8080

# MANAGER - это переменная из multiprocessing для обмена данными между процессами
MANAGER = None

# чёрный список функция, для которых не будет вызываться middleware_handler
black_list = [dashboard.login.__name__,dashboard.do_login.__name__,\
                dashboard.users.__name__, handle_ping.__name__, get_files_list.__name__,\
                handle_log.__name__, get_key.__name__, check_update_v2.__name__,\
                get_update_v2.__name__, handle_upload.__name__, get_files_count.__name__, handle_logs.__name__,\
                dashboard.add_user.__name__, dashboard.delete_user.__name__, dashboard.update_user.__name__, dashboard.filter_users.__name__]


# данные для подключения к БД postgres
db_manager.users_db_data = {
    "host": os.getenv("DB_HOST"), # ip postgres
    "port": os.getenv("DB_PORT"), # port
    "user": os.getenv("DB_USER"), # username
    "password": os.getenv("DB_PASSWORD"), # pass
    "database": os.getenv("DB_USERS"), # db_name
    'min_size': int(os.getenv("DB_MIN_POOL")), # pool connections minimum (default 5)
    'max_size': int(os.getenv("DB_MAX_POOL")) # maximum (default 20)
    }
# функции для работы с БД авторизационнах данных юзеров
db_manager.pool = db_manager.AsyncDatabasePool(**db_manager.users_db_data) # Создаем экземпляр класса пула

file_counter.USERS_DATABASE = 'users.db'
#=====# DAHBOARD SETTINGS #=====#
dashboard.dashboard_db_data = {
    "host": os.getenv("DB_HOST"), #
    "port": os.getenv("DB_PORT"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_DASHBOARD"),
    'min_size': int(os.getenv("DB_MIN_POOL")),
    'max_size': int(os.getenv("DB_MAX_POOL"))
    }
dashboard.users_db_data = db_manager.users_db_data
dashboard.pool = dashboard.AsyncDatabasePool(**dashboard.dashboard_db_data)
dashboard.FILES_DIR = FILES_DIR
# пул для основного кода сервера
pool = AsyncDatabasePool(**dashboard.dashboard_db_data) # Создаем экземпляр класса пула
#==========================================================================================================================================================#

if __name__ == "__main__":

    # asyncio.run(db_manager.main())
    with Manager() as manager:
        # общий словарь для AUTH_USERS
        ns = manager.Namespace()
        ns.AUTH_USERS = AUTH_USERS

        # Запуск сервера в отдельном процессе
        server_process = Process(target=start_server, args=(ns,))
        server_process.start()

        # Главный цикл
        while True:
            try:
                time.sleep(20) 
                try:
                    response = requests.get(f'http://localhost:{port}/ping', timeout=40)
                    if response.status_code != 200:
                        logger.sync_debug("Сервер не ответил, перезапуск...")
                        logger.sync_debug(f"ключей в ОЗУ: {len(ns.AUTH_USERS)}")

                        if server_process.is_alive():
                            server_process.terminate()  # Завершить процесс сервера
                            server_process.join()
                        server_process = Process(target=start_server, args=(ns,))
                        server_process.start()

                except requests.exceptions.RequestException:
                    logger.sync_debug("Сервер не ответил, перезапуск...")
                    logger.sync_debug(f"ключей в ОЗУ: {len(ns.AUTH_USERS)}")

                    if server_process.is_alive():
                        server_process.terminate()  # Завершить процесс сервера
                        server_process.join()
                    server_process = Process(target=start_server, args=(ns,))
                    server_process.start()

            except:

                if server_process.is_alive():
                    server_process.terminate()  # Завершить процесс сервера
                    server_process.join()
                server_process = Process(target=start_server, args=(ns,))
                server_process.start()
