import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter import scrolledtext
import zipfile
import os
import datetime

class ZipperApp:
    def __init__(self, root):
        self.folder_path = ""
        self.root = root
        self.root.title("FireStorm Updater")
        self.root.geometry("420x380")
        self.root.resizable(False, False)

        self.style = ttk.Style()
        self.style.theme_use("clam")

        self.main = ttk.Frame(root, padding=12)
        self.main.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        header = ttk.Label(self.main, text="Сборка обновления FireStorm", font=("TkDefaultFont", 11, "bold"))
        header.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))

        self.version_label = ttk.Label(self.main, text="Номер версии:")
        self.version_label.grid(row=1, column=0, sticky="w")

        # Текущая дата в формате ГГ.ММ.ДД
        current_date = datetime.datetime.now().strftime('%y.%m.%d')
        self.version_var = tk.StringVar(value=current_date)
        self.version_entry = ttk.Entry(self.main, textvariable=self.version_var, width=24, justify="center")
        self.version_entry.grid(row=1, column=1, sticky="we", padx=(8, 0))

        self.folder_var = tk.StringVar(value="Папка не выбрана")
        self.folder_entry = ttk.Entry(self.main, textvariable=self.folder_var, state="readonly")
        self.folder_entry.grid(row=2, column=0, columnspan=2, sticky="we", pady=(12, 0))
        self.folder_button = ttk.Button(self.main, text="Выбрать папку", command=self.select_folder)
        self.folder_button.grid(row=2, column=2, sticky="e", padx=(8, 0), pady=(12, 0))

        self.news_label = ttk.Label(self.main, text="Текст новостей (опционально):")
        self.news_label.grid(row=3, column=0, columnspan=3, sticky="w", pady=(12, 4))

        self.news_text = scrolledtext.ScrolledText(self.main, height=8)
        self.news_text.grid(row=4, column=0, columnspan=3, sticky="nsew")
        self.main.rowconfigure(4, weight=1)

        self.status_var = tk.StringVar(value="")
        self.status_label = ttk.Label(self.main, textvariable=self.status_var)
        self.status_label.grid(row=5, column=0, columnspan=3, sticky="w", pady=(8, 4))

        self.start_button = ttk.Button(self.main, text="Собрать архив", command=self.start_zip)
        self.start_button.grid(row=6, column=0, columnspan=3, sticky="we")
        
    def select_folder(self):
        self.folder_path = filedialog.askdirectory()
        if self.folder_path:
            self.folder_var.set(self.folder_path)
        else:
            self.folder_var.set("Папка не выбрана")
            
    def start_zip(self):
        # версия сборки обновы
        version = self.version_var.get().strip()
        if not version:
            messagebox.showwarning("Внимание", "Укажите номер версии.")
            return
        news_text = self.news_text.get("1.0", tk.END).strip()  # Получить текст из поля новостей

        zip_name = "update_v2.zip"
        # Используем контекстный менеджер для работы с файлом
        with zipfile.ZipFile(zip_name, 'w') as zipf:
            if self.folder_path:
                for root, dirs, files in os.walk(self.folder_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        zipf.write(file_path, os.path.relpath(file_path, self.folder_path))
                # Записываем комментарий к архиву с номером сборки
                zipf.comment = version.encode('utf-8')
                # Если текст новостей был введен, создаем текстовый файл в архиве
                if news_text:
                    zipf.writestr('news.txt', news_text)
                self.status_var.set(f"Успех! Архив собран: {zip_name}")
            else:
                self.status_var.set("Ошибка: не выбрана папка")
                messagebox.showerror("Ошибка", "Не выбрана папка с файлами.")
        
root = tk.Tk()
app = ZipperApp(root)
root.mainloop()
