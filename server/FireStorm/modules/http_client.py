# тут функции для отправки на сервер http-запросов
import os
import time
import aiohttp
import asyncio
#


# для получения временной зоны юзера (смещение)
def get_utc_offset():
    # Получаем текущее местное время и время по UTC
    local_time = time.localtime()
    utc_time = time.gmtime(time.mktime(local_time))
    
    # Рассчитываем смещение в секундах
    offset_seconds = time.mktime(local_time) - time.mktime(utc_time)
    
    # Преобразуем смещение в часы и минуты
    offset_hours = offset_seconds // 3600
    offset_minutes = (offset_seconds % 3600) // 60
    
    # Форматируем строку со знаком
    sign = "+" if offset_seconds >= 0 else "-"
    offset_string = f"UTC{sign}{abs(int(offset_hours)):02}:{abs(int(offset_minutes)):02}"
    
    return offset_string

async def upload_file(client, filename, room, semaphore, lock, sub_dirs=""):
    """
    эта функция для отправки файлов на сервак. Она сильно привязана к ГУИ-шному клиенту,
    и поэтому сюда передаётся целый объект ГУИ-клиента, чтобы не передавать кучу аргументов
    отдельно. Используется ТОЛЬКО в uploader.py при отправке файлов рук на сервер.
    """

    # если обнаружен запущенный процесс рума - закрываем прогу через 3 секунды
    if client.process_finded:
        async with lock:
            client.timer_close(text="Найден запущенный процесс рума!\nЗавершение работы программы!", timer=3)

    async with semaphore:
        # print(f"отправляем файл {filename}")

        # функция для передачи файла на сервер
        try:
            size_limit = 4096 * 1024  # переводим килобайты в байты
            # передаю только файлы которые весят меньше порога (либо txt, его размер не учитываем)
            file_size = os.path.getsize(filename)
            if file_size > size_limit and not filename.lower().endswith('txt'):
                print(f"Файл {filename} не удовлетворяет условиям передачи!")
                return ""
            # Делаем проверку, если файл весит меньше 4-х байт - считаем пустым
            elif file_size <= 4:
                print(f"Файл {filename} пустой!")
                return ""
        except Exception as error:
            print(f"Ошибка при попытке проверить файл: {filename}! Error: {error}")
            await send_log(URL=client.server_url, username=client.username, error=f"Ошибка при попытке проверить файл перед отправкой, error={error}, room={room}, file={filename}", session=client.session)
            return ""

        # кол-во попыток выполнить отправку, после которого пишется лог об ошибке
        log_after_retryes = 10
        retryes = 0

        # ключ аутентификации
        auth_key = client.auth_key

        while True:
            url = f'{client.file_server}/upload'
            data = aiohttp.FormData()
            data.add_field('file', open(filename, 'rb'))
            data.add_field('username', client.username)
            data.add_field('auth_key', auth_key)
            data.add_field('room', room)
            data.add_field('route', client.route)
            data.add_field('subdirs', sub_dirs) # подпапки
            statuscode = None # код ответа от сервера
            try:
                async with client.session.post(url, data=data, timeout=90) as response:
                    # print(response.status)
                    statuscode = response.status
                    # если ключ авторизации невалидный
                    if statuscode in (301, 205):
                        async with lock:
                            # для синхронизации ключа аутентификации
                            if auth_key != client.auth_key:
                                print(f"Ключи не совпадают: auth_key={auth_key}, client.auth_key={client.auth_key}. Присваиваем новое значение...")
                                auth_key = client.auth_key
                                continue
                            print("Ключ невалидный. Попытка получить новый ключ...")
                            # невалидный ключ
                            if not await client.try_log_in():
                                client.click_close(text="Ошибка при получении ключа аутентификации!\nПерезапустите программу!")
                                return None
                            else:
                                # print(f"auth_key={auth_key}")

                                auth_key = client.auth_key
                                # print(f"client.auth_key={client.auth_key}")

                                continue
                    # сервер работает, но бекенд на нём не работает!
                    elif statuscode == 502:
                        async with lock:
                            client.show_error(text="Ошибка на стороне сервера! Пожалуйста, подождите...", timer=1)
                        continue
                    # всё ок, файл отправился
                    elif statuscode == 200:
                        # если файл отправился
                        async with lock:
                            # добавляем в прогрессбар +1 отправленный файл
                            await client.plus_uploaded_counter()
                        return await response.text()

            except asyncio.TimeoutError as error:
                retryes += 1
                async with lock:
                    client.show_error(text="Истекло время ожидания ответа от сервера... Подождите ещё, либо перезапустите программу", timer=3)
                if retryes >= log_after_retryes:
                    retryes = 0
                    # отправка ошибки в лог
                    await send_log(URL=client.server_url, username=client.username, error=f"Истекло время ожидания ответа от сервера, error={error}, room={room}, file={filename}, statuscode={statuscode}", session=client.session)
                continue
            except aiohttp.ClientConnectorError as error:
                retryes += 1
                async with lock:
                    client.show_error(text="Нет соединения с сервером!\nПроверьте интернет-соединение!\nЕсли в течении 3-х минут соединение не восстановится, перезапустите ПО!", timer=3)
                if retryes >= log_after_retryes:
                    retryes = 0
                    # отправка ошибки в лог
                    await send_log(URL=client.server_url, username=client.username, error=f"Нет соединения с сервером, error={error}, room={room}, file={filename}, statuscode={statuscode}", session=client.session)
                continue
            except Exception as error:
                retryes += 1
                print(f"Неизвестная ошибка: {error}")
                if retryes >= log_after_retryes:
                    retryes = 0
                    # отправка ошибки в лог
                    await send_log(URL=client.server_url, username=client.username, error=f"Неизвестная ошибка, error={error}, room={room}, file={filename}, statuscode={statuscode}", session=client.session)
                continue
            
            # если попали сюда - то это вообще ошибка ошибок
            await send_log(URL=client.server_url, username=client.username, error=f"Необработанная ситуация, room={room}, file={filename}, statuscode={statuscode}", session=client.session)



