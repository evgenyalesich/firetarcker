import tkinter as tk
from tkinter import filedialog, Text
import zipfile
import os
import datetime

class ZipperApp:
    def __init__(self, root):
        self.folder_path = ""
        self.root = root
        self.root.title("FireStormUpdater")
        self.root.geometry("320x320")
        self.root.resizable(False, False)
        
        self.version_label = tk.Label(root, text="Укажите номер версии:")
        self.version_label.pack(fill="both")
        
        # Текущая дата в формате ГГ.ММ.ДД
        current_date = datetime.datetime.now().strftime('%y.%m.%d')
        self.version_entry = tk.Entry(root, justify="center", width=30)
        self.version_entry.pack(fill="both", padx=4)
        self.version_entry.insert(0, current_date)
        
        self.folder_button = tk.Button(root, text="Указать папку с файлами ПО", command=self.select_folder)
        self.folder_button.pack(fill="both", pady=14, padx=4)
        
        self.news_label = tk.Label(root, text="Введите текст новостей (опционально):")
        self.news_label.pack(fill="both")
        
        self.news_text = Text(root, height=8)
        self.news_text.pack(fill="both", padx=4, pady=4)
        
        self.status_label = tk.Label(self.root, text="")
        self.status_label.pack(fill="both")
        
        self.start_button = tk.Button(root, text="Начать", bg="#90ee90", command=self.start_zip)  # Светло-зелёная кнопка
        self.start_button.pack(fill="both", side="bottom", pady=4)
        
    def select_folder(self):
        self.folder_path = filedialog.askdirectory()
        if self.folder_path:
            self.folder_button.config(text=os.path.basename(self.folder_path))
        else:
            self.folder_button.config(text="Указать папку с файлами ПО")
            
    def start_zip(self):
        # версия сборки обновы
        version = self.version_entry.get().strip()
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
                
                self.status_label.configure(text="Успех!")
            else:
                self.status_label.configure(text="Ошибка: не выбрана папка")
        
root = tk.Tk()
app = ZipperApp(root)
root.mainloop()
