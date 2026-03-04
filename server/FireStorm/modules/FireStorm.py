from PIL import Image
import threading
import os
import sys
import json
#
# устанавливаем путь к папке с софтом
os.chdir(os.path.dirname(sys.argv[0]))
#
import modules.app_gui as app_gui

class FireStorm:
    def __init__(self):

        # извлекаем адрес сервера из файла с настройками
        with open("settings/config.json", "r") as file:
            data = json.load(file)
        server_url = data["server"]
        self.main_window = app_gui.PokerCheckApp(parent=self, url=server_url, height=600, width=1024)

        # запускаем поток для создания ГУИ
        # self.main_window.create_widgets()


def delete_files(file_paths):
    for file_path in file_paths:
        if os.path.isfile(file_path):
            try:
                os.remove(file_path)
                print(f"Файл {file_path} успешно удалён.")
            except Exception as error:
                print(f"Не хватает прав для удаления файла {file_path}: {error}")
                return False
    return True

def check_del_file():
    file_to_check = 'delete.txt'
    if os.path.isfile(file_to_check):
        with open(file_to_check, 'r') as file:
            paths = file.read().splitlines()
        if delete_files(paths):
            try:
                os.remove(file_to_check)
                print(f"Ok! Файл {file_to_check} успешно обработан и удалён!")
            except:
                print(f"Не могу удалить {file_to_check}, попробуйте запустить с правами администратора.")
    else:
        print(f"Файл {file_to_check} не найден.")

# проверяем, есть-ли файлы на удаление
try:
    check_del_file()
except Exception as error:
    print(f"Не удалось проверить файлы, которые нужно удалить. Error: {error}")

# создаём экземпляр приложения
app = FireStorm()



"""
# отправляем лог ошибки на сервер
except Exception as e:
    text = "Произошла непредвиденная ошибка!"
    asyncio.run(http_client.send_log(URL=self.server_url, username=self.login_entry.get(), error=str(e)))
    print(e)
"""