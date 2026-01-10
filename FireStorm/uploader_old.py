import os
import sys
import psutil
import asyncio
import json
import hashlib
import tkinter as tk
import threading
import time
import aiohttp
#
import modules.http_client as http_client

# устанавливаем путь к папке с софтом
os.chdir(os.path.dirname(sys.argv[0]))

class ProgressBarWindow:
    # класс прогрессбара
    def __init__(self, size):
        self.pause = 2 # сколько ждём перед закрытием
        self.size = size
        self.root = tk.Tk()
        self.root.geometry(f"{size}x{size}")
        self.root.resizable(False, False)
        self.root.title("Uploader")
        self.root.iconbitmap("img/gui_icon.ico")
        self.canvas = tk.Canvas(self.root, width=size, height=size, bg="#1E1E1E")
        self.canvas.pack()
        self.temp_text = None
        self.arc = None
        self.persent_text = None
        self.downloaded = None

    def change_text(self, text):
        self.canvas.delete("all")
        self.temp_text = self.canvas.create_text(self.size // 2, self.size // 2, text=text, font=("Arial", 12, "bold"), fill="white", width=self.size)

        
    def draw_progress_bar(self, progress, total_files=None, current=None):
        # self.canvas.delete("all")
        x0 = y0 = self.size // 10
        x1 = y1 = self.size * 9 // 10
        arc = self.canvas.create_arc(x0, y0, x1, y1, start=90, extent=-359*(progress/100), style="arc", width=20, outline="#C71B74")
        if self.temp_text != None:
            self.canvas.delete(self.temp_text)
            self.temp_text = None

        if self.arc != None:
            self.canvas.delete(self.arc)
        self.arc = arc

        

        if self.persent_text != None:
            self.canvas.itemconfig(self.persent_text, text=f"{progress}%")
        else:
            self.persent_text = self.canvas.create_text(self.size // 2, self.size // 2-10, text=f"{progress}%", font=("Arial", 20, "bold"), fill="white")

        if  total_files != None and current != None:
            if  self.downloaded != None:
                self.canvas.itemconfig(self.downloaded, text=f"{current} из {total_files}")
            else:
                self.downloaded = self.canvas.create_text(self.size // 2, self.size // 2+10, text=f"{current} из {total_files}", font=("Arial", 10, "bold"), fill="white")

    def end_upload(self):
        for t in range(self.pause, 0, -1):
            self.canvas.delete("all")
            text = f"Файлы отправлены!\nВыход через {t} с."
            self.canvas.create_text(self.size // 2, self.size // 2, text=text, font=("Arial", 12, "bold"), fill="white", width=self.size)
            time.sleep(1)
        # закрываем программу
        os._exit(0)

    def connection_error(self):
        self.canvas.delete("all")
        text = f"Неверный логин/пароль, либо нет соединения с сервером!\nЗапустите FireStorm, либо попробуйте перезапустить программу!"
        self.canvas.create_text(self.size // 2, self.size // 2, text=text, font=("Arial", 12, "bold"), fill="white", width=self.size)
        self.canvas.bind("<Button-1>", lambda event: os._exit(0))

    def paths_error(self):
        for t in range(self.pause, 0, -1):
            self.canvas.delete("all")
            text = f"Запустите FireStorm и проверьте правильность указанных путей к рукам!\nВыход через {t} с."
            self.canvas.create_text(self.size // 2, self.size // 2, text=text, font=("Arial", 12, "bold"), fill="white", width=self.size)
            time.sleep(1)
        # закрываем программу
        os._exit(0)

    def auth_error(self):
        for t in range(self.pause, 0, -1):
            self.canvas.delete("all")
            text = f"Ошибка при проверке ключа авторизации! Повторите попытку!\nВыход через {t} с."
            self.canvas.create_text(self.size // 2, self.size // 2, text=text, font=("Arial", 12, "bold"), fill="white", width=self.size)
            time.sleep(1)
        # закрываем программу
        os._exit(0)

    def process_error(self, room_name):
        for t in range(self.pause, 0, -1):
            self.canvas.delete("all")
            text = f"Обнаружен процесс рума: [{room_name}]!\nВыход через {t} с."
            self.canvas.create_text(self.size // 2, self.size // 2, text=text, font=("Arial", 12, "bold"), fill="white", width=self.size)
            time.sleep(1)
        # закрываем программу
        os._exit(0)

    def not_files(self):
        for t in range(self.pause, 0, -1):
            self.canvas.delete("all")
            text = f"Не найдено новых файлов для отправки на сервер!\nВыход через {t} с."
            self.canvas.create_text(self.size // 2, self.size // 2, text=text, font=("Arial", 12, "bold"), fill="white", width=self.size)
            time.sleep(1)
        # закрываем программу
        os._exit(0)

    def show_alert(self):
        self.canvas.delete("all")
        text = f"Проверка актуальной версии ПО..."
        self.canvas.create_text(self.size // 2, self.size // 2, text=text, font=("Arial", 12, "bold"), fill="white", width=self.size)

        if os.path.exists("ver"):
            with open("ver", "r") as file:
                self.version = file.readline()
        else:
            self.version = "1.0"

        with open("settings/config.json", "r") as file:
            data = json.load(file)
        server_url = data["server"] # ip:port сервера

        server_version = asyncio.run(http_client.check_update(URL=server_url))
        if server_version == None:
            print("Не удалось получить информацию о обновлениях с сервера!")
            return

        if server_version == "" or server_version == self.version:
            # если у юзера последняя версия, то выходим из цикла
            # выводит сообщение юзеру перед отправкой файлов
            self.user_accept = False # согласился ли юзер продолжить
            self.canvas.delete("all")
            text = f"ВНИМАНИЕ!\nИспользование этой программы при любом запущенном клиенте\nрума ЗАПРЕЩЕНО!\n\nДля начала отправки нажмите мышкой в это окно."
            self.canvas.create_text(self.size // 2, self.size // 2, text=text, font=("Arial", 12, "bold"), fill="white", width=self.size)
            self.canvas.bind("<Button-1>", lambda event: self.accept())

        elif server_version == 200:
            # если ошибка при запросе версии
            self.canvas.delete("all")
            text = f"Не удалось проверить обновления! Проверьте интернет соединение и перезапустите программу!"
            self.canvas.create_text(self.size // 2, self.size // 2, text=text, font=("Arial", 12, "bold"), fill="white", width=self.size)
            self.canvas.bind("<Button-1>", lambda event: os._exit(0))

        elif server_version != self.version:
            # если ошибка при запросе версии
            self.canvas.delete("all")
            text = f"Ваша версия ПО устарела!\nЗапустите FireStorm, и загрузите обновление для дальнейшей работы с программой!"
            self.canvas.create_text(self.size // 2, self.size // 2, text=text, font=("Arial", 12, "bold"), fill="red", width=self.size)
            self.canvas.bind("<Button-1>", lambda event: os._exit(0))
        


    def accept(self):
        global server_url, username, route, file_server, auth_key, rooms, FILE_TYPES
        # когда юзер согласился отправлять файлы
        # проверка на запущенные процессы
        if check_processes():
            return


        # считываем из файла интервал времени, через который производится попытка отправки файлов на сервер
        with open("settings/config.json", "r") as file:
            data = json.load(file)
        FILE_TYPES = data["filetypes"] # типы файлов, которые будем забирать
        server_url = data["server"] # ip:port сервера

        with open("settings/user_data.json", "r") as file:
            data = json.load(file)
        username = data["username"] # логин юзера
        password = data["password"] # пароль

        if not username or not password:
            # Запускаем отправку в отдельном потоке, чтобы не блокировать окно
            thread = threading.Thread(target=window.connection_error)
            thread.daemon = True
            thread.start()
            
            return
            
        with open("settings/services.json", "r") as file:
            data = json.load(file)
        # тут пройтись по данным из файла, и вытащить пути и имена румов, у которых включен трекинг
        rooms = {} # имя рума - список путей к каталогам
        for room in data["services"]:
            if data["services"][room]["folders"] != [] and data["services"][room]["track"]:
                rooms[room] = data["services"][room]["folders"]
        if rooms == {}:
            asyncio.run(http_client.send_log(URL=server_url, username=username, error="У клиента неправильно заданы пути к рукам либо выключен трекинг!"))
            # Запускаем отправку в отдельном потоке, чтобы не блокировать окно
            thread = threading.Thread(target=window.paths_error)
            thread.daemon = True
            thread.start()

            return
            
        try:
            status = asyncio.run(http_client.autorization(URL=server_url, \
                username=username, \
                password=password))

        except aiohttp.ClientConnectorError as e:
            thread = threading.Thread(target=window.connection_error)
            thread.daemon = True
            thread.start()

        else:
            # проверяем, залогинились-ли мы
            if status[0] == 205:
                # если да - записываем ключ аутентификации от сервера
                auth_key = status[-1]
                file_server = status[1] # адрес сервера для приёма файлов
                route = status[2]
                # print(f"Получен ключ аутентификации: {auth_key}")
            else:
                asyncio.run(http_client.send_log(URL=server_url, username=username, error=f"Клиент не смог установить соединение с сервером [{server_url}]!"))
                # Запускаем отправку в отдельном потоке, чтобы не блокировать окно
                thread = threading.Thread(target=window.connection_error)
                thread.daemon = True
                thread.start()
                
                return
                
            self.canvas.delete("all")
            text = f"Сканируем файлы... Подождите"
            self.canvas.create_text(self.size // 2, self.size // 2, text=text, font=("Arial", 12, "bold"), fill="white", width=self.size)

            # запуск скана каталогов
            thread = threading.Thread(target=check_start, args=(server_url, username, route, file_server, auth_key, rooms, FILE_TYPES,))
            thread.daemon = True
            thread.start()
            # check_start(server_url=server_url, file_server=file_server, route=route, username=username, auth_key=auth_key,\
            #     rooms=rooms, file_types=FILE_TYPES)


    def run(self):
        self.root.mainloop()



def check_processes(main_window=None):
    # Проверка запущенных процессов

    # Путь к файлу processes.ini
    file_path = 'settings/processes.ini'
    # Чтение содержимого файла
    with open(file_path, 'r') as file:
        processes = file.read().splitlines()

    for process in processes:
        matched_process = next((p.name() for p in psutil.process_iter() if process.lower() in p.name().lower()), None)
        if matched_process:
            print(f"Обнаружен процесс {str(matched_process)}! Завершаю работу!")
            # если найден запущеный процесс
            # Создаем окно размером 220x220, если оно не передано в функцию

            # Запускаем отправку в отдельном потоке, чтобы не блокировать окно
            thread = threading.Thread(target=window.process_error, args=(str(matched_process),))
            thread.daemon = True
            thread.start()
                
            # заходим в вечный цикл чтобы не отправлялись файлы
            return True
        else:
            return False

def try_log_in():
    with open("settings/user_data.json", "r") as file:
        data = json.load(file)
    username = data["username"] # логин юзера
    password = data["password"] # пароль
    # считываем из файла интервал времени, через который производится попытка отправки файлов на сервер
    with open("settings/config.json", "r") as file:
        data = json.load(file)
    server_url = data["server"] # ip:port сервера

    while True:
        try:
            status = asyncio.run(http_client.autorization(URL=server_url, \
                username=username, \
                password=password))
            # проверяем, залогинились-ли мы
            if status[0] == 205:
                # если да - записываем ключ аутентификации от сервера
                auth_key = status[-1]
                file_server = status[1] # адрес сервера для приёма файлов
                route = status[2]
                return auth_key
            # если сервер ответил, что не удалось залогиниться
            else:
                thread = threading.Thread(target=window.connection_error)
                thread.daemon = True
                thread.start()
                return None


        except aiohttp.ClientConnectorError as e:
            print(f"Ошибка соединения с сервером: {e}")


def check_start(server_url, username, route, file_server, auth_key, rooms, file_types):
    # проходимся по путям и собираем файлы

    # проверка на запущенные процессы
    if check_processes():
        return

    

    # если процессы из тех, что прописаны в файле, не запущены, то
    files = [] # список списков файлов, которые будем по итогу отправлять
    # проходимся по всем румам и отслеживаемым папкам
    for srv in rooms:
        room_name = srv
        dir_list = rooms[srv]
            
        # print("Процессы в норме!")
        # print(f"Рум: {room_name}, список каталогов: {dir_list}")
        window.change_text(text=f"Получаем список файлов на сервере для рума: {room_name}...")

        while True:
            files_on_server = asyncio.run(http_client.get_files(URL=file_server, route=route, username=username, room=room_name, auth_key=auth_key))
            
            # если потеряно соединение с сервером
            if files_on_server == 200:
                window.change_text(text=f"Потеряно соединение с сервером...\nПопытка восстановления")
                window.arc = None
                window.persent_text = None
                window.downloaded = None

            elif files_on_server == None:
                # невалидный ключ
                auth_key = try_log_in()
                if auth_key == None:
                    return
            elif files_on_server != 300:
                break

            # ждём 3 секунды
            time.sleep(3)

        # если невалидный ключ авторизации
        if files_on_server == None:
            # Запускаем отправку в отдельном потоке, чтобы не блокировать окно
            thread = threading.Thread(target=window.auth_error)
            thread.daemon = True
            thread.start()

            return

            # print(f"Всего файлов этого рума на сервере: {len(files_on_server)}")
            
        # проходимся по каталогам, которые мониторим
        window.change_text(text=f"Определяем, какие файлы рума {room_name} нужно отправить на сервер...")

        for path in dir_list:
            # получаем список файлов из каталогов (абсолютные пути к файлам)
            finded_files = find_files(path=path)

            # формируем список файлов, которые нужно отправить на сервер (которых там ещё нет)
            finded_files_set = set(map(tuple, finded_files))
            files_on_server = set(map(tuple, files_on_server))
            need_to_send = list(finded_files_set - files_on_server)

            if need_to_send == [()] or need_to_send == []:
                continue

            # записываем список [имя_рума, осн_путь, [пути_к_файлам]]
            files.append([room_name, path, need_to_send])


    # если есть файлы, которые нужно отправить
    if files:
        # Создаем окно размером 220x220
        # Запускаем отправку в отдельном потоке, чтобы не блокировать окно
        thread = threading.Thread(target=send_files, args=(file_server, username, auth_key, files, window))
        thread.daemon = True
        thread.start()
        

    else:
        asyncio.run(http_client.send_log(URL=server_url, username=username, error="Не обнаружено файлов для передачи на сервер! Возможно, файлы были переданы ранее, \
неверно указан каталог с руками, либо файлов рук пока нет в указанном каталоге юзера!", level='log'))
        # Создаем окно размером 220x220
        # Запускаем отправку в отдельном потоке, чтобы не блокировать окно
        thread = threading.Thread(target=window.not_files)
        thread.daemon = True
        thread.start()
        

def send_files(URL, username, auth_key, files, window):
    # отправляем файлы, которые нужно отправить
    total_files = 0 # сколько файлов всего нужно отправить
    current = 0 # какой по счёту файл уже отправили
    # считаем кол-во файлов для отправки
    for sublist in files:
        for item in sublist:
            if isinstance(item, list):
                total_files += len(item)
    # print(f'Всего нужно отправить файлов: {total_files}')
    
    # высчитываем, сколько это в процентах
    percentage = int(current / total_files * 100)
    # отрисовка прогрессбара
    window.canvas.delete("all")
    window.draw_progress_bar(percentage, total_files, current)


    for file in files:
        for file_path in file[2]:
            try:
                # проверка на запущенные процессы
                if check_processes(main_window=window):
                    return
                # status = asyncio.run(http_client.upload_file(URL=URL, route=route, filename=os.path.join(file[1], file_path[0]), username=username, room=file[0], auth_key=auth_key, sub_dirs=os.path.dirname(file_path[0])))
                

                while True:
                    status = asyncio.run(http_client.upload_file(URL=URL, route=route, filename=os.path.join(file[1], file_path[0]), username=username, room=file[0], auth_key=auth_key, sub_dirs=os.path.dirname(file_path[0])))
                    # если потеряно соединение с сервером
                    if status == 200:
                        window.change_text(text=f"Нет соединения с сервером!\nПроверьте интернет-соединение!\nЕсли в течении 3-х минут соединение не восстановится, перезапустите ПО!")
                        window.arc = None
                        window.persent_text = None
                        window.downloaded = None
                    elif status == None:
                        # невалидный ключ
                        auth_key = try_log_in()
                        if auth_key == None:
                            return
                    elif status != 300:
                        break

                    # ждём 3 секунды
                    time.sleep(3)


                if status == None:
                    # Запускаем отправку в отдельном потоке, чтобы не блокировать окно
                    thread = threading.Thread(target=window.auth_error)
                    thread.daemon = True
                    thread.start()

                    return
                    
                current += 1
                percentage = int(current / total_files * 100)
                window.draw_progress_bar(percentage, total_files, current)
            except aiohttp.ClientConnectorError:
                print(f"Ошибка соединения с сервером: {e}")
            except Exception as e:
                current += 1
                print(f"Ошибка отправки файла: {e}")


    if len(files) > 0:
        print("Готово!")

    thread = threading.Thread(target=window.end_upload)
    thread.daemon = True
    thread.start()
    


# функция принимает путь к папке, и возвращает список файлов в ней
def find_files(path, size_limit=1024):
    small_files = [] # сюда попадают названия файлов
    size_limit *= 1024  # переводим килобайты в байты

    if os.path.exists(path):
        # проходим по всем файлам и подпапкам
        for root, dirs, files in os.walk(path):
            for file in files:
                full_path = os.path.join(root, file)
                # если размер файла не превышает предел
                if os.path.getsize(full_path) < size_limit or file.lower().endswith('txt'):
                    # если расширение файла то, что нужно
                    file_extension = os.path.splitext(file)[1][1:]
                    if file_extension and file_extension in FILE_TYPES:
                        # добавляем в список файлов относительный путь
                        relative_path = os.path.relpath(full_path, path)

                        # Вычисляем MD5 контрольную сумму файла
                        with open(full_path, 'rb') as f:
                            md5_hash = hashlib.md5()
                            while chunk := f.read(4096):
                                md5_hash.update(chunk)
                            checksum = md5_hash.hexdigest()

                        small_files.append([relative_path, checksum])

                        # small_files.append(relative_path)

                        # small_files.append(os.path.normpath(full_path))
                        # print(f"Найден файл: {small_files[-1]}")

    else:
        print("Указанный путь не существует")
    # возвразаем список путей к найденным файлам
    return small_files




    
window = ProgressBarWindow(220)
thread = threading.Thread(target = window.show_alert)
thread.daemon = True
thread.start()
window.run()
    