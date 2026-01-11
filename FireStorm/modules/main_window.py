import tkinter as tk
from PIL import ImageTk, Image
from tkinter import filedialog, messagebox
import time
import json
import os
import asyncio
#
import modules.views as views
import modules.http_client as http_client
import modules.polygons as polygons 

class MainWindow():
    def __init__(self, frame, parent, height, width):
        self.parent = parent
        self.username = parent.username
        self.frame = frame
        self.server_url = parent.server_url
        self.active = False # флаг, который указывает, находится ли фрейм в главном окне или нет
        # список вкладок
        # открываем дефолтный файл, если он есть
        default_services = "settings/default_services.json"
        default_data = None
        data = {"services": {}}
        if os.path.exists(default_services):
            with open(default_services, "r") as file:
                default_data = json.load(file)
        # Создадим множество для отслеживания уникальных путей
        unique_paths = set()
        # открываем главный файл (если он есть и он в норме)
        main_services = "settings/services.json"
        if os.path.exists(main_services):
            # Открываем файл основных настроек румов
            try:
                with open(main_services, "r") as file:
                    data = json.load(file)

                # Перебираем каждый список folders и удаляем дубликаты
                for service_key, service_value in data["services"].items():
                    new_folders = []
                    for folder in service_value["folders"]:
                        if folder not in unique_paths:
                            unique_paths.add(folder) 
                            new_folders.append(folder) 
                    service_value["folders"] = new_folders 

                # перезаписываем файл
                with open(main_services, "w") as file:
                    json.dump(data, file)

            except Exception as error:
                data = {"services": {}}
                text = f"Не удалось считать главный файл настройки путей к румам: {error}"
                asyncio.run(http_client.send_log(URL=self.server_url, username=self.username, error=text))

                print("Не удалось считать главный файл настройки путей к румам")

        # если есть дефолтные данные румов - делаем объединение словарей
        if default_data:
            default_data["services"].update(data["services"])
            data = default_data
            # Записываем обновленные данные обратно в файл
            with open(main_services, 'w') as file:
                json.dump(data, file)

        # загружаем имена и настройки окон для вкладок
        self.services = data["services"]
        # словарь, в котором будут храниться объекты фреймов для румов (Room)
        self.tab = {}
        
        self.width = width
        self.height = height

        self.panel_tags = []
        self.canvas = tk.Canvas(self.frame, width=self.width, height=self.height, bg="#1E1E1E")
        # Привязываем обработчик события прокрутки колесика мыши к холсту
        self.canvas.bind_all("<MouseWheel>", self.on_mousewheel)
        self.view_tab = views.Views(parent=self, height=self.height, width=self.width)
        self.load_images()
        self.create_elements()

        default_active = None # флаг для активации первой трекинговой вкладки
        # добавляем в список вкладок румы
        for num, srv in enumerate(self.services):
            self.tab[srv] = Room(name=srv, frame=self.tab_frame, parent=self)
            self.tab[srv].dirs_listbox.items = data["services"][srv]["folders"]
            self.tab[srv].dirs_listbox.update_listbox()
            tracking = self.tab[srv].tracking = data["services"][srv]["track"]
            self.tab[srv].check_switcher()
            self.add_tab_to_panel(name=srv)

            # делаем активным первый рум
            if num == 0:
                self.goto_tab(tag_name=srv, event=None)

            # делаем активным рум у которого включен трекинг
            if not default_active and tracking:
                default_active = srv
                self.goto_tab(tag_name=default_active, event=None)
        # отображаю canvas
        self.canvas.pack()

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

            self.canvas.tag_bind(triangle_up, "<Enter>", lambda event: self.on_enter(event=event, tag=triangle_up))
            self.canvas.tag_bind(triangle_up, "<Leave>", lambda event: self.on_leave(event=event, tag=triangle_up))
            self.canvas.tag_bind(triangle_up, "<Button-1>", lambda event: self.on_mousewheel(event=None, delta=120))

            self.canvas.tag_bind(triangle_down, "<Enter>", lambda event: self.on_enter(event=event, tag=triangle_down))
            self.canvas.tag_bind(triangle_down, "<Leave>", lambda event: self.on_leave(event=event, tag=triangle_down))
            self.canvas.tag_bind(triangle_down, "<Button-1>", lambda event: self.on_mousewheel(event=None, delta=-120))


    # Обработчик события "Enter"
    def on_enter(self, event, tag):
        self.canvas.itemconfig(tag, fill="#ffffff", outline="#ffffff")

    # Обработчик события "Leave"
    def on_leave(self, event, tag):
        self.canvas.itemconfig(tag, fill="#353535", outline="#353535")

    def load_images(self):
        logo_image = Image.open("img/logo.png")
        self.logo_image_tk = ImageTk.PhotoImage(logo_image)
        #
        remove_folder_focus_image = Image.open("img/remove_folder_focus.png")
        self.remove_folder_focus_image_tk = ImageTk.PhotoImage(remove_folder_focus_image)
        #
        remove_folder_image = Image.open("img/remove_folder.png")
        self.remove_folder_image_tk = ImageTk.PhotoImage(remove_folder_image)
        #
        add_folder_focus_image = Image.open("img/add_folder_focus.png")
        self.add_folder_focus_image_tk = ImageTk.PhotoImage(add_folder_focus_image)
        #
        add_folder_image = Image.open("img/add_folder.png")
        self.add_folder_image_tk = ImageTk.PhotoImage(add_folder_image)
        #
        switch_on_image = Image.open("img/switch_on.png")
        self.switch_on_image_tk = ImageTk.PhotoImage(switch_on_image)
        #
        switch_off_image = Image.open("img/switch_off.png")
        self.switch_off_image_tk = ImageTk.PhotoImage(switch_off_image)
        #
        open_folder_image = Image.open("img/open_folder.png")
        self.open_folder_image_tk = ImageTk.PhotoImage(open_folder_image)
        #
        open_folder_focus_image = Image.open("img/open_folder_focus.png")
        self.open_folder_focus_image_tk = ImageTk.PhotoImage(open_folder_focus_image)
        #
        checkbox_on_image = Image.open("img/checkbox_on.png")
        self.checkbox_on_image_tk = ImageTk.PhotoImage(checkbox_on_image)

    def create_elements(self):
        # создаём элементы в окне
        self.canvas.create_image(0, 0, image=self.logo_image_tk, anchor=tk.NW)

        # создаю фрейм, в который будет помещён Canvas с содежимым вкладки
        self.tab_frame = tk.Frame(self.canvas, bg="#1E1E1E", highlightthickness=0)
        self.canvas.create_window(self.logo_image_tk.width()*1.2, self.height//8+(self.logo_image_tk.height()//8), window=self.tab_frame, anchor=tk.NW)

    def read_upload_status(self):
        base_dir = os.getenv("FIRESTORM_BASE", os.getcwd())
        status_path = os.path.join(base_dir, "settings", "upload_status.json")
        if not os.path.exists(status_path):
            return None
        try:
            with open(status_path, "r", encoding="utf-8") as file:
                return json.load(file)
        except Exception:
            return None

    def add_tab_to_panel(self, name):
        # метод для добавления кнопки перехода к настройкам рума на панель слева
        text_id = self.canvas.create_text(self.logo_image_tk.width()//2,\
            self.height//8+(self.logo_image_tk.height()//2*len(self.tab)),\
            text=name, font=("Arial", 14), \
            anchor=tk.CENTER, fill="white", tags=name)
        self.canvas.tag_bind(name, "<Enter>", lambda event: self.change_text_color(tag_name=name, event=event))
        self.canvas.tag_bind(name, "<Leave>", lambda event: self.restore_text_color(tag_name=name, event=event))
        # бинд перехода ко вкладке при нажатии ЛКМ
        self.canvas.tag_bind(name, "<Button-1>", lambda event: self.goto_tab(tag_name=name, event=event))
        # проверяем, включен-ли трекинг
        if self.tab[name].tracking == True:
            checkbox_id = self.canvas.create_image(self.checkbox_on_image_tk.width(), self.height//8+(self.logo_image_tk.height()//2*len(self.tab)), image=self.checkbox_on_image_tk, anchor=tk.CENTER, tags=f"{name}_checkbox")
            self.canvas.lower(checkbox_id)
            self.panel_tags.append(checkbox_id)

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
            if self.canvas.bbox(self.canvas.find_withtag(list(self.services.keys())[-1]))[3] <= self.height:
                return
        elif delta > 0:
            delta = 120
            if self.canvas.bbox(self.canvas.find_withtag(list(self.services.keys())[0]))[1] >= self.logo_image_tk.height():
                return
        # Сдвигаем каждый элемент вверх или вниз на значение delta
        for element in self.panel_tags:
            self.canvas.move(element, 0, delta)

    def change_text_color(self, tag_name, event):
        self.canvas.itemconfig(tag_name, fill="#C71B74")

    def restore_text_color(self, tag_name, event):
        self.canvas.itemconfig(tag_name, fill="white")

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

    def logout(self):
        # для выхода из аккаунта
        self.parent.main_frame.pack_forget()
        # затираем сохраненный ранее логин и пароль
        self.parent.save_user_data(username="", password="")
        self.parent.log_in_frame.pack()

    def pack(self):
        self.active = True
        self.frame.pack(fill="both")

    def pack_forget(self):
        self.active = False
        self.frame.pack_forget()

class Room:
    '''
    класс для создания румов
    '''
    def __init__(self, name, frame, parent):
        self.name = name
        self.frame = frame
        self.parent = parent
        self.tracking = True # флаг для отслеживания каталогов
        self.sub_canvas = tk.Canvas(frame, width=self.parent.width-self.parent.logo_image_tk.width()-75, height=self.parent.height-self.parent.logo_image_tk.height()-75, bg="#1E1E1E", borderwidth=0, relief="flat", highlightthickness=0)
        self.status_id = None
        self.status_text_id = None
        self.status_tooltip = None
        self.create_elements()

    def create_elements(self):
        # метод для компоновки элементов на sub_canvas
        # текст "Hand History Folder"
        self.sub_canvas.create_text(0, 0, text="Hand History Folder", font=("Arial", 14), anchor=tk.NW, fill="white")
        #
        self.sub_canvas.create_image(0, self.parent.add_folder_image_tk.height()//1.2, image=self.parent.add_folder_image_tk, anchor=tk.NW, tags="add_folder_btn")
        self.sub_canvas.create_image(self.parent.remove_folder_image_tk.width()*1.25, self.parent.remove_folder_image_tk.height()//1.2, image=self.parent.remove_folder_image_tk, anchor=tk.NW, tags="remove_folder_btn")
        self.sub_canvas.create_image(self.parent.open_folder_image_tk.width()*2.5, self.parent.open_folder_image_tk.height()//1.2, image=self.parent.open_folder_image_tk, anchor=tk.NW, tags="open_folder_btn")
        # биндим действия
        self.sub_canvas.tag_bind("add_folder_btn", "<Enter>", lambda event: self.on_enter(tag_name="add_folder_btn", new_img=self.parent.add_folder_focus_image_tk))
        self.sub_canvas.tag_bind("add_folder_btn", "<Leave>", lambda event: self.on_leave(tag_name="add_folder_btn", new_img=self.parent.add_folder_image_tk))
        #
        self.sub_canvas.tag_bind("remove_folder_btn", "<Enter>", lambda event: self.on_enter(tag_name="remove_folder_btn", new_img=self.parent.remove_folder_focus_image_tk))
        self.sub_canvas.tag_bind("remove_folder_btn", "<Leave>", lambda event: self.on_leave(tag_name="remove_folder_btn", new_img=self.parent.remove_folder_image_tk))
        #
        self.sub_canvas.tag_bind("open_folder_btn", "<Enter>", lambda event: self.on_enter(tag_name="open_folder_btn", new_img=self.parent.open_folder_focus_image_tk))
        self.sub_canvas.tag_bind("open_folder_btn", "<Leave>", lambda event: self.on_leave(tag_name="open_folder_btn", new_img=self.parent.open_folder_image_tk))
        # ListBox для путей к папкам
        self.dirs_listbox = CustomListBox(parent=self)
        # биндим удаление элемента
        self.sub_canvas.tag_bind("remove_folder_btn", "<Button-1>", lambda event: self.dirs_listbox.remove_item())
        # биндим выбор каталога
        self.sub_canvas.tag_bind("add_folder_btn", "<Button-1>", lambda event: self.choose_folder())
        # биндим открытие каталога в проводнике
        self.sub_canvas.tag_bind("open_folder_btn", "<Button-1>", lambda event: self.dirs_listbox.open_folder())
        # переключатель трекинга
        self.sub_canvas.create_text(0, self.parent.height//2, text="Track", font=("Arial", 12), anchor=tk.W, fill="white", tags="text_track")
        x1, y1, x2, y2 = self.sub_canvas.bbox("text_track")
        self.sub_canvas.create_image(x2+self.parent.switch_on_image_tk.width()//2, self.parent.height//2, image=self.parent.switch_on_image_tk, anchor=tk.W, tags="track_switcher")
        self.sub_canvas.tag_bind("track_switcher", "<Button-1>", lambda event: self.switch_tracking())

        # статус отправки файлов (индикатор + тултип)
        sx1, sy1, sx2, sy2 = self.sub_canvas.bbox("track_switcher")
        status_x = sx2 + 18
        status_y = (sy1 + sy2) // 2
        self.status_id = self.sub_canvas.create_oval(
            status_x - 6, status_y - 6, status_x + 6, status_y + 6,
            fill="#6c757d", outline=""
        )
        self.status_text_id = self.sub_canvas.create_text(
            status_x + 10, status_y, text="Статус", font=("Arial", 10),
            anchor=tk.W, fill="#bdbdbd"
        )
        self.sub_canvas.tag_bind(self.status_id, "<Enter>", self._status_enter)
        self.sub_canvas.tag_bind(self.status_id, "<Leave>", self._status_leave)
        self.sub_canvas.tag_bind(self.status_text_id, "<Enter>", self._status_enter)
        self.sub_canvas.tag_bind(self.status_text_id, "<Leave>", self._status_leave)
        self.refresh_status()


    def check_switcher(self):
        # обновляем положение переключателя
        if self.tracking == True:
            self.sub_canvas.itemconfig("track_switcher", image=self.parent.switch_on_image_tk)
            return True
        else:
            self.sub_canvas.itemconfig("track_switcher", image=self.parent.switch_off_image_tk)
            return False

    def switch_tracking(self):
        # метод для переключателя трекинга
        if self.tracking == True:
            self.tracking = False
            self.sub_canvas.itemconfig("track_switcher", image=self.parent.switch_off_image_tk)
            self.parent.canvas.delete(f"{self.name}_checkbox")
        else:
            self.tracking = True
            self.sub_canvas.itemconfig("track_switcher", image=self.parent.switch_on_image_tk)
            x1, y1, x2, y2 = self.parent.canvas.bbox("rectangle")
            offset = (y2-y1)//2
            checkbox_id = self.parent.canvas.create_image(self.parent.checkbox_on_image_tk.width(), y1+offset , image=self.parent.checkbox_on_image_tk, anchor=tk.CENTER, tags=f"{self.name}_checkbox")
            self.parent.canvas.lower(checkbox_id)
            self.parent.canvas.lower("rectangle")
            self.parent.panel_tags.append(checkbox_id)
        # вносим в json-файл изменения путей, если они были
        # Открываем JSON-файл и загружаем его содержимое
        with open('settings/services.json', 'r') as file:
            data = json.load(file)

        # Изменяем значение в поле
        data["services"][self.name]["track"] = self.tracking

        # Записываем обновленные данные обратно в файл
        with open('settings/services.json', 'w') as file:
            json.dump(data, file)
        self.refresh_status()


    def choose_folder(self):
        # метод принимает переменную, в которую попадёт путь, и label для вывода в него текстового пути
        temp_path = filedialog.askdirectory()
        if temp_path == "":
            return
        # Приводим к нормальному виду
        temp_path = os.path.normpath(temp_path)
        for key, obj in self.parent.tab.items():
            if temp_path in [os.path.normpath(f) for f in obj.dirs_listbox.items]:
                messagebox.showerror(title="Внимание!", message=f"Данная папка уже выбрана в руме: {key}!\nНельзя указывать одну и ту же папку в разных румах!")
                return

        self.dirs_listbox.add_item(f"{temp_path}")

    def active(self):
        # метод для активации вкладки (вызывается при нажатии ЛКМ)
        self.sub_canvas.pack()
        # открепляю все  элементы из фрейма вкладки
        for child in self.frame.winfo_children():
            # не открепляю только текущий сабканвас
            if child != self.sub_canvas:
                child.pack_forget()
        
        # self.sub_canvas.pack()

    def _status_enter(self, event):
        info = self._get_status_info()
        if not info:
            return
        self._status_leave(event)
        tooltip = tk.Toplevel(self.sub_canvas)
        tooltip.wm_overrideredirect(True)
        tooltip.geometry(f"+{event.x_root + 10}+{event.y_root + 10}")
        label = tk.Label(
            tooltip,
            text=info,
            background="#1E1E1E",
            foreground="white",
            justify="left",
            borderwidth=1,
            relief="solid",
            font=("Arial", 10),
        )
        label.pack()
        self.status_tooltip = tooltip

    def _status_leave(self, event):
        if self.status_tooltip:
            self.status_tooltip.destroy()
            self.status_tooltip = None

    def _get_status_info(self):
        if not self.tracking:
            return "Трекинг выключен"
        status = self.parent.read_upload_status()
        if not status:
            return "Нет данных об отправке"
        msg = status.get("message", "Нет данных")
        ts = status.get("ts", "")
        room = status.get("room")
        parts = [msg]
        if room:
            parts.append(f"Рум: {room}")
        if ts:
            parts.append(f"Время: {ts}")
        return "\n".join(parts)

    def refresh_status(self):
        if not self.status_id:
            return
        if not self.tracking:
            color = "#6c757d"
        else:
            status = self.parent.read_upload_status() or {}
            state = status.get("state")
            if state == "ok":
                color = "#2ecc71"
            elif state == "sending":
                color = "#3498db"
            elif state == "update":
                color = "#C71B74"
            elif state == "error":
                color = "#e74c3c"
            else:
                color = "#f1c40f"
        self.sub_canvas.itemconfig(self.status_id, fill=color)
        # обновляем каждые 3 секунды
        self.sub_canvas.after(3000, self.refresh_status)


    def on_enter(self, tag_name, new_img):
        self.sub_canvas.itemconfig(tag_name, image=new_img)

    def on_leave(self, tag_name, new_img):
        self.sub_canvas.itemconfig(tag_name, image=new_img)




class CustomListBox:
    def __init__(self, parent):
        self.parent = parent
        self.frame = tk.Frame(parent.sub_canvas, borderwidth=0, relief="flat", highlightthickness=0, bg="#1E1E1E")
        self.canvas = parent.sub_canvas
        self.canvas.create_window(0, 100, window=self.frame, anchor=tk.NW)
        self.items = []
        self.selected_item = None

    def add_item(self, text):
        # добавляем путь в список
        # защита от переполнения
        if len(self.items) >=5:
            return
        self.items.append(text)
        self.update_listbox()

    def remove_item(self):
        index = self.selected_item
        if index == None:
            return
        if index >= 0 and index < len(self.items):
            del self.items[index]
            self.update_listbox()

    def update_listbox(self):
        for widget in self.frame.winfo_children():
            widget.destroy()

        for i, item in enumerate(self.items):
            bg_color = "#1E1E1E"
            fg_color = "white"
            if i == self.selected_item:
                bg_color = "#353535"
                fg_color = "white"

            label = tk.Label(self.frame, text=item, bg=bg_color, fg=fg_color, width=80, font=("Arial", 13), anchor="w")
            label.pack()

            label.bind("<Button-1>", lambda event, index=i: self.select_item(index))

        # вносим в json-файл изменения путей, если они были
        # Открываем JSON-файл и загружаем его содержимое
        with open('settings/services.json', 'r') as file:
            data = json.load(file)

        # Изменяем значение в поле
        data["services"][self.parent.name]["folders"] = self.items
        try:
            # Записываем обновленные данные обратно в файл
            with open('settings/services.json', 'w') as file:
                json.dump(data, file)
        except Exception as e:
            try:
                text = f"Ошибка в main_window при записи в файл: {e}"
                asyncio.run(http_client.send_log(URL=self.server_url, username=self.username, error=str(e)))
            except:
                print("main_window не удалось отправить лог")

    def open_folder(self):
        # открываем каталог в проводнике
        index = self.selected_item
        if index == None:
            return
        if index >= 0 and index < len(self.items):
            os.startfile(self.items[index])


    def select_item(self, index):
        self.selected_item = index
        self.update_listbox()
