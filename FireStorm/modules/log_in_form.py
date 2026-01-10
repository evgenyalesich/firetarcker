# модуль окна авторизации

import tkinter as tk
from PIL import ImageTk, Image
import json
import time
import threading

class LogInForm():
    def __init__(self, frame, login_func, height, width):
        self.frame = frame
        # функция вызовется при нажатии кнопки авторизации
        self.login_func = login_func
        self.active = False # флаг, который указывает, находится ли фрейм в главном окне или нет
        self.width = width
        self.height = height
        self.canvas = tk.Canvas(self.frame, width=self.width, height=self.height, bg="#1E1E1E")
        self.canvas.pack()


        # считываем данные
        with open("settings/user_data.json", "r") as file:
            data = json.load(file)
        if "username" not in data:
            self.username = ""
        else:
            self.username=data["username"]
        if "password" not in data:
            self.password = ""
        else:
            self.password=data["password"]

        self.load_images()
        self.create_elements()

    def load_images(self):
        logo_image = Image.open("img/logo.png")
        self.logo_image_tk = ImageTk.PhotoImage(logo_image)
        #
        log_in_btn_img = Image.open("img/log_in_button.png")
        self.log_in_btn_tk = ImageTk.PhotoImage(log_in_btn_img)
        log_in_btn_focus_img = Image.open("img/log_in_button_focus.png")
        self.log_in_btn_focus_tk = ImageTk.PhotoImage(log_in_btn_focus_img)
        #
        connecting_img = Image.open("img/connecting.png")
        self.connecting_img_tk = ImageTk.PhotoImage(connecting_img)

    def create_elements(self):
        self.canvas.create_image(0, 0, image=self.logo_image_tk, anchor=tk.NW)
        self.canvas.create_text(self.width//2, self.height//4, text="Sign In", font=("Arial", 48), anchor=tk.CENTER, fill="white")
        
        # для ввода логина
        self.canvas.create_text(self.width//2.5, self.height//2.5, text="Username", font=("Arial", 12), anchor=tk.E, fill="white")
        self.login_frame = tk.Frame(self.canvas, bg="#C71B74")
        self.login_entry = tk.Entry(self.login_frame, width=14, relief="flat", justify='center', font=("Arial", 14), bg="#1E1E1E", fg="white")
        self.login_entry.insert(0, self.username)
        self.login_entry.pack(padx=2, pady=2)
        self.canvas.create_window(self.width//2, self.height//2.5, window=self.login_frame, anchor=tk.CENTER)

        # для ввода пароля
        self.canvas.create_text(self.width//2.5, self.height//2, text="Password", font=("Arial", 12), anchor=tk.E, fill="white")
        self.password_frame = tk.Frame(self.canvas, bg="#C71B74")
        self.password_entry = tk.Entry(self.password_frame, width=14, relief="flat", justify='center', font=("Arial", 14), bg="#1E1E1E", fg="white")
        self.password_entry.insert(0, self.password)
        self.password_entry.pack(padx=2, pady=2)
        self.canvas.create_window(self.width//2, self.height//2, window=self.password_frame, anchor=tk.CENTER)

        # кнопка для входа
        self.canvas.create_image(self.width//2, self.height//1.5, image=self.log_in_btn_tk, anchor=tk.CENTER, tags="log_in_button")
        # Привязка функций к событиям
        self.canvas.tag_bind("log_in_button", "<Enter>", self.on_enter)
        self.canvas.tag_bind("log_in_button", "<Leave>", self.on_leave)
        self.canvas.tag_bind("log_in_button", "<Button-1>", self.on_click)
        # бинд кнопки enter на вход в аккаунт
        self.login_entry.bind("<Return>", self.on_click)
        self.password_entry.bind("<Return>", self.on_click)

    def on_enter(self, event):
        self.canvas.itemconfig("log_in_button", image=self.log_in_btn_focus_tk)

    def on_leave(self, event):
        self.canvas.itemconfig("log_in_button", image=self.log_in_btn_tk)

    def on_click(self, event):
        self.canvas.tag_unbind("log_in_button", "<Enter>")
        self.canvas.tag_unbind("log_in_button", "<Leave>")
        self.canvas.tag_unbind("log_in_button", "<Button-1>")

        self.canvas.itemconfig("log_in_button", image=self.connecting_img_tk)
        thread = threading.Thread(target=self.login_func)
        thread.daemon = True
        thread.start()
        

        # self.canvas.itemconfig("log_in_button", image=self.log_in_btn_tk)

    def invalid_data_window(self):
        # выводит сообщение что логин или пароль неправильные
        self.canvas.delete("error_msg")
        self.canvas.create_text(self.width//2, self.height//1.7, text="invalid login or password", font=("Arial", 12), anchor=tk.CENTER, fill="white", tags="error_msg")
        
        self.canvas.tag_bind("log_in_button", "<Enter>", self.on_enter)
        self.canvas.tag_bind("log_in_button", "<Leave>", self.on_leave)
        self.canvas.tag_bind("log_in_button", "<Button-1>", self.on_click)
        self.canvas.itemconfig("log_in_button", image=self.log_in_btn_tk)
        time.sleep(3)
        self.canvas.delete("error_msg")

    def connection_error_window(self):
        # выводит сообщение что соединение с сервером не установлено
        self.canvas.delete("error_msg")
        self.canvas.create_text(self.width//2, self.height//1.7, text="server connection error", font=("Arial", 12), anchor=tk.CENTER, fill="white", tags="error_msg")
                
        self.canvas.tag_bind("log_in_button", "<Enter>", self.on_enter)
        self.canvas.tag_bind("log_in_button", "<Leave>", self.on_leave)
        self.canvas.tag_bind("log_in_button", "<Button-1>", self.on_click)
        self.canvas.itemconfig("log_in_button", image=self.log_in_btn_tk)
        time.sleep(3)
        self.canvas.delete("error_msg")

    def pack(self):
        self.active = True
        self.frame.pack(fill="both")

    def pack_forget(self):
        self.active = False
        self.frame.pack_forget()