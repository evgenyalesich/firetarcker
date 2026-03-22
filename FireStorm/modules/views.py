"""
вкладка views
"""

from tkinter import filedialog
from tkinter import Toplevel, Label
from tkinter import messagebox
from PIL import ImageTk, Image
#
import threading
import tkinter as tk
import os
import ctypes
import asyncio
import shutil
import zipfile
from pathlib import Path
import json
import subprocess
import sys


import webbrowser
#
import modules.polygons as polygons 
import modules.http_client as http_client

def get_desktop():
    # для определения пути к Desktop

    # определяем ОС
    os_name = sys.platform
    print(f"ОС: {os_name}")
    if os_name == "darwin" or os_name.startswith("linux"):
        desktop_path = Path.home() / "Desktop"
        return str(desktop_path) if desktop_path.exists() else None

    try:
        from ctypes import wintypes, windll

        CSIDL_DESKTOP = 0
        SHGFP_TYPE_CURRENT = 0

        buffer = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
        result = windll.shell32.SHGetFolderPathW(0, CSIDL_DESKTOP, 0, SHGFP_TYPE_CURRENT, buffer)

        if result != 0:
            raise Exception("Error obtaining the desktop path")

        desktop_path = Path(buffer.value)

        return str(desktop_path)
    except Exception as error:
        print(f"Не удалось определить путь в Desktop: {error}")
        return None


def open_path(path):
    if sys.platform.startswith("win"):
        os.startfile(path)
        return
    opener = "open" if sys.platform == "darwin" else "xdg-open"
    subprocess.run([opener, path], check=False)