async def update_send_date(URL, username, auth_key, session=None):
    # для обновления на сервере даты отправки файлов
    url = f'{URL}/update_send_date'
    data = aiohttp.FormData()
    data.add_field('username', username)
    data.add_field('auth_key', auth_key)
    for attempt in range(10):
        try:
            # async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data, timeout=60) as response:
                print(f"Обновление даты отправки выполнено! Status={response.status}")
                return response.status
        except Exception as error:
            print(f"Не удалось обновить дату последней отправки файлов, попытка #{attempt+1}. Ошибка: {error}")

async def check_notice(URL, username, auth_key, session=None):
    # для запроса уведомления
    url = f'{URL}/check_notice'
    data = aiohttp.FormData()
    data.add_field('username', username)
    data.add_field('auth_key', auth_key)

    new_session = None
    if not session:
        new_session = aiohttp.ClientSession()
        session = new_session

    # async with aiohttp.ClientSession() as session:
    try:
        async with session.post(url, data=data, timeout=30) as response:
            if response.status == 400:
                return await response.text()
            else:
                return None
    except:
        pass
    finally:
        if new_session:
            await session.close()

async def delete_notice(URL, username, auth_key, session=None):
    # для удаления уведомления
    url = f'{URL}/delete_notice'
    data = aiohttp.FormData()
    data.add_field('username', username)
    data.add_field('auth_key', auth_key)

    new_session = None
    if not session:
        new_session = aiohttp.ClientSession()
        session = new_session

    # async with aiohttp.ClientSession() as session:
    try:
        async with session.post(url, data=data, timeout=30) as response:
            return None
    except:
        pass
    finally:
        if new_session:
            await session.close()

async def get_files(URL, username, room, route, auth_key, session=None, timeout=None):
    # функция для запроса списка файлов, которые уже есть на сервере 
    #(чтобы не отправлять повторно те, которые там уже есть)
    url = f'{URL}/get_files_list'
    data = aiohttp.FormData()
    data.add_field('username', username)
    data.add_field('room', room)
    data.add_field('route', route)
    data.add_field('auth_key', auth_key)
    try:
        # async with aiohttp.ClientSession() as session:
        async with session.post(url, data=data, timeout=60) as response:
            # если на сервере только что запустился поток сбора файлов
            if response.status == 300:
                # возвращаем код ответа
                return response.status
            # если ключ авторизации невалидный
            elif response.status == 301:
                print("Ключ невалидный. Попытка получить новый ключ...")
                return None
            else:
                # если есть файлы, то превращаем строку в список и возвращаем
                files_list = await response.text()
                return eval(files_list)

    except asyncio.TimeoutError as error:
        print(f"Возникла ошибка TimeoutError при запросе файлов: {error}")
        return 200
    except aiohttp.ClientConnectorError as error:
        print(f"Возникла ошибка ClientConnectorError при запросе файлов: {error}")
        return 200
    except Exception as error:
        print(f"Возникла критическая ошибка при запросе файлов: {error}")
        return 300

async def autorization(URL, username, password, session=None, time_offset=False):
    # функция для авторизации
    url = f'{URL}/login'
    data = aiohttp.FormData()
    data.add_field('username', username)
    data.add_field('password', password)
    # если нужно передавать смещение времени
    if time_offset:
        data.add_field('time_offset', get_utc_offset())

    new_session = None
    if not session:
        new_session = aiohttp.ClientSession()
        session = new_session

    # 5 попыток соединения
    for attempt in range(5):
        try:
            async with session.post(url, data=data, timeout=15) as response:
                # если всё ок
                if response.status == 205:
                    auth_key = await response.text()
                    file_server = await get_server(URL=URL, username=username, auth_key=auth_key, session=session)
                    file_server = eval(file_server) # преобразуем в список ["http://ip:port", "route"]
                    if new_session:
                        await session.close()
                    return [response.status, file_server[0], file_server[1], auth_key]
                else:
                    if new_session:
                        await session.close()
                    return  [response.status, None]
        # если по истечении времени не был получен ответ - вызываем исключение
        except asyncio.TimeoutError:
            pass

    if new_session:
        await session.close()

    # вызываем исключение после 5-ти неудачных попыток получить ответ от сервера
    raise aiohttp.ClientConnectorError(
        "Соединение с сервером не удалось",
        OSError(111, "Соединение отклонено"))

