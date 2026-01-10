import os
import json
from datetime import datetime, timedelta
from pathlib import Path
# 
from tkinter import messagebox

# все доступные в системе диски
drives = [d for d in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" if os.path.exists(f"{d}:\\")]
# системные пути для подстановки
def _get_appdata():
    userprofile = os.getenv("USERPROFILE")
    if userprofile:
        return os.path.join(userprofile, "AppData")
    xdg_data_home = os.getenv("XDG_DATA_HOME")
    if xdg_data_home:
        return xdg_data_home
    return str(Path.home() / ".local" / "share")


system_paths = {
    "appdata": _get_appdata(),
    "user": os.path.expanduser("~"),
    "documents": str(Path.home() / "Documents"),
    "desktop": str(Path.home() / "Desktop"),
    }

def load_conf(json_file):
    try:
        if os.path.exists(json_file):
            with open(json_file, 'r') as file:
                data = json.load(file)
            return data
        else:
            print(f"Нет файла со списком проверяемых путей: {json_file}")
            return None
    except Exception as error:
        print(f'Ошибка при открытии файла конфигураций: {error}')
        return None

def save_conf(json_file, paths, last_check):
    try:
        with open(json_file, 'w') as file:
            file.write(json.dumps({"paths": paths, "last_check": last_check}, indent=4))
    except Exception as error:
        print(f'Ошибка при сохраненииии файла конфигураций: {error}')

def check_paths(json_file, added_paths):
    current_date = datetime.now()
    conf_data = load_conf(json_file)
    if conf_data:
        paths = conf_data.get("paths", [])
        last_check = conf_data.get("last_check", "")
    else:
        return []
    # если дата в файле не указана - ставим сегодняшнюю
    if not last_check:
        last_check = current_date.strftime('%d-%m-%Y')
        need_check = True
    else:
        # переводим дату из файла в дату
        parsed_date = datetime.strptime(last_check, '%d-%m-%Y')
        # высчитываем, прошло-ли 7 дней с момента последней проверки
        need_check = (current_date - parsed_date) >= timedelta(days=7)
    if not need_check:
        return []
    # сохраняем новые данные в файл
    save_conf(json_file, paths, current_date.strftime('%d-%m-%Y'))



    tmp_paths = []
    for room, room_data in added_paths.items():
        tmp_paths += room_data['folders'] if room_data['track'] else []
    added_paths = [os.path.normpath(path.lower()) for path in tmp_paths]
    
    print(f"В трекере включены пути: {added_paths}")
    
    try:
        expanded_paths = []
        # выполняем подстановку для плесхолдеров {disk}, заменяя
        # его на буквы всех доступных дисков, расширяя тем самым списко путей
        for path in paths:
            file_path = path.get("path", "")
            if "{disk}" in file_path:
                expanded_paths.extend([{"room": path.get("room"), "path": f"{d}{file_path.replace('{disk}', '')}"} for d in drives])
            else:
                expanded_paths.append(path)
        paths = expanded_paths
        print("\n".join([path['path'] for path in paths]))
        # Список для путей, которые нужно обработать
        paths_to_process = []
        for path in paths:
            try:
                # делаем подстановку путей {} если она тут требуется
                formatted_path = path.get("path").format(**system_paths)
                print(formatted_path)
                # Проверка существования пути
                if os.path.exists(formatted_path):
                    # Проверка наличия файлов в пути
                    if any(os.scandir(formatted_path)):
                        # Проверка наличия пути в списке added_paths
                        formatted_path_lower = formatted_path.lower()
                        if not any(formatted_path_lower in added_path for added_path in added_paths):
                            paths_to_process.append({"room": path.get("room"), "path": formatted_path})
            except Exception as e:
                print(f"Error processing path {formatted_path}: {e}")

        return paths_to_process

    except Exception as e:
        print(e)
        return []

def remove_longer_containing_strings(strings):
    sorted_strings = sorted(strings, key=len)
    to_remove = set()
    for i, short_str in enumerate(sorted_strings):
        for long_str in sorted_strings[i+1:]:
            if short_str in long_str:
                to_remove.add(long_str)
    result = [s for s in sorted_strings if s not in to_remove]
    return result

def run_check(window, services, auto_switch_track):
    """
    Принимает окно и список путей которые у юзера уже выбраны.
    added_paths должен быть словарём (данными из файла services.json)
    auto_switch_track если True, то значит переключатель трекинга автоматически установится в True
    в функции которая вызвала данную функцию. Если False, то переключение произойдёт внутри этой функции
    """
    # Файл с дефолтными путями
    json_file = 'settings/default_paths.json'
    print(f"services={services}")
    services["services"][next(iter(services["services"].keys()))]['folders'] = remove_longer_containing_strings((services["services"][next(iter(services["services"].keys()))]['folders']))
    with open("settings/services.json", 'w') as file:
        file.write(json.dumps(services, indent=4))

    paths_to_process = check_paths(json_file, services["services"])
    print(f"Пути которые нужно добавить: {paths_to_process}")
    if paths_to_process:
        formatted_path = "\n".join([path['path'] for path in paths_to_process])
        response = messagebox.askyesno(
            "Найдены стандартные пути",
            f"В системе обнаружены пути с файлами, но в трекере не включено отслеживание этих путей! Хотите автоматически включить эти пути для отслеживания?\n{formatted_path}"
        )
        if response:
            # Логика для включения путей для отслеживания
            print("Добавляем пути для отслеживания...")
            # добавляем пути в свои папки
            for room_name, selected_paths in services['services'].items():
                for p_obj in paths_to_process:
                    if room_name.lower() == p_obj['room'].lower():
                        services['services'][room_name]['folders'].append(p_obj['path'])
                        if not auto_switch_track:
                            services["services"][room_name]['track'] = True
                if services['services'][room_name]['folders']:
                    # Чистим от вложенных папок
                    services['services'][room_name]['folders'] = remove_longer_containing_strings(services['services'][room_name]['folders'])

            with open("settings/services.json", 'w') as file:
                file.write(json.dumps(services, indent=4))
            
            #возвращаем истину если добавились новые пути 
            return True
        else:
            print("Пути не будут добавлены для отслеживания.")
            return False
    else:
        return True
    

"""
+сделать срабатываение раз в неделю (в этот-же файл добавить дату последнего чека)
-сделать подстановку в {appdata}, {user}, {documents} полных путей!
+добавить код в uploader и в inj_uploader
-собрать новые файлы в основной проект, скомпилить
"""