class Views():
    def __init__(self, parent, height, width):
        self.parent = parent
        self.frame = parent.canvas # canvas в котором будет отрисована панель переключения вкладок
        self.active = False # флаг, который указывает, находится ли фрейм в главном окне или нет
        self.width = width
        self.height = height
        self.server_url = parent.server_url
        self.canvas = tk.Canvas(self.parent.frame, width=self.width, height=self.height, bg="#1E1E1E")
        self.help_button = None



        # словарь, в котором будут храниться объекты фреймов для румов (Room)
        self.tab = {}
        # self.services = parent.services
        # считываем, какие стили есть, чтобы наполнить вкладками панель слева
        folder_path = "layouts"
        if os.path.exists(folder_path) and os.path.isdir(folder_path):
            # если в папке лейаута нет конфига - не выводим его в панель слева
            self.services = [name for name in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, name)) and\
                os.path.exists(f"layouts/{name}/config.json")]
        else:
            self.services = []

        self.panel_tags = []

        self.load_images()
        self.x_offset = self.logo_image_tk.width()*1.1 # высчитываем смещение вправо
        self.y_offset = self.height//8+(self.logo_image_tk.height()//8)
        self.add_buttons() # кнопки для верхней панели переключателя вкладок и выхода из акка
        self.create_elements()
        self.bind_elements()
        self.create_left_panel() # создаём левую панель румов

    def delete_custom_button(self):
        if self.help_button:
            self.canvas.tag_unbind(self.help_button[0], '<Motion>')
            self.canvas.tag_unbind(self.help_button[0], '<Leave>')
            self.canvas.tag_unbind(self.help_button[0], '<Button-1>')
            #
            self.canvas.tag_unbind(self.help_button[1], '<Motion>')
            self.canvas.tag_unbind(self.help_button[1], '<Leave>')
            self.canvas.tag_unbind(self.help_button[1], '<Button-1>')
            #
            self.canvas.delete(self.help_button[0])
            self.canvas.delete(self.help_button[1])
            self.help_button = None


    def create_custom_button(self, x, y, radius, url):
        # кнопка помощи по установке лейаута
        tooltip = None  # переменная для сохранения всплывающей подсказки

        def on_enter(event):
            nonlocal tooltip
            on_leave(event)
            self.canvas.itemconfig(circle, fill="light blue")  # Сделать цвет круга светлее
            tooltip = Toplevel(self.canvas)
            tooltip.wm_overrideredirect(True)
            tooltip.geometry("+{}+{}".format(event.x_root + 10, event.y_root + 10))
            label = Label(tooltip, text="Нажмите для\nполучения инструкции", background="white")
            label.pack()

        def on_leave(event):
            nonlocal tooltip
            self.canvas.itemconfig(circle, fill="blue")  # Вернуть исходный цвет
            if tooltip:
                tooltip.destroy()
                tooltip = None

        def on_click(event):
            webbrowser.open(url)  # Открыть ссылку в браузере

        # Рисуем круг
        circle = self.canvas.create_oval(x - radius*2, y + radius*2, x, y, fill="blue", outline="")
        self.canvas.tag_raise(circle)

        # Рисуем вопросительный знак
        question_mark = self.canvas.create_text(x - radius, y + radius, text="?", font=("Arial", radius), fill="white")
        self.canvas.tag_raise(question_mark)  # Переносим на передний план

        if self.help_button:
            self.delete_custom_button()

        # Добавляем события
        self.canvas.tag_bind(circle, '<Motion>', on_enter)
        self.canvas.tag_bind(circle, '<Leave>', on_leave)
        self.canvas.tag_bind(circle, '<Button-1>', on_click)

        self.canvas.tag_bind(question_mark, '<Motion>', lambda event: on_enter(event))
        self.canvas.tag_bind(question_mark, '<Leave>', lambda event: on_leave(event))
        self.canvas.tag_bind(question_mark, '<Button-1>', on_click)

        self.help_button = (circle, question_mark)

    def load_images(self):
        logo_image = Image.open("img/logo.png")
        self.logo_image_tk = ImageTk.PhotoImage(logo_image)
        #
        img = Image.open("img/download_layout_button.png")
        self.download_button_image_tk = ImageTk.PhotoImage(img)
        img = Image.open("img/download_layout_button_focus.png")
        self.download_button_focus_image_tk = ImageTk.PhotoImage(img)
        img = Image.open("img/download_layout_button_pressed.png")
        self.download_button_pressed_image_tk = ImageTk.PhotoImage(img)
        img = Image.open("img/set_path_layout_button.png")
        self.path_layout_button_image_tk = ImageTk.PhotoImage(img)
        img = Image.open("img/set_path_layout_button_focus.png")
        self.path_layout_button_focus_image_tk = ImageTk.PhotoImage(img)

    def create_left_panel(self):
        if not self.services:
            return
        # добавляем в список вкладок румы
        for srv in self.services:
            self.tab[srv] = Room(name=srv, frame=self.tab_frame, parent=self)
            # запускаем в потоке расстановку дефолтных картинок чтобы не вис основной поток при запуске ПО
            thread = threading.Thread(target=self.tab[srv].active)
            thread.daemon = True
            thread.start()
            try:
                self.add_tab_to_panel(name=srv)
            except:
                continue

        # делаем активным первый рум
        try:
            self.goto_tab(tag_name=next(iter(self.services)), event=None)
        except:
            pass
        # проверка, вмещаются-ли все элементы на панель слева
        coords = self.canvas.bbox(self.canvas.find_withtag("rectangle"))
        if coords == None:
            return
        height = coords[3]-coords[1]
        if height*len(self.services)+self.logo_image_tk.height() > self.height:
            # если не вмещаются, отрисовываем 2 треугольника навигации
            # нужно высчитать координаты для обеих треугольников. x это шири
            x = coords[2] # правая граница прямоугольника выбора рума
            y = self.height//2 # высота окна // 2
            offset = self.logo_image_tk.height()//2 # расстояние между треугольниками
            triangle_up = polygons.round_polygon(self.canvas, [x+5, x+13, x+21], [y+6-offset, y-3-offset, y+6-offset],\
            sharpness=1 , width=1, outline="#353535", fill="#353535")

            triangle_down = polygons.round_polygon(self.canvas, [x+5, x+13, x+21], [y-3+offset, y+6+offset, y-3+offset],\
            sharpness=1 , width=1, outline="#353535", fill="#353535")

            self.canvas.tag_bind(triangle_up, "<Enter>", lambda event: self.triangle_enter(tag=triangle_up))
            self.canvas.tag_bind(triangle_up, "<Leave>", lambda event: self.triangle_leave(tag=triangle_up))
            self.canvas.tag_bind(triangle_up, "<Button-1>", lambda event: self.on_mousewheel(event=None, delta=120))

            self.canvas.tag_bind(triangle_down, "<Enter>", lambda event: self.triangle_enter(tag=triangle_down))
            self.canvas.tag_bind(triangle_down, "<Leave>", lambda event: self.triangle_leave(tag=triangle_down))
            self.canvas.tag_bind(triangle_down, "<Button-1>", lambda event: self.on_mousewheel(event=None, delta=-120))

    # Обработчик события "Enter"
    def triangle_enter(self, tag):
        self.canvas.itemconfig(tag, fill="#ffffff", outline="#ffffff")

    # Обработчик события "Leave"
    def triangle_leave(self, tag):
        self.canvas.itemconfig(tag, fill="#353535", outline="#353535")

    def goto_tab(self, tag_name, event):
        self.canvas.delete("rectangle")
        # Получение координат текста
        x1, y1, x2, y2 = self.canvas.bbox(tag_name)
        # получаем смещение
        offset = self.logo_image_tk.height()//8
        # Создание прямоугольника
        rect_tag = self.canvas.create_rectangle(0, y1-offset, self.logo_image_tk.width(), y2+offset, fill="#353535", tags="rectangle", outline="")
        self.panel_tags.append(rect_tag)
        # Помещение прямоугольника за текстом
        self.canvas.tag_lower("rectangle")

        # вызываем метод activate класса Room для этого объекта
        self.tab[tag_name].active()

    def add_tab_to_panel(self, name):
        # метод для добавления кнопки перехода к настройкам рума на панель слева
        text_id = self.canvas.create_text(self.logo_image_tk.width()//2,\
            self.height//8+(self.logo_image_tk.height()//2*len(self.tab)),\
            text=name, font=("Arial", 14), \
            anchor=tk.CENTER, fill="white", tags=name)
        self.canvas.tag_bind(name, "<Enter>", lambda event: self.change_text_color(tag_name=name, canvas=self.canvas, event=event))
        self.canvas.tag_bind(name, "<Leave>", lambda event: self.restore_text_color(tag_name=name, canvas=self.canvas, event=event))
        # бинд перехода ко вкладке при нажатии ЛКМ
        self.canvas.tag_bind(name, "<Button-1>", lambda event: self.goto_tab(tag_name=name, event=event))

        # добавляем доп. теги для бинда прокрутки
        self.panel_tags.append(text_id)
        self.canvas.lower(text_id)


    def on_mousewheel(self, event=None, delta=None):
        # Получаем значение прокрутки колесика мыши
        if not delta:
            delta = event.delta
        # если листаем вниз
        if delta < 0:
            delta = -120
            if self.canvas.bbox(self.canvas.find_withtag(self.services[-1]))[3] <= self.height:
                return
        elif delta > 0:
            delta = 120
            if self.canvas.bbox(self.canvas.find_withtag(self.services[0]))[1] >= self.logo_image_tk.height():
                return
        # Сдвигаем каждый элемент вверх или вниз на значение delta
        for element in self.panel_tags:
            self.canvas.move(element, 0, delta)

    def add_buttons(self):
        # положение кнопки Views привязано к первой кнопке. Значит меняя положение первой кнопки
        # будет меняться и положение второй

    	# создаём кнопки переключения вкладок
        # на положение именно этой кнопки ориентируются все остальные во всех фреймах!
        main_x = self.logo_image_tk.width()*1.2 # эти координаты можно
        main_y = self.logo_image_tk.height()//2 # менять

        settings_tab = self.frame.create_text(main_x,\
            main_y,\
            text="Tracker", font=("Arial", 14), \
            anchor="w", fill="#C71B74", tags="settings_btn")
        x1, y1, x2, y2 = self.frame.bbox(settings_tab)

        constructor_tab = self.frame.create_text(x2+10,\
            main_y,\
            text="Layout constructor", font=("Arial", 14), \
            anchor="w", fill="white", tags="views_btn")
        x1, y1, x2, y2 = self.frame.bbox(constructor_tab)

        # создаём кнопку Log Out
        self.frame.create_text(x2+10,\
            main_y,\
            text="Log Out", font=("Arial", 14), \
            anchor="w", fill="white", tags="logout_btn")
        self.frame.tag_bind("logout_btn", "<Enter>", lambda event: self.parent.change_text_color(tag_name="logout_btn", event=event))
        self.frame.tag_bind("logout_btn", "<Leave>", lambda event: self.parent.restore_text_color(tag_name="logout_btn", event=event))
        self.frame.tag_bind("logout_btn", "<Button-1>", lambda event: self.parent.logout())

        settings_tab = self.canvas.create_text(main_x,\
            main_y,\
            text="Tracker", font=("Arial", 14), \
            anchor="w", fill="white", tags="settings_btn")
        x1, y1, x2, y2 = self.frame.bbox(settings_tab)

        constructor_tab = self.canvas.create_text(x2+10,\
            main_y,\
            text="Layout constructor", font=("Arial", 14), \
            anchor="w", fill="#C71B74", tags="views_btn")
        x1, y1, x2, y2 = self.frame.bbox(constructor_tab)

        # создаём кнопку Log Out
        self.canvas.create_text(x2+10,\
            main_y,\
            text="Log Out", font=("Arial", 14), \
            anchor="w", fill="white", tags="logout_btn")

    def create_elements(self):
    	# создаём элементы в окне
        self.canvas.create_image(0, 0, image=self.logo_image_tk, anchor=tk.NW)

        # создаю фрейм, в который будет помещён Canvas с содежимым вкладки
        self.tab_frame = tk.Frame(self.canvas, bg="#1E1E1E", highlightthickness=0)
        self.canvas.create_window(self.x_offset, self.y_offset, window=self.tab_frame, anchor=tk.NW)

    def bind_elements(self):
        self.frame.tag_bind("views_btn", "<Enter>", lambda event: self.change_text_color(tag_name="views_btn", canvas=self.frame, event=event))
        self.frame.tag_bind("views_btn", "<Leave>", lambda event: self.restore_text_color(tag_name="views_btn", canvas=self.frame, event=event))
        self.frame.tag_bind("views_btn", "<Button-1>", lambda event: self.views()) # прописать тут переход к другому фрейму

        self.canvas.tag_bind("settings_btn", "<Enter>", lambda event: self.change_text_color(tag_name="settings_btn", canvas=self.canvas, event=event))
        self.canvas.tag_bind("settings_btn", "<Leave>", lambda event: self.restore_text_color(tag_name="settings_btn", canvas=self.canvas, event=event))
        self.canvas.tag_bind("settings_btn", "<Button-1>", lambda event: self.settings()) # прописать тут переход к другому фрейму

        self.canvas.tag_bind("logout_btn", "<Enter>", lambda event: self.change_text_color(tag_name="logout_btn", canvas=self.canvas, event=event))
        self.canvas.tag_bind("logout_btn", "<Leave>", lambda event: self.restore_text_color(tag_name="logout_btn", canvas=self.canvas, event=event))
        self.canvas.tag_bind("logout_btn", "<Button-1>", lambda event: self.logout())

    def change_text_color(self, tag_name, canvas, event):
        canvas.itemconfig(tag_name, fill="#C71B74")

    def restore_text_color(self, tag_name, canvas, event):
        canvas.itemconfig(tag_name, fill="white")

    def logout(self):
        # для выхода из аккаунта
        self.active = False
        self.parent.parent.main_frame.pack_forget()
        # затираем сохраненный ранее логин и пароль
        self.parent.parent.save_user_data(username="", password="")
        self.parent.parent.log_in_frame.pack()

    def views(self):
        self.parent.canvas.unbind_all("<MouseWheel>")
        self.canvas.bind_all("<MouseWheel>", self.on_mousewheel)
        self.active = True
        self.parent.canvas.pack_forget()
        self.canvas.pack()

    def settings(self):
        self.canvas.unbind_all("<MouseWheel>")
        self.parent.canvas.bind_all("<MouseWheel>", self.parent.on_mousewheel)
        self.active = False
        self.canvas.pack_forget()
        self.parent.canvas.pack()

