import os
import sys
import psutil
import atexit
import asyncio
import json
import hashlib
import tkinter as tk
from tkinter import messagebox
from threading import Thread
import time
import aiohttp
from datetime import datetime, date
#
import modules.http_client as http_client
# 
import modules.paths_checker as path_checker

# устанавливаем путь к папке с софтом
base_dir = os.getenv("FIRESTORM_BASE", os.path.dirname(sys.argv[0]))
os.chdir(base_dir)


def _pid_path():
    return os.path.join(base_dir, "settings", "uploader.pid")


def _is_pid_active(pid):
    try:
        process = psutil.Process(pid)
        return process.is_running() and process.status() != psutil.STATUS_ZOMBIE
    except Exception:
        return False


def _ensure_single_instance():
    os.makedirs(os.path.join(base_dir, "settings"), exist_ok=True)
    pid_file = _pid_path()
    current_pid = os.getpid()
    if os.path.exists(pid_file):
        try:
            with open(pid_file, "r", encoding="utf-8") as file:
                existing = int(file.read().strip() or 0)
        except Exception:
            existing = 0
        if existing and existing != current_pid and _is_pid_active(existing):
            print(f"Uploader already running (pid={existing}).")
            raise SystemExit(0)
    with open(pid_file, "w", encoding="utf-8") as file:
        file.write(str(current_pid))

    def _cleanup():
        try:
            if os.path.exists(pid_file):
                with open(pid_file, "r", encoding="utf-8") as file:
                    existing = int(file.read().strip() or 0)
                if existing == current_pid:
                    os.remove(pid_file)
        except Exception:
            pass

    atexit.register(_cleanup)


_ensure_single_instance()


def _status_path():
    return os.path.join(base_dir, "settings", "upload_status.json")


