from PIL import Image
import threading
import os
import sys
import json
import hashlib
import shutil
from pathlib import Path
#
# устанавливаем путь к папке с софтом
def _parse_version_key(value):
    value = str(value or "").strip()
    if not value:
        return None
    parts = value.split(".")
    if len(parts) < 3:
        return None
    try:
        day = int(parts[0])
        month = int(parts[1])
        year = int(parts[2])
        build = int(parts[3]) if len(parts) > 3 else 0
    except ValueError:
        return None
    return (year, month, day, build)


def _prepare_paths():
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
        resource_dir = getattr(sys, "_MEIPASS", base_dir)
        data_dir = os.path.join(Path.home(), ".local", "share", "firestorm")
        os.makedirs(data_dir, exist_ok=True)
        for name in ("settings", "layouts", "img", "ver"):
            src = os.path.join(resource_dir, name)
            dst = os.path.join(data_dir, name)
            if os.path.isdir(src) and not os.path.exists(dst):
                shutil.copytree(src, dst)
            elif os.path.isfile(src) and not os.path.exists(dst):
                shutil.copy2(src, dst)
        # Keep local version if already updated; only seed on first run.
        resource_ver = os.path.join(resource_dir, "ver")
        data_ver = os.path.join(data_dir, "ver")
        if os.path.isfile(resource_ver):
            update_ver = False
            if not os.path.exists(data_ver):
                update_ver = True
            else:
                try:
                    with open(resource_ver, "r", encoding="utf-8") as file:
                        resource_val = file.readline().strip()
                    with open(data_ver, "r", encoding="utf-8") as file:
                        data_val = file.readline().strip()
                except Exception:
                    resource_val = ""
                    data_val = ""
                resource_key = _parse_version_key(resource_val)
                data_key = _parse_version_key(data_val)
                if resource_key is not None and data_key is not None:
                    update_ver = resource_key > data_key
                elif resource_val and resource_val != data_val:
                    # Fallback: sync to packaged version if parsing fails.
                    update_ver = True
            if update_ver:
                shutil.copy2(resource_ver, data_ver)
        # Merge new config defaults; update server only if it was default legacy.
        try:
            res_cfg = os.path.join(resource_dir, "settings", "config.json")
            data_cfg = os.path.join(data_dir, "settings", "config.json")
            if os.path.isfile(res_cfg):
                with open(res_cfg, "r", encoding="utf-8") as file:
                    res_data = json.load(file)
                if not os.path.exists(data_cfg):
                    shutil.copy2(res_cfg, data_cfg)
                else:
                    with open(data_cfg, "r", encoding="utf-8") as file:
                        data_data = json.load(file)
                    changed = False
                    for key, value in res_data.items():
                        if key not in data_data:
                            data_data[key] = value
                            changed = True
                    legacy_servers = {
                        "https://s1.firestorm.team",
                        "http://s1.firestorm.team",
                    }
                    if data_data.get("server") in legacy_servers and res_data.get("server"):
                        data_data["server"] = res_data["server"]
                        changed = True
                    if changed:
                        with open(data_cfg, "w", encoding="utf-8") as file:
                            json.dump(data_data, file, ensure_ascii=False)
        except Exception:
            pass
        # Remember install dir for updater restarts.
        try:
            with open(os.path.join(data_dir, "app_dir.txt"), "w", encoding="utf-8") as file:
                file.write(base_dir)
        except Exception:
            pass
        os.chdir(data_dir)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        resource_dir = base_dir
        data_dir = base_dir
        os.chdir(base_dir)
    return base_dir, resource_dir, data_dir


base_dir, resource_dir, data_dir = _prepare_paths()
os.environ["FIRESTORM_BASE"] = data_dir
os.environ["FIRESTORM_APP_DIR"] = base_dir
#
import modules.app_gui as app_gui


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def resolve_runtime_file(rel_path):
    candidates = [
        os.path.join(data_dir, rel_path),
        os.path.normpath(rel_path),
    ]
    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate
        if os.path.isdir(candidate):
            nested = os.path.join(candidate, os.path.basename(rel_path))
            if os.path.isfile(nested):
                return nested
    return candidates[0]


def verify_manifest(required):
    manifest_path = os.path.join(data_dir, "manifest.json")
    if not os.path.exists(manifest_path):
        if required:
            print("manifest.json не найден. Запуск остановлен.")
            return False
        return True
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    except Exception:
        print("manifest.json поврежден. Запуск остановлен.")
        return False if required else True

    files = manifest.get("files", {})
    for rel_path, expected in files.items():
        file_path = resolve_runtime_file(rel_path)
        if not os.path.exists(file_path):
            print(f"Файл {rel_path} отсутствует. Запуск остановлен.")
            return False
        if os.path.isdir(file_path):
            print(f"Файл {rel_path} имеет некорректный тип (директория). Запуск остановлен.")
            return False
        actual = sha256_file(file_path)
        if actual.lower() != str(expected).lower():
            print(f"Файл {rel_path} поврежден. Запуск остановлен.")
            return False
    return True

class FireStorm:
    def __init__(self):

        # извлекаем адрес сервера из файла с настройками
        with open(os.path.join(data_dir, "settings", "config.json"), "r") as file:
            data = json.load(file)
        require_manifest = bool(data.get("require_manifest", False))
        if not verify_manifest(require_manifest):
            sys.exit(1)
        server_url = data["server"]
        self.main_window = app_gui.PokerCheckApp(
            parent=self,
            url=server_url,
            height=600,
            width=1024,
        )

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
    file_to_check = os.path.join(data_dir, "delete.txt")
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
