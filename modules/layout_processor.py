import asyncio
import os
import zipfile
import io
from aiohttp import web


async def pack_layout(room_name, data, paths):
    '''
    data - выбранные юзером элементы
    paths - пути из файла соответствий

    для TigerGaming, BetOnline и SportsBetting
    пакуем в zip-архив нужные файлы, а zip храним в ОЗУ и его возвращаем
    '''


    base_dir = f'layouts/{room_name}' # Путь к нужному лейауту
    file_path = ''  # Путь к файлу

    # если нет архива, создаём его сразу в ОЗУ
    if not os.path.exists(f'{base_dir}/sample.zip'):
        zip_buffer = io.BytesIO()
    else:
        # Открываем zip-архив для чтения
        with open(f'{base_dir}/sample.zip', 'rb') as file:
            # Читаем содержимое архива в память
            zip_data = file.read()

        # Создаем объект BytesIO для работы с данными в памяти
        zip_buffer = io.BytesIO(zip_data)

    # Создаем объект zipfile для работы с архивом
    archive = zipfile.ZipFile(zip_buffer, 'a')

    # тут добавляем файлы в архив
    for choosed in data:
        if data[choosed]:
            if choosed in paths:
                if choosed not in paths:
                    continue
                if data[choosed] in paths[choosed]:

                    for file in paths[choosed][data[choosed]]:
                        if type(file) == list:
                            path = os.path.join(os.getcwd(), "layouts", room_name, file[0])
                            file = file[1]
                        else:
                            path = os.path.join(os.getcwd(), "layouts", room_name, file)
                        path = os.path.normpath(path)
                        if os.path.exists(path):
                            # если это одиночный файл
                            if os.path.isfile(path):
                                archive.write(path, file)
                            # если же это папка с файлами
                            elif os.path.isdir(path):
                                for root, dirs, files in os.walk(path):
                                    for f in files:
                                        file_path = os.path.join(root, f)
                                        archive.write(file_path, os.path.join(file, os.path.relpath(file_path, path)))
                        else:
                            print(f"File {path} is not exists!")

    # Сохраняем изменения в архиве
    archive.close()
    # Перемещаем указатель в начало объекта BytesIO
    zip_buffer.seek(0)
    # Получаем байтовое представление измененного архива
    updated_zip_data = zip_buffer.getvalue()

    return updated_zip_data