def write_status(state, message, room=None, extra=None):
    os.makedirs(os.path.join(base_dir, "settings"), exist_ok=True)
    payload = {
        "state": state,
        "message": message,
        "room": room,
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    if extra:
        payload.update(extra)
    try:
        with open(_status_path(), "w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=True)
    except Exception:
        pass


def _config_bool(value, default=False):
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")
    return bool(value)

class Window():
    def __init__(self, size):
        self.manager = None

        self.pause = 2 # сколько ждём перед закрытием
        self.size = size
        self.redraw_interval = 300 # через сколько миллисекунд будем вызывать метод

    def start(self, manager):
        self.manager = manager
        self.root = tk.Tk()
        # установка обработчика события закрытия окна
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.geometry(f"{self.size}x{self.size}")
        self.root.resizable(False, False)
        self.root.title("Uploader")
        if sys.platform.startswith("win"):
            icon_path = os.path.join(base_dir, "img", "gui_icon.ico")
            if os.path.exists(icon_path):
                try:
                    self.root.iconbitmap(icon_path)
                except Exception:
                    pass
        else:
            icon_path = os.path.join(base_dir, "img", "logo.png")
            if os.path.exists(icon_path):
                try:
                    icon_img = tk.PhotoImage(file=icon_path)
                    self.root.iconphoto(True, icon_img)
                    self._icon_img = icon_img
                except Exception:
                    pass
        self.canvas = tk.Canvas(self.root, width=self.size, height=self.size, bg="#1E1E1E")
        self.canvas.bind("<Button-1>", self.mouse_click)
        self.canvas.pack()
        self.text = None
        self.canvas_text = None
        self.arc = None
        self.persent_text = None
        self.downloaded = None

        # Планирование первого вызова redraw
        self.root.after(0, self.redraw)
        self.root.mainloop()

    def on_closing(self):
        os._exit(0)

    def mouse_click(self, event):
        # делает активной "mouse_click"
        self.manager["mouse_click"] = True

    def redraw(self):
        # для перерисовки содержимого окна
        if self.manager["progress"] is None:
            if self.persent_text is not None:
                self.canvas.delete(self.persent_text)
                self.persent_text = None
            if self.downloaded is not None:
                self.canvas.delete(self.downloaded)
                self.downloaded = None
            if self.arc is not None:
                self.canvas.delete(self.arc)
                self.arc = None
        # вывод временного текста. Обычно это алерты
        if self.manager["text"] is not None and self.text != self.manager["text"]:
            self.canvas.delete("all")
            self.text = self.manager["text"]
            self.canvas_text = self.canvas.create_text(self.size // 2, self.size // 2, text=self.text, font=("Arial", self.manager["size"], "bold"), fill=self.manager["color"], width=self.size)
        
        elif self.manager["text"] is None:
            if self.canvas_text is not None:
                self.canvas.delete(self.canvas_text)
                self.canvas_text = None
            else:
                self.text = None

        if self.manager["downloaded"]:
            if self.text is not None:
                if self.canvas_text is not None:
                    self.canvas.delete(self.canvas_text)
                    self.canvas_text = None
                else:
                    self.canvas.delete("all")
                    self.text = None

            # рисуем прогрессбар 
            x0 = y0 = self.size // 10
            x1 = y1 = self.size * 9 // 10
            arc = self.canvas.create_arc(x0, y0, x1, y1, start=90, extent=-359*(self.manager["progress"]/100), style="arc", width=20, outline="#C71B74")

            if self.arc is not None:
                self.canvas.delete(self.arc)
            self.arc = arc

            if self.persent_text is not None:
                self.canvas.itemconfig(self.persent_text, text=f'{self.manager["progress"]}%')
            else:
                self.persent_text = self.canvas.create_text(self.size // 2, self.size // 2-10, text=f'{self.manager["progress"]}%', font=("Arial", 20, "bold"), fill="white")

            if  self.manager["downloaded"] is not None:
                if self.downloaded is not None:
                    self.canvas.itemconfig(self.downloaded, text=f'{self.manager["downloaded"]}')
                else:
                    self.downloaded = self.canvas.create_text(self.size // 2, self.size // 2+10, text=f'{self.manager["downloaded"]}', font=("Arial", 10, "bold"), fill="white")

        self.text = None
        # print(self.manager) # отслеживаю словарь

        # Планирование следующего вызова redraw через заданный интервал
        self.root.after(self.redraw_interval, self.redraw)





class HTTP_Client():
    def __init__(self, manager):

        self.process_finded = False # обнаружен-ли запущенный процесс из ЧС
        # self.processes_scaner = Thread(target=self.check_processes)
        # self.processes_scaner.daemon = True
        # self.processes_scaner.start()

        self.manager = manager
        # задаём дефолтные значения
        self.manager["color"] = "white"
        self.manager["size"] = 12


        with open("settings/config.json", "r") as file:
            self.config = json.load(file)
        self.server_url = self.config["server"]# ip:port сервера
        self.FILE_TYPES = self.config["filetypes"] # типы файлов, которые будем забирать
        self.auto_upload = _config_bool(self.config.get("auto_upload"), True)
        try:
            self.auto_upload_interval = int(self.config.get("auto_upload_interval_sec", 60))
        except Exception:
            self.auto_upload_interval = 60
        if self.auto_upload_interval < 10:
            self.auto_upload_interval = 10

        with open("settings/user_data.json", "r") as file:
            self.user_data = json.load(file)
        self.username = self.user_data["username"] # логин юзера
        self.password = self.user_data["password"] # пароль

        self.manual_request = None
        self.manual_mode = False
        self.manual_include_existing = False
        self.manual_date_from = None
        self.manual_date_to = None
        self.manual_room = None
        self.manual_paths = []

        # раз в 7 дней делаем проверку, что дефолтные пути есть и тречатся
        if os.path.exists("settings/services.json"):
            self.manager["text"] = "Проверка стандартных путей румов"
            with open("settings/services.json", 'r') as file:
                services = json.load(file)
            # если добавлены новые пути для отслеживания
            path_checker.run_check(tk.Tk(), services, False)
        # открываем файл конфигурации сервисов
        with open("settings/services.json", "r") as file:
            self.services_data = json.load(file)
        self.rooms = {} # имя рума - список путей к каталогам
        for room in self.services_data["services"]:
            if self.services_data["services"][room]["folders"] != [] and self.services_data["services"][room]["track"]:
                self.rooms[room] = self.services_data["services"][room]["folders"]

                
        write_status("idle", "Ожидание отправки")
        asyncio.run(self.show_alert())

    def load_manual_request(self):
        manual_path = os.path.join(base_dir, "settings", "manual_upload.json")
        if not os.path.exists(manual_path):
            return None
        try:
            with open(manual_path, "r", encoding="utf-8") as file:
                data = json.load(file)
        except Exception:
            data = None
        try:
            os.remove(manual_path)
        except Exception:
            pass
        return data

    def _parse_date(self, value):
        if not value:
            return None
        value = str(value).strip()
        for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d.%m.%y"):
            try:
                return datetime.strptime(value, fmt).date()
            except Exception:
                continue
        return None

    def _parse_version_parts(self, value):
        value = str(value).strip()
        if not value:
            return None
        pieces = value.split(".")
        if len(pieces) < 3:
            return None
        date_str = ".".join(pieces[:3])
        for fmt in ("%d.%m.%Y", "%d.%m.%y"):
            try:
                date_val = datetime.strptime(date_str, fmt)
                build_num = 0
                if len(pieces) > 3 and pieces[3].isdigit():
                    build_num = int(pieces[3])
                return date_val, build_num
            except Exception:
                continue
        return None

    def _is_newer_version(self, server_version, local_version):
        if not server_version:
            return False
        s_parts = self._parse_version_parts(server_version)
        l_parts = self._parse_version_parts(local_version)
        if s_parts and l_parts:
            if s_parts[0] != l_parts[0]:
                return s_parts[0] > l_parts[0]
            return s_parts[1] > l_parts[1]
        return server_version != local_version


    def timer_close(self, text="", timer=0, color="red"):
        # завершает работу программы по истечении времени
        self.manager["downloaded"] = None
        self.manager["progress"] = None
        self.manager["color"] = color
        if self.auto_upload:
            self.manager["text"] = text
            return
        for t in range(timer, 0, -1):
            self.manager["text"] = f"{text}\nВыход через {t}с."
            time.sleep(1)
        os._exit(0)

    def click_close(self, text=""):
        # завершает работу ПО по клику мыши в окне
        self.manager["downloaded"] = None
        self.manager["progress"] = None
        self.manager["text"] = f"{text}\nДля выхода кликните мышкой в этом окне"
        self.manager["mouse_click"] = False
        if self.auto_upload:
            return
        while not self.manager["mouse_click"]:
            time.sleep(0.1)
        os._exit(0)

    def show_error(self, text, timer=0):
        # завершает работу программы по истечении времени
        self.manager["downloaded"] = None
        self.manager["progress"] = None
        self.manager["color"] = "red"
        self.manager["text"] = text
        for t in range(timer, 0, -1):
            time.sleep(1)
        return

    async def plus_uploaded_counter(self):
        # функция для добавления в счётчик отправленных файлов 1
        self.manager['uploaded_count'] += 1
        current = self.manager['uploaded_count']
        total_files = self.manager['files_count']
        # высчитываем, сколько это в процентах
        percentage = int(current / total_files * 100)
        self.manager["downloaded"] = f"{current} из {total_files}"
        self.manager["text"] = None
        self.manager["progress"] = percentage

    async def show_alert(self):
        self.loop = asyncio.get_event_loop()
        self.loop.create_task(self.check_processes())

        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=None)) as self.session:
            # показ предупреждения
            self.manager["text"] = "Проверка актуальной версии ПО..."
            self.manager["color"] = "white"

            version_path = "ver"
            if os.path.isdir(version_path):
                version_path = os.path.join("ver", "ver")
            if os.path.isfile(version_path):
                with open(version_path, "r") as file:
                    self.version = file.readline()
            else:
                self.version = "1.0"

            # запрашиваем номер актуальной версии ПО с сервера
            server_version = await http_client.check_update(
                URL=self.server_url,
                session=self.session,
            )

            server_version = "" if server_version is None else str(server_version).strip()
            local_version = str(self.version).strip()

            if server_version in ("", "200"):
                # если ошибка при запросе версии
                self.manager["color"] = "red"
                write_status("error", "Не удалось проверить обновления")
                self.click_close(text="Не удалось проверить обновления! Проверьте интернет соединение и перезапустите программу!")
                return

            if self._is_newer_version(server_version, local_version):
                self.manager["color"] = "red"
                write_status("update", "Требуется обновление клиента")
                self.click_close(text="Ваша версия ПО устарела!\nЗапустите FireStorm, и загрузите обновление для дальнейшей работы с программой!")
                return

            # если у юзера последняя версия, то продолжаем
            self.user_accept = False # согласился ли юзер продолжить
            if self.auto_upload:
                self.manager["text"] = "Автоотправка включена. Проверка процессов..."
                self.manager["color"] = "white"
                write_status("idle", "Автоотправка включена")
                await asyncio.sleep(1)
                await self.accept()
            else:
                self.manager["text"] = "ВНИМАНИЕ!\nИспользование этой программы при любом запущенном клиенте\nрума ЗАПРЕЩЕНО!\n\nДля начала отправки нажмите мышкой в это окно."
                self.manager["color"] = "white"
                write_status("idle", "Ожидание подтверждения пользователя")

                self.manager["mouse_click"] = False
                # пока юзер не нажал ЛКМ, ждём...
                while not self.manager["mouse_click"]:
                    await asyncio.sleep(0.1)

                #
                self.manager["text"] = "Начинаем сканирование процессов..."
                self.manager["color"] = "white"
                # если вышли из цикла - значит юзер принял предупреждение
                await self.accept()

    async def accept(self):
        # метод вызывается, когда юзер принимает ответственность за запуск ПО

        # если найден процесс рума:
        if self.process_finded:
            # self.manager["color"] = "red"
            # self.timer_close(text="Найден запущенный процесс рума!\nЗавершение работы программы!", timer=3)
            return

        # если не указан логин/пароль юзера
        if not self.username or not self.password:
            # Запускаем отправку в отдельном потоке, чтобы не блокировать окно
            self.manager["color"] = "red"
            write_status("error", "Неверный логин или пароль")
            self.click_close(text="Неверный логин или пароль!\nЗапустите FireStorm и проверьте корректность учётных данных!")
            
            return

        self.manager["text"] = "Попытка авторизации..."
        self.manager["color"] = "white"

        # если пустой словарь - значит не включен трекинг либо не каталогов
        if self.rooms == {}:
            await http_client.send_log(URL=self.server_url, username=self.username, error="У клиента неправильно заданы пути к рукам либо выключен трекинг!", session=self.session)
            self.manager["color"] = "red"
            write_status("error", "Трекинг выключен или нет путей")
            self.click_close(text="Запустите FireStorm и проверьте правильность указанных путей к рукам!")

            return
        
        # попытка авторизации
        try:
            status = await http_client.autorization(URL=self.server_url, \
                username=self.username, \
                password=self.password, \
                session=self.session, \
                time_offset=True)

        except aiohttp.ClientConnectorError:
            self.manager["color"] = "red"
            write_status("error", "Не удалось подключиться к серверу")
            self.click_close(text="Не удалось авторизоваться!\nОшибка подключения к серверу!\nПопробуйте ещё раз...")
            return

        else:
            # проверяем, залогинились-ли мы
            if status[0] == 205:
                # если да - записываем ключ аутентификации от сервера
                self.auth_key = status[-1]
                self.file_server = status[1] # адрес сервера для приёма файлов
                self.route = status[2]
            else:
                await http_client.send_log(URL=self.server_url, username=self.username, error=f"Клиент получил status при авторизации: {str(status)} [server={self.server_url}]!", session=self.session)
                write_status("error", "Ошибка авторизации на сервере")
                return
            
            try:
                notice = await http_client.check_notice(URL=self.server_url, username=self.username, auth_key=self.auth_key, session=self.session)
                if notice:
                    notice_thread = Thread(target=self.show_notice, args=(notice,))
                    notice_thread.daemon = True
                    notice_thread.start()
                else:
                    print("Для Вас нет уведомлений на сервере")
            except Exception as error:
                print(error)

        self.manager["text"] = "Сканируем файлы... Подождите"
        self.manager["color"] = "white"
        # вызываем сканер файлов
        if self.auto_upload:
            while True:
                await self.check_start()
                await asyncio.sleep(self.auto_upload_interval)
        else:
            await self.check_start()

        return

    async def show_notice(self, notice):
        status = messagebox.showinfo(title="Уведомление", message=notice)
        await http_client.delete_notice(URL=self.server_url, username=self.username, auth_key=self.auth_key, session=self.session)


    async def check_start(self):
        # проходимся по путям и собираем файлы

        # проверка на запущенные процессы
        if self.process_finded:
            # self.manager["color"] = "red"
            # self.timer_close(text="Найден запущенный процесс рума!\nЗавершение работы программы!", timer=3)
            return

        # если процессы из тех, что прописаны в файле, не запущены, то
        files = [] # список списков файлов, которые будем по итогу отправлять
        # переменная для хранения кол-ва всех файлов всех румов!
        files_counter = 0
        local_files_counter = 0
        # проходимся по всем румам и отслеживаемым папкам
        for srv in self.rooms:
            room_name = srv
            dir_list = self.rooms[srv]
                
            files_on_server = []
            if not self.manual_mode or not self.manual_include_existing:
                self.manager["text"] = f"Получаем список файлов на сервере для рума: {room_name}..."
                self.manager["color"] = "white"
                timeout = 45
                while True:
                    files_on_server = await http_client.get_files(URL=self.file_server, route=self.route, username=self.username, room=room_name, auth_key=self.auth_key, session=self.session, timeout=timeout)

                    # если потеряно соединение с сервером
                    if files_on_server == 200:
                        self.manager["text"] = "Потеряно соединение с сервером...\nПопытка восстановления"
                        self.manager["color"] = "red"
                        self.manager["downloaded"] = None
                        self.manager["progress"] = None
                        timeout += 45 # увеличиваем таймаут ожидания ответа

                    elif files_on_server is None:
                        # невалидный ключ
                        if not await self.try_log_in():
                            self.manager["color"] = "red"
                            self.click_close(text="Ошибка при получении ключа аутентификации!\nПерезапустите программу!")
                    elif files_on_server != 300:
                        break

                    # ждём 1 секунду
                    await asyncio.sleep(1)

            # если невалидный ключ авторизации
            if files_on_server is None:
                # Запускаем отправку в отдельном потоке, чтобы не блокировать окно
                self.manager["color"] = "red"
                self.click_close(text="Ошибка при проверке ключа авторизации!\nПерезапустите программу!")
                return

                
            # проходимся по каталогам, которые мониторим
            self.manager["text"] = f"Определяем, какие файлы рума {room_name} нужно отправить на сервер..."
            self.manager["color"] = "white"

            for path in dir_list:
                # получаем список файлов из каталогов (абсолютные пути к файлам)
                finded_files = self.find_files(path=path, date_from=self.manual_date_from, date_to=self.manual_date_to)

                # формируем список файлов, которые нужно отправить на сервер (которых там ещё нет)
                finded_files_set = set(map(tuple, finded_files))
                files_on_server = set(map(tuple, files_on_server))
                files_counter += len(files_on_server)
                if self.manual_mode and self.manual_include_existing:
                    need_to_send = list(finded_files_set)
                else:
                    need_to_send = list(finded_files_set - files_on_server)
                local_files_counter += len(need_to_send)

                if need_to_send == [()] or need_to_send == []:
                    continue

                # записываем список [имя_рума, осн_путь, [пути_к_файлам]]
                files.append([room_name, path, need_to_send])


        if files:
            self.manager["text"] = "Начинаем отправку файлов на сервер..."
            self.manager["color"] = "white"
            write_status("sending", "Идет отправка файлов")
        
            # если есть файлы, которые нужно отправить
            status = await self.send_files(files=files)
            if status is False:
                # False возвращается, если найден запущенный процесс рума
                return
            elif status == True:
                # если файлы отправлены, обновляем дату отправки на серваке
                await http_client.update_send_date(URL=self.server_url, username=self.username, auth_key=self.auth_key, session=self.session)
                # выводим юзеру инфу
                total_sent = getattr(self, "_total_files", 0)
                write_status("ok", f"Отправлено файлов: {total_sent}", extra={"files_sent": total_sent})
                if self.auto_upload:
                    self.manager["text"] = "Отправка завершена"
                    self.manager["color"] = "green"
                    self.manager["downloaded"] = None
                    self.manager["progress"] = None
                    return True
                self.timer_close(text="Файлы отправлены!", timer=3, color="green")
        
        else:
            await http_client.update_send_date(URL=self.server_url, username=self.username, auth_key=self.auth_key, session=self.session)
            await http_client.send_log(URL=self.server_url, username=self.username, error="Не обнаружено файлов для передачи на сервер! Возможно, файлы были переданы ранее, неверно указан каталог с руками, либо файлов рук пока нет в указанном каталоге юзера!", level='log', session=self.session)
            write_status("idle", "Нет новых файлов для отправки")
            if self.auto_upload:
                self.manager["text"] = "Новых файлов нет"
                self.manager["color"] = "yellow"
                self.manager["downloaded"] = None
                self.manager["progress"] = None
                return False
            self.timer_close(text="Не найдено новых файлов для отправки на сервер!", timer=5, color="yellow")
            return


    async def send_files(self, files):
        # отправляем файлы, которые нужно отправить
        total_files = 0 # сколько файлов всего нужно отправить
        current = 0 # какой по счёту файл уже отправили
        # считаем кол-во файлов для отправки
        for sublist in files:
            for item in sublist:
                if isinstance(item, list):
                    total_files += len(item)

        self.manager['files_count'] = total_files
        self._total_files = total_files
        
        # print(f'Всего нужно отправить файлов: {total_files}')
        
        # высчитываем, сколько это в процентах
        percentage = int(current / total_files * 100)
        self.manager["downloaded"] = f"{current} из {total_files}"
        self.manager["text"] = None
        self.manager["progress"] = percentage

        # создаём таски для выполнения параллельно порциями
        # files == список [имя_рума, осн_путь, [пути_к_файлам]]
        semaphore = asyncio.Semaphore(100) # задаёт макс. параллельных отправок
        lock = asyncio.Lock() # для блокировки потока, чтобы не ломалась очередь записи данных
        tasks = []
        for room_name, main_path, files_list in files:
            tasks += [http_client.upload_file(
                                            client=self,
                                            filename=os.path.join(main_path, file_path[0]), 
                                            room=room_name, 
                                            sub_dirs=os.path.dirname(file_path[0]), 
                                            semaphore=semaphore, 
                                            lock=lock
                                            ) 
                                        for file_path in files_list]
        await asyncio.gather(*tasks)


        if len(files) > 0:
            print("Готово!")
        #
        return True


    async def try_log_in(self):
        # попытка авторизации
        while True:
            try:
                status = await http_client.autorization(URL=self.server_url, \
                    username=self.username, \
                    password=self.password, \
                    session=self.session, \
                    time_offset=True)
                # проверяем, залогинились-ли мы
                if status[0] == 205:
                    # если да - записываем ключ аутентификации от сервера
                    self.auth_key = status[-1]
                    self.file_server = status[1] # адрес сервера для приёма файлов
                    self.route = status[2]
                    return True
                # если сервер ответил, что не удалось залогиниться
                else:
                    self.manager["color"] = "red"
                    self.click_close(text="Не удалось авторизоваться!\nОшибка подключения к серверу!\nПопробуйте ещё раз...")
                # если не удалось авторизоваться
                return None

            except aiohttp.ClientConnectorError as e:
                print(f"Ошибка соединения с сервером: {e}")
                return None

    # функция принимает путь к папке, и возвращает список файлов в ней
    def find_files(self, path, date_from=None, date_to=None): #, size_limit=1024):
        small_files = [] # сюда попадают названия файлов

        # size_limit *= 1024  # переводим килобайты в байты

        if os.path.exists(path):
            # проходим по всем файлам и подпапкам
            for root, dirs, files in os.walk(path):
                for file in files:
                    full_path = os.path.join(root, file)

                    # если размер файла не превышает предел (я это перенёс в http_client в отправку файлов!)
                    # if os.path.getsize(full_path) < size_limit or file.lower().endswith('txt'):

                    # Игнорим пустые файлы
                    if os.path.getsize(full_path) < 1:
                        continue

                    # если расширение файла то, что нужно
                    file_extension = os.path.splitext(file)[1][1:]
                    if file_extension and file_extension in self.FILE_TYPES:
                        if date_from or date_to:
                            file_date = date.fromtimestamp(os.path.getmtime(full_path))
                            if date_from and file_date < date_from:
                                continue
                            if date_to and file_date > date_to:
                                continue
                        # добавляем в список файлов относительный путь
                        relative_path = os.path.relpath(full_path, path)

                        # просчитываем хеш только для db-файлов
                        if file.lower().endswith("db"):
                            # Вычисляем MD5 контрольную сумму файла
                            with open(full_path, 'rb') as f:
                                md5_hash = hashlib.md5()
                                while chunk := f.read(4096):
                                    md5_hash.update(chunk)
                                checksum = md5_hash.hexdigest()
                        else:
                            checksum = None

                        small_files.append([relative_path, checksum])

        else:
            print("Указанный путь не существует")
        # возвразаем список путей к найденным файлам
        return small_files

    async def check_processes(self):
        # Проверка запущенных процессов

        # Путь к файлу processes.ini
        file_path = 'settings/processes.ini'
        # Чтение содержимого файла
        with open(file_path, 'r') as file:
            processes = file.read().splitlines()
        while True:
            all_processes = [p.name().lower() for p in psutil.process_iter()]
            for process in processes:
                for running in all_processes:
                    if process.lower() in running.lower():
                        print(f"Обнаружен процесс {str(process)}! Завершаю работу!")
                        self.process_finded = True  
                        self.timer_close(text="Найден запущенный процесс рума!\nЗавершение работы программы!", timer=3, color="red")
                        return False
                        # заходим в вечный цикл чтобы не отправлялись файлы
                        return
                await asyncio.sleep(0.05)
            await asyncio.sleep(0.9)



# для запуска скрипта
main_window = Window(size=220)

# общай словарь для потоков
name_space = dict()
name_space["size"] = 12
name_space["color"] = "white"
name_space["downloaded"] = None
name_space["text"] = None
name_space["progress"] = 0
name_space["files_count"] = 0
name_space["uploaded_count"] = 0

# по дефолту стоит бинд на клик мыши в окно. Когда кликаем - "mouse_click" == True 
name_space["mouse_click"] = False # флаг, было-ли выполнено действие юзером (клик мыши в окно)

# запускаем в потоке GUI, чтобы не блокировать отрисовку
gui_process = Thread(target=main_window.start, args=(name_space,))
gui_process.daemon = False
gui_process.start()

# движок запросов на сервер
engine = HTTP_Client(manager=name_space)    

gui_process.join()