async def send_log(URL, username, error, session=None, level='errorlog'):
    # функция для авторизации
    url = f'{URL}/{level}'
    data = aiohttp.FormData()
    data.add_field('username', username)
    data.add_field('error', error)

    new_session = None
    if not session:
        new_session = aiohttp.ClientSession()
        session = new_session

    try:
        # async with aiohttp.ClientSession() as session:
        async with session.post(url, data=data, timeout=5) as response:
            return response.status
    except asyncio.TimeoutError:
        return 303
    except:
        return 304
    finally:
        if new_session:
            await session.close()

async def check_update(URL, session=None):
    # функция для запрашивания последней версии ПО    
    # сервер возвращает номер версии и ссылку для загрузки
    url = f'{URL}/checkupdate_v2'
    data = aiohttp.FormData()

    new_session = None
    if not session:
        new_session = aiohttp.ClientSession()
        session = new_session

    # 10 попыток соединения
    for attempt in range(10):
        try:
            # async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data, timeout=30) as response:
                if response.status == 303:
                    if new_session:
                        await session.close()
                    return await response.text()
                else:
                    if new_session:
                        await session.close()
                    return ""

        except Exception as error:
            print(f"Попытка {attempt+1} получить версию ПО провалилась... {error}")
    if new_session:
        await session.close()
    return None

async def get_update(URL, bar):
    # скачивание обновы
    url = f'{URL}/getupdate_v2'
    data = aiohttp.FormData()
    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=data) as response:
            if response.status == 200:
                downloaded_size = 0
                total_size = int(response.headers.get('Content-Length', 0))  # размер принимаемого файла
                print(f"Размер обновления: {total_size}байт")
                filename = 'update.zip'
                with open(filename, 'wb') as f:
                    while True:
                        try:
                            # если в течении 15 секунд не получаем ответ - вызываем исключение
                            chunk = await asyncio.wait_for(response.content.read(1024), timeout=40)
                            downloaded_size += len(chunk)
                            progress = int(downloaded_size / total_size * 100)
                            # переписовываем статусбар
                            bar.draw_progress_bar(progress=progress, total_files=total_size, current=downloaded_size)
                        except asyncio.TimeoutError:
                            return False

                        

                        if not chunk:
                            break
                        f.write(chunk)
                print(f"File '{filename}' received and saved.")
                bar.complete()
                return True

async def get_layout(URL, room, constructed, parent):
    # функция для запроса и скачивание наконструированного лейаута с сервера
    url = f'{URL}/get_layout'
    data = aiohttp.FormData()
    data.add_field('room', room) # имя рума, для которого будем качать лейаут
    data.add_field('constructed', constructed) # список элементов, которые выбрал юзер
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=None)) as session:
        async with session.post(url, data=data) as response:


            if response.status == 200:
                downloaded_size = 0
                total_size = int(response.headers.get('Content-Length', 0))  # размер принимаемого файла
                print(f"Размер принимаемого лейаута: {total_size}байт")
                filename = 'layout.zip'
                with open(filename, 'wb') as f:
                    while True:
                        try:
                            chunk = await asyncio.wait_for(response.content.read(1024), timeout=120)
                            downloaded_size += len(chunk)
                            progress = downloaded_size / total_size * 100
                            # переписовываем статусбар
                            await parent.set_persents(persent=progress)

                        except asyncio.TimeoutError:
                            return 404

                        except Exception as error:
                            print(f"Возниклаошибка при загрузке лейаута: {error}")

                        if not chunk:
                            break
                        f.write(chunk)
                print(f"Лейаут принят и сохранён успешно!")
                return 200

            else:
                print(f"Не удалось скачать лейаут. Код: {response.status}")
                return response.status

async def get_server(URL, username, auth_key, session=None):
    # для получения адреса сервера для передачи ему файлов
    url = f'{URL}/get_server'
    data = aiohttp.FormData()
    data.add_field('username', username)
    data.add_field('auth_key', auth_key)

    new_session = None
    if not session:
        new_session = aiohttp.ClientSession()
        session = new_session
    
    # async with aiohttp.ClientSession() as session:
    async with session.post(url, data=data) as response:
        try:
            # если не найден сервер
            if response.status == 404:
                return URL
            # если всё ок, возвращаем новый адрес
            elif response.status == 200:
                return await response.text()
            # если ключ невалидный
            elif response.status == 301:
                return URL
            # если произошло что-то непредсказуемое
            else:
                return URL
        except:
            return URL
        finally:
            if new_session:
                await session.close()
