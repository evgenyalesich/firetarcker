'''
скрипт для загрузки и установки обнов.
Алгоритм: основная прога чекает обновы. Если находит, то запускает updater, а сама
закрывается. Апдейтер после скачивания файлов обновы, закидывает их в папку приложения,
запускает основную прогу, и завершает работу
'''

import subprocess
import zipfile
import os

# Открываем архив
if os.path.exists("update.zip"):
    with zipfile.ZipFile('update.zip', 'r') as zip_ref:
        # Извлекаем все файлы в текущую директорию
        for file in zip_ref.namelist():
            try:
                zip_ref.extract(file, '.')
            except:
                print(f"Ошибка при извлечении файла: {file}. Пропускаем его.")

        # Получаем комментарий архива
        comment = zip_ref.comment.decode('utf-8')

    # Открываем файл 'ver' и записываем в него комментарий
    with open('ver', 'w') as ver_file:
        ver_file.write(comment)

# Запускаем 'FireStorm'
python_path = f"{os.path.join(os.path.dirname(os.getcwd()), 'pythonw.exe')}"
script_path = f"{os.path.join(os.getcwd(), 'FireStorm.py')}"

subprocess.Popen([f'{python_path}', script_path], shell=True)