class Room:
    '''
    класс для создания румов (создаёт canvas и элементы в нем для каждой вкладки)
    '''
    def __init__(self, name, frame, parent):
        self.name = name
        self.frame = frame
        self.parent = parent
        self.rectangle_size = 60
        self.first_activate = True # флаг, обозначающий что данная вкладка открывается впервые (нужно для отрисовки дефолтных изображений)
        self.names = ["Background","Texture","Cloth color","Chips","Front card","Back card"]
        self.sub_canvas = tk.Canvas(frame, width=self.parent.width-parent.x_offset, height=self.parent.height-parent.y_offset, bg="#1E1E1E", borderwidth=0, relief="flat", highlightthickness=0)
        self.img_chooser = {} # словарь для окошек 3Х3
        self.normal = True
        self.create_selectors() # 2 столбца по 3 кнопки селекторов
        # создание вьювера
        x = self.sub_canvas.bbox(self.selectors[self.names[1]].triangle)[2]+self.rectangle_size//2
        y = self.sub_canvas.bbox(self.selectors[self.names[1]].box)[1]

        width = parent.width-parent.x_offset-x-self.rectangle_size//2
        aspect_ratio = 3/2
        height = width / aspect_ratio # высчитываем по соотношению сторон

        self.conf_data = self.load_json()

        # если не удалось считать настройки из файла
        if not self.conf_data:
            self.sub_canvas.delete(tk.ALL)
            self.normal = False
            self.sub_canvas.create_text((self.parent.width-parent.x_offset)//2,\
                (self.parent.height-parent.y_offset)//2,\
                text="Файл config.json некорректен или отсутствует! Попробуйте переустановить ПО!", font=("Arial", 14), \
                anchor="center", fill="#C71B74")
            return

        self.viewer = ViewerScreen(parent=self, x=x, y=y, \
            width=width,\
            height=height,\
            canvas=self.sub_canvas) # экран для отображения результатов
        self.downloader = LayoutDownloader(parent=self)
        

    def load_json(self):
        # загрузка конфигов из файла
        if os.path.exists(f"layouts/{self.name}/config.json"):
            try:
                with open(f"layouts/{self.name}/config.json", "r") as file:
                    conf_data = json.load(file)
                return conf_data
            except:
                return None
        else:
            return None

    def draw_default(self):
        '''
        метод для отрисовки доступных элементов в вьювере. Берёт первые изображения из ячеек и расставляет их
        '''
        for name in self.names:
            if self.img_chooser[name].images:
                self.img_chooser[name].draw(on_canvas=False)
                self.img_chooser[name].cells[0].selected()

    def active(self):
        # кнопка помощи по установке лейаута
        button_radius = 38
        if self.conf_data and "help_link" in self.conf_data and not self.first_activate and self.conf_data["help_link"]:
            self.parent.create_custom_button(self.parent.width-button_radius//4, button_radius//4, button_radius, self.conf_data["help_link"])
        else:
            self.parent.delete_custom_button()


        # метод для активации вкладки (вызывается при нажатии ЛКМ)
        if not self.normal:
            if self.first_activate:
                self.first_activate = False
                return
            for child in self.frame.winfo_children():
                child.pack_forget()
            self.sub_canvas.pack()
            return
        if self.first_activate:
            # расставляем дефолтные элементы
            self.first_activate = False
            self.draw_default()
            return
        # открепляю все  элементы из фрейма вкладки
        for child in self.frame.winfo_children():
            child.pack_forget()
        # добавляю Canvas текущей вкладки на фрейм
        self.sub_canvas.pack()

    def create_selectors(self):
        #создаём элементы для выбора вида объектов
        
        self.selectors = {}
        x = 0
        y = 30
        for i, name in enumerate(self.names):
            if i % 2:
                x = self.rectangle_size*2
            else:
                x = 0
            self.selectors[name] = ObjectSelector(parent=self, canvas=self.sub_canvas, name=name, x=x, y=y, rect_size=self.rectangle_size)
            self.img_chooser[name] = ElementChooser(parent=self, rect_size=self.rectangle_size, name=name)
            if not self.img_chooser[name].images:
                self.selectors[name].active = False
            self.selectors[name].refresh()

            if i % 2:
                y += self.rectangle_size*1.5

class LayoutDownloader():
    # класс кнопки загрузки и прогрессбара
    def __init__(self, parent):
        self.name = parent.name
        self.canvas = parent.sub_canvas
        self.parent = parent

        if parent.conf_data:
            self.room_path = parent.conf_data["path"]
            self.create_bat = parent.conf_data["batfile"]
            self.check = parent.conf_data["check"]
        else:
            self.room_path = "" # путь к руму (сюда нужно будет записывать дефолтный путь)
            self.create_bat = False # нужно=ли генерировать bat-файл на рабочем столе юзера
            self.check = "" # файл/папка, наличие которой проверяется при указании пути
        #
        self.create_button()


    def create_button(self):
        # кнопка загрузки лейаута
        x1, y1, x2, y2 = self.canvas.bbox(self.parent.viewer.viewer)
        self.y_offset = self.parent.parent.download_button_image_tk.height()//2
        self.button = self.canvas.create_image(x2, y2+self.y_offset, image=self.parent.parent.download_button_image_tk, anchor=tk.NE)
        
        # кнопка выбора пути
        self.path_button = self.canvas.create_image(x1, y2+self.y_offset, image=self.parent.parent.path_layout_button_image_tk, anchor=tk.NW)

        # биндим
        self.canvas.tag_bind(self.button, "<Enter>", lambda event: self.canvas.itemconfig(self.button, image=self.parent.parent.download_button_focus_image_tk))
        self.canvas.tag_bind(self.button, "<Leave>",lambda event: self.canvas.itemconfig(self.button, image=self.parent.parent.download_button_image_tk))
        self.canvas.tag_bind(self.button, "<Button-1>", self.start_downloading_thread)

        self.canvas.tag_bind(self.path_button, "<Enter>", lambda event: self.canvas.itemconfig(self.path_button, image=self.parent.parent.path_layout_button_focus_image_tk))
        self.canvas.tag_bind(self.path_button, "<Leave>", lambda event: self.canvas.itemconfig(self.path_button, image=self.parent.parent.path_layout_button_image_tk))
        self.canvas.tag_bind(self.path_button, "<Button-1>", self.set_room_path)

    def set_room_path(self, event):
        # метод для указания пути к руму
        while True:
            if self.room_path and os.path.exists(self.room_path):
                room_path = filedialog.askdirectory(initialdir=self.room_path, title=f"Path to {self.name} room")
            else:
                room_path = filedialog.askdirectory(title=f"Path to {self.name} room")

            # если был выбран путь
            if room_path:
                if not os.path.exists(os.path.join(room_path, self.check)):
                    messagebox.showerror("Ошибка", f"Указан неверный путь к руму!\nОбычно каталог рума находится тут: {self.room_path}")
                else:
                    self.room_path = room_path
                    self.save_path()
                    return
            else:
                return

    def save_path(self):
        # сохраняет в json указанный юзером корректный путь к руму

        # считываем 
        with open(f"layouts/{self.name}/config.json", 'r') as f:
            conf_dict = json.load(f)

        conf_dict["path"] = self.room_path
        # Сохранение словаря в JSON
        with open(f"layouts/{self.name}/config.json", 'w') as f:
            json.dump(conf_dict, f)

    def start_downloading_thread(self, event):
        # запускаем в потоке процесс загрузки лейаута
        thread = threading.Thread(target=self.on_click, args=(None, ))
        thread.daemon = True
        thread.start()

    # Обработчик ЛКМ для загрузки лейаута
    def on_click(self, event):
        if not self.room_path or not os.path.exists(self.room_path):
            messagebox.showerror("Ошибка", f"Не найден путь к руму! Укажите путь к установленному руму вручную!\nОбычно каталог рума находится тут: {self.room_path}")
            return
        elif not os.path.exists(os.path.join(self.room_path, self.check)):
            messagebox.showerror("Ошибка", f"Указан неверный путь к руму! Укажите путь к папке с установленным румом!\nОбычно каталог рума находится тут: {self.room_path}")
            return

        # убираем бинды
        self.canvas.tag_unbind(self.button, "<Enter>")
        self.canvas.tag_unbind(self.button, "<Leave>")
        self.canvas.tag_unbind(self.button, "<Button-1>")
        self.canvas.tag_unbind(self.path_button, "<Enter>")
        self.canvas.tag_unbind(self.path_button, "<Leave>")
        self.canvas.tag_unbind(self.path_button, "<Button-1>")
        self.canvas.itemconfig(self.button, image=self.parent.parent.download_button_pressed_image_tk)       


        # тут в потоке нужно запустить загрузку обнов и отрисовку прогрессбара (set_persents)
        self.draw_progressbar()

        status = self.get_layout() # запрашиваем у сервера лейаут

        # этот код использовать после окончания загрузки
        self.canvas.tag_bind(self.button, "<Enter>", lambda event: self.canvas.itemconfig(self.button, image=self.parent.parent.download_button_focus_image_tk))
        self.canvas.tag_bind(self.button, "<Leave>",lambda event: self.canvas.itemconfig(self.button, image=self.parent.parent.download_button_image_tk))
        self.canvas.tag_bind(self.button, "<Button-1>", self.start_downloading_thread)

        self.canvas.tag_bind(self.path_button, "<Enter>", lambda event: self.canvas.itemconfig(self.path_button, image=self.parent.parent.path_layout_button_focus_image_tk))
        self.canvas.tag_bind(self.path_button, "<Leave>", lambda event: self.canvas.itemconfig(self.path_button, image=self.parent.parent.path_layout_button_image_tk))
        self.canvas.tag_bind(self.path_button, "<Button-1>", self.set_room_path)

        self.canvas.itemconfig(self.button, image=self.parent.parent.download_button_image_tk)
        self.canvas.delete("progressbar")



    def get_layout(self):
        # отправляет на сервер запрос на скачивание наконструированного лейаута
        data = {} 
        
        for elem in self.parent.viewer.elements:
            if self.parent.viewer.elements[elem]:
                # задаём в словарь наименование - имя файла (без расширения и пути)
                data[elem] = os.path.splitext(os.path.basename(self.parent.viewer.elements[elem]["path"]))[0]
        if data:
            data = str(data)
        else:
            return False
        
        try:
            status = asyncio.run(http_client.get_layout(URL=self.parent.parent.server_url, room=self.name, constructed=data, parent=self))
            if status == 200:
                # если лейаут нормально скачался
                # устанавливаем наш лейаут
                try:
                    self.install_layout()
                except Exception as error:
                    messagebox.showerror("Ошибка", f"Произошла ошибка при установке лейаута: {error}")
            else:
                print(status)
                messagebox.showerror("Ошибка", "Не удалось загрузить лейаут, так как сервер не ответил на запрос!\nПопробуйте повторить попытку!")
                return False
        except Exception as error:
            messagebox.showerror("Ошибка", f"Произошла ошибка: {error}\nПопробуйте повторить попытку!")
            return False

    def install_layout(self):
        # для распаковки скачанного лейаута
        zip_path = 'layout.zip'  # Путь к zip-файлу

        # создаём bat-файл для применения лейаута (если это необходимо)
        if self.create_bat:

            extract_path = f'layouts/{self.name}/downloaded'  # Путь к каталогу назначения
            # если папки нет - создаём её. Если есть - удаляем перед распаковкой из неё всё
            if not os.path.exists(extract_path):
                os.makedirs(extract_path)
            else:
                shutil.rmtree(extract_path)
                os.makedirs(extract_path)

            # распаковываем zip
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_path)

            # пытаемся получить дефолтный путь к Desktop
            desktop_path = get_desktop()

            # если путь пустой, или такого пути не существует - пытаюсь найти другим способом
            if not desktop_path or not os.path.exists(desktop_path):
                try:
                    desktop_path = Path.home() / 'Desktop'
                    desktop_path = str(desktop_path)
                except Exception as error:
                    print(f"Не удалось определить путь в Desktop: {error}")
                    desktop_path = None

            if not desktop_path or not os.path.exists(desktop_path):
                try:
                    desktop_path = os.path.join(os.environ['USERPROFILE'], 'Desktop')
                except Exception as error:
                    print(f"Не удалось определить путь в Desktop: {error}")
                    desktop_path = None
            
            if not desktop_path or not os.path.exists(desktop_path):
                try:
                    desktop_path = os.path.join(os.environ['USERPROFILE'], 'OneDrive', 'Desktop')
                except Exception as error:
                    print(f"Не удалось определить путь в Desktop: {error}")
                    desktop_path = None

            if not desktop_path or not os.path.exists(desktop_path):
                # Вывод диалогового окна с предупреждением
                response = messagebox.askokcancel(
                    "Внимание!",
                    "Программе не удалось обнаружить путь к рабочему столу! Укажите, пожалуйста, путь вручную"
                )

                # Обработка реакции пользователя
                if response:
                    desktop_path = filedialog.askdirectory(title="Укажите путь к рабочему столу")
                    if not desktop_path:
                        messagebox.showinfo("Успех!", "Лейаут загружен, но bat-файл не сгенерирован!")
                        return
                else:
                    messagebox.showinfo("Успех!", "Лейаут загружен, но bat-файл не сгенерирован!")
                    return

            source_path = os.path.normpath(os.path.join(os.getcwd(), extract_path))
            target_path = os.path.normpath(self.room_path)
            if sys.platform.startswith("win"):
                script_file_name = f"{self.name}_set_layout.bat"
                script_content = f'XCOPY "{source_path}" "{target_path}" /e /y'
            else:
                script_file_name = f"{self.name}_set_layout.command" if sys.platform == "darwin" else f"{self.name}_set_layout.sh"
                script_content = (
                    "#!/bin/sh\n"
                    f'mkdir -p "{target_path}"\n'
                    f'cp -R "{source_path}/." "{target_path}/"\n'
                )

            script_file_path = os.path.normpath(os.path.join(desktop_path, script_file_name))

            with open(script_file_path, 'w') as f:
                f.write(script_content)

            if not sys.platform.startswith("win"):
                os.chmod(script_file_path, 0o755)

            print(f"Создан файл установки лейаута: {script_file_path}")

            # запускаем созданный скрипт
            open_path(script_file_path)

            messagebox.showinfo("Успех!", f"Лейаут загружен! На рабочем столе создан файл {script_file_name} для установки лейаута!")
        else:
            # распаковываем zip в папку рума
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                print(f"Распаковываю zip  {self.room_path}")
                zip_ref.extractall(os.path.normpath(self.room_path))
            messagebox.showinfo("Успех!", "Лейаут загружен и установлен!")

    def draw_progressbar(self):
        self.progressbar = None
        # отрисовывает прогрессбар
        self.x1, y1, self.x2, y2 = self.canvas.bbox(self.parent.viewer.viewer)

        self.offset = self.canvas.bbox(self.button)[3]+5
        self.width = self.x2-self.x1
        # отрисовка задней серой части
        self.progressbar_background = polygons.round_rectangle(self.canvas, self.x1, self.offset+self.y_offset,\
            self.x2, self.offset+self.y_offset+10,\
            radius=7, outline="#353535", fill="#353535", width=1, tags="progressbar")

        # получаем координаты бекграунда
        x1, self.y1, x2, self.y2 = self.canvas.bbox(self.progressbar_background)
        
        # отрисовка текста
        self.progressbar_text = self.canvas.create_text(self.x1, self.offset+self.y_offset-3,\
            text="Loading files...", font=("Arial", 10), \
            anchor="sw", fill="#ffffff", tags="progressbar")
    
    async def set_persents(self, persent=0):
        # принимать должен от 0 до 101
        # для перерисовки процента загрузки прогрессбара
        if persent < 3:
            persent = 2
        width = self.width / 100 * persent+1
        progressbar = polygons.round_rectangle(self.canvas, self.x1, self.offset+self.y_offset,\
            self.x1+width, self.offset+self.y_offset+10,\
            radius=7, outline="#C71B74", fill="#C71B74", width=1, tags="progressbar")
        if self.progressbar != None:
            self.canvas.delete(self.progressbar)
        self.progressbar = progressbar


