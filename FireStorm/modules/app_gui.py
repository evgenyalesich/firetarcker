import tkinter as tk
from tkinter import messagebox
import aiohttp
import asyncio
import threading
import json
import os
import subprocess
# самописные модули
import modules.http_client as http_client
import modules.log_in_form as log_in_form
import modules.main_window as main_window
import modules.update_progressbar as progressbar
# 
import modules.paths_checker as path_checker

def load_user_data():
    # пытаемся считать логин-пароль
    if not os.path.exists("settings/user_data.json"):
        return None
    with open("settings/user_data.json", "r") as file:
        user_data = json.load(file)
    return user_data


class PokerCheckApp():
    # главный класс ГУИ
    def __init__(self, parent, url, height, width):
        # ключ аутентификации
        self.auth_key = ""
        # адрес сервера
        self.server_url = url
        #
        self.parent = parent
        # шрифт для текста и размер
        self.font = ("calibri", 12)
        self.username = ""
        self.password = ""
        self.height = height
        self.width = width

        # если обнаружена обнова, и юзер согласился её скачать, то скачиваем и ставим
        version_path = "ver"
        if os.path.isdir(version_path):
            version_path = os.path.join("ver", "ver")
        if os.path.isfile(version_path):
            with open(version_path, "r") as file:
                self.version = file.readline()
        else:
            self.version = "1.0"

        self.window = tk.Tk()
        self.window.withdraw()

        self.window.after(0, self.create_widgets)

        self.window.mainloop()


    def get_update(self):
        # метод запускает загрузку и установку обновления
        status = False
        bar = progressbar.ProgressBarWindow(size=220)
        while True:
            try:
                status = asyncio.run(
                    http_client.get_update(
                        URL=self.server_url,
                        bar=bar,
                    )
                )
                # если сработал таймаут
                if status == False:
                    # Обработка ошибки таймаута чтения чанка
                    bar.connection_error()

            except Exception as error:
                print(f"Ошибка при загрузке обновления: {error}")
                bar.connection_error()


            # проверяем, загрузилась ли обнова
            if status == True:
                print("обновление загружено!")
                # запускаем ПО для обновления софта
                python_path = f"{os.path.join(os.path.dirname(os.getcwd()), 'pythonw.exe')}"
                script_path = f"{os.path.join(os.getcwd(), 'update_installer.py')}"
                subprocess.Popen([f'{python_path}', script_path], shell=True)
                os._exit(0)

    
    def check_update(self):
        try:
            server_version = asyncio.run(http_client.check_update(URL=self.server_url))
            if server_version == None:
                print("Не удалось получить информацию о обновлениях с сервера!")
                return
            asyncio.run(http_client.send_log(URL=self.server_url, username="", error=f"Версия ПО пользователя: {self.version}", level='log'))
            if server_version == "":
                print("Не обнаружено обновлений на сервере")
                return
            # если версия на сервере отличается от нашей, то выводим окно для загрузки обновы
            if server_version != self.version:
                # если раскомментить, то при отказе от обновы и последующей загрузке лейаута софт вылетит
                # temp_window = tk.Tk()
                # temp_window.withdraw()
                response = messagebox.askyesno(title="FireStorm", message=f"Доступна новая версия ПО ({server_version}). Загрузить обновление?", icon=messagebox.QUESTION)
                # temp_window.destroy()
                if response == True:
                    asyncio.run(http_client.send_log(URL=self.server_url, username="", error="Пользователь начал загрузку обновления...", level='log'))
                    self.get_update()
                else:
                    asyncio.run(http_client.send_log(URL=self.server_url, username="", error="Пользователь отказался от загрузки обновления!", level='log'))
                    return
        except Exception as e:
            try:
                text = f"Ошибка при проверке обновлений {e}"
                asyncio.run(http_client.send_log(URL=self.server_url, username=self.username, error=str(e)))
            except:
                print("app_gui не удалось отправить лог")
            print(f"Ошибка при запросе актуальной версии ПО: {e}")

    def create_widgets(self):

        # если запустить не в потоке, то гл. окно не будет создано, и произойдёт зависание
        thread = threading.Thread(target=self.check_update)
        thread.daemon = True
        thread.start()        

        self.window.resizable(False, False)
        self.window.title(f"FireStorm v{self.version}")
        self.window.iconbitmap("img/gui_icon.ico")

        self.log_in_frame = log_in_form.LogInForm(tk.Frame(self.window, borderwidth=0, relief="flat", highlightthickness=0), self.login, height=self.height, width=self.width) # создаём элементы в фрейме авторизации
        self.log_in_frame.pack()
        self.main_frame = main_window.MainWindow(frame=tk.Frame(self.window, borderwidth=0, relief="flat", highlightthickness=0), parent=self, height=self.height, width=self.width)
        #
        if self.log_in_frame.login_entry.get() and self.log_in_frame.password_entry.get():
            thread = threading.Thread(target=self.log_in_frame.on_click, args=(None,))
            thread.daemon = True
            thread.start()

        if os.path.exists('news.txt'):
            try:
                with open(file='news.txt', mode='r', encoding='utf8') as file:
                    whats_news = file.read()
                info_window = messagebox.showinfo(title='Обновление установлено!', message=whats_news)
                os.remove('news.txt')
            except Exception as error:
                print(f"Ошибка чтения файла news.txt: {error}")
        else:
            print('Файла news.txt не найдено!')

        self.window.deiconify()

            
    def login(self):
        # проверяем длину логина/пароля
        if len(self.log_in_frame.login_entry.get()) < 4 or len(self.log_in_frame.login_entry.get()) > 20:
            thread = threading.Thread(target=self.log_in_frame.invalid_data_window)
            thread.daemon = True
            thread.start()
            return
        if len(self.log_in_frame.password_entry.get()) < 4 or len(self.log_in_frame.password_entry.get()) > 20:
            thread = threading.Thread(target=self.log_in_frame.invalid_data_window)
            thread.daemon = True
            thread.start()
            return
        try:
            self.window.update_idletasks()
            self.window.update()
            status = asyncio.run(http_client.autorization(URL=self.server_url, \
                username=self.log_in_frame.login_entry.get(), \
                password=self.log_in_frame.password_entry.get()))
        except aiohttp.ClientConnectorError as e:
            # Ошибка при подключении к серверу
            thread = threading.Thread(target=self.log_in_frame.connection_error_window)
            thread.daemon = True
            thread.start()
        else:
            text = ""
            if status[0] == 205:
                # Успешная авторизация
                self.log_in_frame.canvas.tag_bind("log_in_button", "<Enter>", self.log_in_frame.on_enter)
                self.log_in_frame.canvas.tag_bind("log_in_button", "<Leave>", self.log_in_frame.on_leave)
                self.log_in_frame.canvas.tag_bind("log_in_button", "<Button-1>", self.log_in_frame.on_click)
                self.log_in_frame.canvas.itemconfig("log_in_button", image=self.log_in_frame.log_in_btn_tk)
                # записываем в файл логин-пароль
                self.auth_key = status[-1]
                self.username = self.log_in_frame.login_entry.get()
                self.password = self.log_in_frame.password_entry.get()
                self.save_user_data(username=self.log_in_frame.login_entry.get(), password=self.log_in_frame.password_entry.get())
                self.file_server = status[1] # адрес сервера приёма файлов
                self.route = status[2] # направление
                #
                self.log_in_frame.pack_forget()
                self.main_frame.pack()
                try:
                    notice = asyncio.run(http_client.check_notice(URL=self.server_url, username=self.username, auth_key=self.auth_key))
                    if notice:
                        notice_thread = threading.Thread(target=self.show_notice, args=(notice,))
                        notice_thread.daemon = True
                        notice_thread.start()
                    else:
                        print("Для Вас нет уведомлений на сервере")
                except Exception as error:
                    print(error)
                # функция для проверки дефолтных путей
                # paths_checker_thread = threading.Thread(
                #     target=path_checker.run_check,
                #     args=(self.window, "settings/services.json"))
                # paths_checker_thread.daemon = True
                # paths_checker_thread.start()

                if os.path.exists("settings/services.json"):
                    with open("settings/services.json", 'r') as file:
                        services = json.load(file)
                else:
                    return
                new_paths = path_checker.run_check(self.window, services, True)
                # если добавились новые пути для отследивания
                if new_paths:
                    with open("settings/services.json", 'r') as file:
                        services = json.load(file)["services"]
                    for name, srv in self.main_frame.tab.items():
                        # Если какие-то пути есть
                        if services.get(name, {}).get('folders'):
                            # включаем трекинг
                            self.main_frame.tab[name].dirs_listbox.items = services[name]["folders"]
                            self.main_frame.tab[name].dirs_listbox.update_listbox()
                            if not self.main_frame.tab[name].tracking:
                                print(f"включен трекинг на {name}")
                                self.main_frame.goto_tab(tag_name=name, event=None)  
                                self.main_frame.tab[name].switch_tracking()              

            elif status[0] == 505:
                # Неверный пароль
                thread = threading.Thread(target=self.log_in_frame.invalid_data_window)
                thread.daemon = True
                thread.start()
            elif status[0] == 506:
                # Данный юзер не зарегистрирован
                thread = threading.Thread(target=self.log_in_frame.invalid_data_window)
                thread.daemon = True
                thread.start()
            else:
                # Ошибка при подключении к серверу
                thread = threading.Thread(target=self.log_in_frame.connection_error_window)
                thread.daemon = True
                thread.start()

    def show_notice(self, notice):
        status = messagebox.showinfo(title="Уведомление", message=notice)
        asyncio.run(http_client.delete_notice(URL=self.server_url, username=self.username, auth_key=self.auth_key))
         
    def save_user_data(self, username, password):
        # сохраняем логин-пароль после удачной авторизации
        data = {
            "username": username,
            "password": password
        }
        with open("settings/user_data.json", "w") as file:
            json.dump(data, file)
