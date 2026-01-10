import os
import sys
import tkinter as tk
from tkinter import messagebox

class ProgressBarWindow:
    # класс прогрессбара загрузки обновления
    def __init__(self, size):
        self.size = size
        self.root = tk.Toplevel()
        self.root.geometry(f"{size}x{size}")
        self.root.resizable(False, False)
        self.root.title("Update Downloader")
        base_dir = os.getenv("FIRESTORM_BASE", os.getcwd())
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
        self.canvas = tk.Canvas(self.root, width=size, height=size, bg="#1E1E1E")
        self.canvas.pack()
        self.attempt = 1 # кол-во попыток восстановления соединения
        default_text = "Начинаю загрузку обновления...\nПожалуйста, подождите"
        self.default_text = self.canvas.create_text(self.size // 2, self.size // 2, text=default_text, font=("Arial", 20, "bold"), fill="white", width=self.size)
        self.arc = None
        self.persent_text = None
        self.downloaded = None
        
    def draw_progress_bar(self, progress, total_files=None, current=None):
        self.attempt = 1 # Обнуляем кол-во попыток соединения
        # тут будем выводить скачанный объем / общий размер (в мегабайтах)
        x0 = y0 = self.size // 10
        x1 = y1 = self.size * 9 // 10

        # очищаем дефолтный текст
        if self.default_text != None:
            self.canvas.delete(self.default_text)
            self.default_text = None

        arc = self.canvas.create_arc(x0, y0, x1, y1, start=90, extent=-359*(progress/100), style="arc", width=20, outline="#C71B74")

        if self.arc != None:
            self.canvas.delete(self.arc)
        self.arc = arc

        if self.persent_text != None:
            self.canvas.itemconfig(self.persent_text, text=f"{progress}%")
        else:
            self.persent_text = self.canvas.create_text(self.size // 2, self.size // 2-10, text=f"{progress}%", font=("Arial", 20, "bold"), fill="white")

        if  total_files != None and current != None:
            if  self.downloaded != None:
                self.canvas.itemconfig(self.downloaded, text=f"{current//1024} из {total_files//1024}Кб")
            else:
                self.downloaded = self.canvas.create_text(self.size // 2, self.size // 2+10, text=f"{current//1024} из {total_files//1024}Кб", font=("Arial", 10, "bold"), fill="white")


    def connection_error(self):
        if self.arc != None:
            self.canvas.delete(self.arc)
            self.arc = None
        if self.default_text != None:
            self.canvas.delete(self.default_text)
            self.default_text = None
        if self.persent_text != None:
            self.canvas.delete(self.persent_text)
            self.persent_text = None
        if self.downloaded != None:
            self.canvas.delete(self.downloaded)
            self.downloaded = None

        text = f"Ошибка соединения с сервером!\nВыполняется {self.attempt} попытка восстановления соединения..."
        self.default_text = self.canvas.create_text(self.size // 2, self.size // 2, text=text, font=("Arial", 12, "bold"), fill="white", width=self.size)
        # увеличиваем счётчик
        self.attempt += 1

        if self.attempt > 15:
            messagebox.showerror("Ошибка соединения", f"Произошла ошибка при загрузке обновления! \nПовторите попытку позже!")
            self.root.destroy()


    def complete(self):
        self.canvas.delete("all")
        text = "Обновление загружено! Выполняется установка..."
        self.canvas.create_text(self.size // 2, self.size // 2, text=text, font=("Arial", 12, "bold"), fill="white", width=self.size)