class ObjectSelector():
    '''
    класс для ячеек выбранного изображения
    '''
    def __init__(self, parent, canvas, name, x, y, rect_size):
        self.parent = parent
        self.canvas = canvas
        self.name = name
        self.x = x
        self.y = y
        self.size = rect_size
        self.active = True # можно-ли выбирать этот объект мышкой (если нет элементов для выбора - ставим False)
        self.image_id = None # сюда попадает id отрисованного на canvas элемента для последующего удаления
        self.draw()
        # self.refresh()

    def draw(self):
        # отрисовка текста
        self.text = self.canvas.create_text(self.x, self.y,\
            text=self.name, font=("Arial", 10), \
            anchor="w", fill="white")
        x1, y1, x2, y2 = self.canvas.bbox(self.text)

        # создаю ячейку для объекта
        self.box = polygons.round_rectangle(self.canvas, self.x, y2+(y2-y1)//2, self.x+self.size, y2+self.size+(y2-y1)//2,\
            radius=10, outline="#353535", fill="#1E1E1E", width=1, tags=self.name)
        x1, y1, x2, y2 = self.canvas.bbox(self.box)
        # создаю треугольник справа
        self.triangle = polygons.round_polygon(self.canvas, [x2+5, x2+13, x2+21], [y2-(y2-y1)//2-3, y2-(y2-y1)//2+6, y2-(y2-y1)//2-3],\
            sharpness=1 , width=1, outline="#353535", fill="#353535")

    def bind(self):
        if self.active:
            # Привязываем обработчики событий к элементу Canvas
            self.canvas.tag_bind(self.box, "<Enter>", self.on_enter)
            self.canvas.tag_bind(self.box, "<Leave>", self.on_leave)
            self.canvas.tag_bind(self.box, "<Button-1>", lambda event: self.parent.img_chooser[self.name].draw())

            if self.image_id:
                self.canvas.tag_bind(self.image_id, "<Enter>", self.on_enter)
                self.canvas.tag_bind(self.image_id, "<Leave>", self.on_leave)
                self.canvas.tag_bind(self.image_id, "<Button-1>", lambda event: self.parent.img_chooser[self.name].draw())

            self.canvas.tag_bind(self.triangle, "<Enter>", self.on_enter)
            self.canvas.tag_bind(self.triangle, "<Leave>", self.on_leave)
            self.canvas.tag_bind(self.triangle, "<Button-1>", lambda event: self.parent.img_chooser[self.name].draw())
        else:
            self.canvas.tag_unbind(self.box, "<Enter>")
            self.canvas.tag_unbind(self.box, "<Leave>")
            self.canvas.tag_unbind(self.box, "<Button-1>")

            if self.image_id:
                self.canvas.tag_unbind(self.image_id, "<Enter>")
                self.canvas.tag_unbind(self.image_id, "<Leave>")
                self.canvas.tag_unbind(self.image_id, "<Button-1>")

            self.canvas.tag_unbind(self.triangle, "<Enter>")
            self.canvas.tag_unbind(self.triangle, "<Leave>")
            self.canvas.tag_unbind(self.triangle, "<Button-1>")

    def refresh(self):
        # для обновления биндов и цветов
        self.bind() # выполняем бинд/анбинд в зависимости от состояния флага self.active
        if self.active:
            outline="#ffffff"
            fill="#ffffff"
        else:
            outline="#353535"
            fill="#353535"
        self.canvas.itemconfig(self.triangle, outline=outline, fill=fill)

    def change_image(self, image, fill=None):
        # отрисовывает выбранное в Cell изображение
        # Fill отвечает за то, нужно ли залить ячейку цветом, а не вывести в него картинку
        if not fill:
            x1, y1, x2, y2 = self.canvas.bbox(self.text)
            self.canvas.delete(self.image_id)
            self.image_id = self.canvas.create_image(self.x+self.size//2,\
                y2+(y2-y1)//2+self.size//2,\
                image=image)
        else:
            self.canvas.itemconfig(self.box, fill=fill)
        self.refresh()


    # Обработчик события "Enter"
    def on_enter(self, event):
        self.canvas.itemconfig(self.box, outline="#C71B74")
        # если это не ячейка фона, то меняем на ней бек
        if self.name != self.parent.names[0]:
            self.canvas.itemconfig(self.box, fill="#353535")

    # Обработчик события "Leave"
    def on_leave(self, event):
        self.canvas.itemconfig(self.box, outline="#353535")
        # если это не ячейка фона, то меняем на ней бек
        if self.name != self.parent.names[0]:
            self.canvas.itemconfig(self.box, fill="#1E1E1E")


class ViewerScreen():
    # класс для экрана предпросмотра собираемого стиля

    def __init__(self, parent, x, y, width, height, canvas):
        self.parent = parent
        self.x = x
        self.y = y
        self.canvas = canvas
        self.width = width
        self.height = height
        self.scale = 20 # чем больше это значение, тем меньше будет происходить уменьшение изображения если оно не вмещается в вьювер
        self.scale_coef = 0 # коэффициент для изменения разрешения
        self.elements = {} # словарь списков элементов для видов
        # заполняем словарь пустыми значениями
        for _ in self.parent.names:
            self.elements[_] = None
        self.create_viewer()

    def redraw(self):
        # метод для перерисовки экрана
        for i, obj in enumerate(self.elements):
            if self.elements[obj]:
                x_offset = 0 # смещение по x относительно центра вьювера
                y_offset = 0 # смещение по y относительно центра вьювера
                amount = 1 # количество выводимых картинок
                gap = 10 # зазор между выводимыми элементами (если amount > 1)
                stretch = False # нужно-ли растянуть на весь вьювер (для фона/текстуры)
                fill = False
                fill_color = None
                """
                Тут нужен алгоритм который отсекает прозрачность со стола, и задаёт координаты для вывода элементов.
                Пока что задал фиксированные координаты
                0 - цвет фона
                1 - текстура фона
                2 - стол
                3 - фишки
                4 - передник карты
                5 - рубашка карты
                """
                if i == 0:
                    fill = True
                else:
                    fill = False

                if i == 3:
                    x_offset = -90

                elif i == 4:
                    amount = 2
                    y_offset = self.parent.conf_data["cards_y_offset"][0]
                    
                elif i == 5:
                    amount = 2
                    y_offset = self.parent.conf_data["cards_y_offset"][1]

                for _ in range(amount):
                    if amount > 1 and i == 4 and _ == 1:
                        path, fname = os.path.split(self.elements[obj]["path"])
                        name, extension = os.path.splitext(fname)
                        searched_file = os.path.join(path, f"{name}_secondcard{extension}")
                        if os.path.exists(searched_file):
                            photo_image = tk.PhotoImage(file=searched_file)
                        else:
                            photo_image = tk.PhotoImage(file=self.elements[obj]["path"])
                    else:
                        # выполняем преобразование объектов
                        photo_image = tk.PhotoImage(file=self.elements[obj]["path"])
                    
                    width = photo_image.width()
                    height = photo_image.height()
                    # реобразуем в изображение Pillow
                    pil_image = ImageTk.getimage(photo_image)

                    if fill: # если это цвет фона, то заливаем
                        # получаем цвет первого пиксела
                        pixel_color = pil_image.getpixel((1, 1))
                        # преобразуем в HEX представление цвета
                        hex_color = '#{:02x}{:02x}{:02x}'.format(pixel_color[0], pixel_color[1], pixel_color[2])

                        # красим фон за столом
                        self.canvas.itemconfig(self.viewer, fill=hex_color)

                        continue

                    # проверяем разрешение
                    if width > self.width-self.width//self.scale or height > self.height-self.height//self.scale:
                        # Вычисляем новые размеры изображения, сохраняя соотношение сторон
                        if width > height:
                            new_width = self.width - self.width//self.scale
                            new_height = int(height * new_width / width)
                        else:
                            new_height = self.height - self.height//self.scale
                            new_width = int(width * new_height / height)
                        scale_coef = new_width / width # получаем коэффициент зума
                        if self.scale_coef < scale_coef:
                            self.scale_coef = scale_coef
                        if self.scale_coef:
                            # Масштабируем изображение до новых размеров
                            pil_image.thumbnail((int(width*self.scale_coef), int(height*self.scale_coef)))
                        else:    
                            pil_image.thumbnail((new_width, new_height))
                    if self.scale_coef:
                        pil_image.thumbnail((int(width*self.scale_coef), int(height*self.scale_coef)))

                    photo_image = ImageTk.PhotoImage(pil_image)
                    
                    if _ == 0 and amount > 1:
                        self.elements[obj]["viewer_img"] = photo_image
                        x_offset = -photo_image.width()//1.9
                    elif _ == 1 and amount > 1:
                        self.elements[obj]["viewer_img_second"] = photo_image
                        x_offset = photo_image.width()//1.9
                    else:
                        self.elements[obj]["viewer_img"] = photo_image
                    
                    if _ == 1 and amount > 1:
                        self.canvas.create_image(self.x+x_offset+self.width//2,\
                            self.y+y_offset+self.height//2,\
                            image=self.elements[obj]["viewer_img_second"], anchor=tk.CENTER)
                    else:
                        self.canvas.create_image(self.x+x_offset+self.width//2,\
                            self.y+y_offset+self.height//2,\
                            image=self.elements[obj]["viewer_img"], anchor=tk.CENTER)


    def create_viewer(self):
        self.viewer = polygons.round_rectangle(self.parent.sub_canvas, self.x, self.y, self.x+self.width, self.y+self.height,\
            radius=10, outline="#353535", fill="#1E1E1E", width=1, tags="viewer")


class ElementChooser():
    def __init__(self, parent, rect_size, name):
        self.parent = parent
        self.name = name
        self.rect_size = rect_size
        self.cells_count = 3 # это число в квадрате равно количеству ячеек
        if not self.parent.selectors[self.name].active:
            return
        self.cells = [] # сюда попадают ссылки на отрисованные ячейки для бинда и т.д.
        self.images = [] # сюда попадают пути к файлам изображений
        self.load_images()
 
    def load_images(self):
        # метод для загрузки изображений в список
        path = os.path.normpath(f"layouts/{self.parent.name}/{self.name}")
        if not os.path.exists(path):
            return

        for root, dirs, files in os.walk(path):
            for file in files:
                if file.lower().endswith(('.png', '.jpg')) and "_secondcard" not in file.lower():
                    self.images.append(os.path.join(root, file))

    def draw(self, on_canvas=True):
        # флаг on_canvas отвечает за то, нужно-ли отрисовывать на холсте сетку 3х3 (по дефолту отрисовывается)

        # если ячейка с таким именем недоступна для активации
        if not self.parent.selectors[self.name].active:
            return
        
        # удаляем предыдущий chooser с холста
        self.parent.sub_canvas.delete("chooser")

        x = self.parent.selectors[self.parent.names[-2]].x
        y = self.parent.selectors[self.parent.names[-2]].y + self.rect_size*1.5
        scale = 3.2
        indentation = (self.rect_size*scale-self.rect_size*self.cells_count)//4
        #
        if on_canvas:
            # рисуем фон для 3x3
            polygons.round_rectangle(self.parent.sub_canvas, x, y, x+self.rect_size*scale, y+self.rect_size*scale,\
                radius=10, outline="#0F0F0F", fill="#0F0F0F", width=1, tags="chooser")
        
        if not self.cells:
            # рисуем ячейки
            x+=indentation
            y+=indentation
            image_counter = 1 # счётчик изображений
            for i in range(self.cells_count):
                for n in range(self.cells_count):
                    if image_counter > len(self.images):
                        image = None
                    else:
                        image = self.images[image_counter-1]
                    self.cells.append(Cell(parent=self,\
                        canvas=self.parent.sub_canvas,\
                        scale=scale,\
                        indentation=indentation,\
                        x=x, y=y,\
                        i=i, n=n,\
                        rect_size=self.rect_size, image=image))
                    image_counter += 1
        if on_canvas:
            # отрисовываем ячейку
            for cell in self.cells:
                cell.create()

class Cell():
    # класс ячеек для выбора понравившегося сета
    def __init__(self, parent, canvas, scale, indentation, x, y, i, n, rect_size, image=None):
        self.parent = parent
        self.canvas = canvas
        self.scale = scale
        self.indentation = indentation
        self.x = x
        self.y = y
        self. i = i
        self.n = n
        self.rect_size = rect_size
        self.fill_color = None
        self.image = image # путь к картинке
        self.image_tk = None # картинка без изменения разрешения
        self.scale_image_tk = None # изображение подогнанное по разрешению под ячейку, если оно превышало её размеры
        if self.image:
            photo_image = tk.PhotoImage(file=self.image)
            image = ImageTk.getimage(photo_image)
            if self.parent.name == self.parent.parent.names[0]: # если это цвет стола
                # получаем цвет первого пиксела
                pixel_color = image.getpixel((1, 1))
                # преобразуем в HEX представление цвета
                self.fill_color = '#{:02x}{:02x}{:02x}'.format(pixel_color[0], pixel_color[1], pixel_color[2])


            width, height = image.size
            # если изображение больше ячейки
            if width > self.rect_size - self.rect_size//20 or height > self.rect_size - self.rect_size//20:
                # Вычисляем новые размеры изображения, сохраняя соотношение сторон
                if width > height:
                    new_width = self.rect_size - self.rect_size//20
                    new_height = int(height * self.rect_size - self.rect_size//20 / width)
                else:
                    new_height = self.rect_size - self.rect_size//20
                    new_width = int(width * self.rect_size - self.rect_size//20 / height)
                # Масштабируем изображение до новых размеров
                self.scale_image_tk = image.thumbnail((new_width, new_height))
            self.image_tk = ImageTk.PhotoImage(image)
            if not self.scale_image_tk:
                self.scale_image_tk = self.image_tk

    def create(self):
        self.cell = polygons.round_rectangle(self.canvas, self.x+(self.n*self.rect_size)+self.indentation*self.n,\
            self.y+(self.i*self.rect_size)+self.indentation*self.i,\
            self.x+(self.n*self.rect_size)+self.rect_size+self.indentation*self.n,\
            self.y+(self.i*self.rect_size)+self.rect_size+self.indentation*self.i,\
            radius=10, outline="#353535", fill="#0F0F0F", width=1, tags="chooser")
        if self.scale_image_tk:
            if not self.fill_color:
                self.element = self.canvas.create_image(self.x+(self.n*self.rect_size)+self.indentation*self.n+self.rect_size//2,\
                    self.y+(self.i*self.rect_size)+self.indentation*self.i+self.rect_size//2,\
                    image=self.scale_image_tk, tags="chooser")
                self.canvas.tag_bind(self.element, "<Enter>", lambda event: self.canvas.itemconfig(self.cell, outline="#C71B74"))
                self.canvas.tag_bind(self.element, "<Leave>", lambda event: self.canvas.itemconfig(self.cell, outline="#353535"))
                self.canvas.tag_bind(self.element, "<Button-1>", lambda event: self.selected())
            else:
                self.canvas.itemconfig(self.cell, fill=self.fill_color)

        self.canvas.tag_bind(self.cell, "<Enter>", lambda event: self.canvas.itemconfig(self.cell, outline="#C71B74"))
        self.canvas.tag_bind(self.cell, "<Leave>", lambda event: self.canvas.itemconfig(self.cell, outline="#353535"))
        self.canvas.tag_bind(self.cell, "<Button-1>", lambda event: self.selected())

    def selected(self):
        # при выборе ячейки вызывается этот метод
        if not self.scale_image_tk:
            return
        object_name = self.parent.name
        if not self.fill_color:
            # если нужно вывести картинку, а не залить цветом
            self.parent.parent.selectors[object_name].change_image(image=self.scale_image_tk)
        else:
            # если-же нужно залить цветом
            self.parent.parent.selectors[object_name].change_image(image=self.scale_image_tk, fill=self.fill_color)

        self.parent.parent.viewer.elements[object_name] = {"image": self.image_tk , "path": self.image}
        self.parent.parent.viewer.redraw()


"""

"""
