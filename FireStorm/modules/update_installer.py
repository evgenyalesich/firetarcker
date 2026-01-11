'''
скрипт для загрузки и установки обнов.
Алгоритм: основная прога чекает обновы. Если находит, то запускает updater, а сама
закрывается. Апдейтер после скачивания файлов обновы, закидывает их в папку приложения,
запускает основную прогу, и завершает работу
'''

import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile


def load_config(base_dir):
    config_path = os.path.join(base_dir, "settings", "config.json")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def verify_signature(archive_path, signature_path, public_key_path):
    gpg = shutil.which("gpg")
    if not gpg:
        return False
    if not (os.path.exists(signature_path) and os.path.exists(public_key_path)):
        return False
    with tempfile.TemporaryDirectory() as gnupg_home:
        env = os.environ.copy()
        env["GNUPGHOME"] = gnupg_home
        import_result = subprocess.run(
            [gpg, "--import", public_key_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )
        if import_result.returncode != 0:
            return False
        verify_result = subprocess.run(
            [gpg, "--verify", signature_path, archive_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )
        return verify_result.returncode == 0

base_dir = os.getenv("FIRESTORM_BASE", os.getcwd())
app_dir = os.getenv("FIRESTORM_APP_DIR")
if not app_dir:
    app_hint = os.path.join(base_dir, "app_dir.txt")
    if os.path.isfile(app_hint):
        try:
            with open(app_hint, "r", encoding="utf-8") as file:
                app_dir = file.read().strip() or None
        except Exception:
            app_dir = None

# Открываем архив
config = load_config(base_dir)
require_signature = bool(config.get("require_signature", False))
public_key_path = config.get("public_key_path", os.path.join(base_dir, "settings", "public.key"))

update_zip = os.path.join(base_dir, "update.zip")
if os.path.exists(update_zip):
    if require_signature:
        sig_path = update_zip + ".asc"
        if not os.path.exists(sig_path):
            print("Подпись обновления не найдена. Установка остановлена.")
            raise SystemExit(1)
        if not verify_signature(update_zip, sig_path, public_key_path):
            print("Подпись обновления невалидна. Установка остановлена.")
            raise SystemExit(1)
    with zipfile.ZipFile(update_zip, 'r') as zip_ref:
        # Извлекаем все файлы в папку данных
        for file in zip_ref.namelist():
            try:
                zip_ref.extract(file, base_dir)
            except:
                print(f"Ошибка при извлечении файла: {file}. Пропускаем его.")

        # Получаем комментарий архива
        comment = zip_ref.comment.decode('utf-8')

    # Открываем файл 'ver' и записываем в него комментарий
    ver_path = os.path.join(base_dir, "ver")
    if os.path.isdir(ver_path):
        ver_path = os.path.join(ver_path, "ver")
    with open(ver_path, 'w') as ver_file:
        ver_file.write(comment)

    try:
        os.remove(update_zip)
    except Exception:
        pass
    if os.path.exists(update_zip + ".asc"):
        try:
            os.remove(update_zip + ".asc")
        except Exception:
            pass

# Запускаем 'FireStorm'
exe_name = "FireStorm.exe" if sys.platform.startswith("win") else "FireStorm"
if app_dir and os.path.exists(os.path.join(app_dir, exe_name)):
    subprocess.Popen([os.path.join(app_dir, exe_name)], shell=False)
else:
    script_path = os.path.join(base_dir, "FireStorm.py")
    python_path = sys.executable
    subprocess.Popen([python_path, script_path], shell=False)
