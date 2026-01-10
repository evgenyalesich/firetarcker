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


def load_config():
    config_path = os.path.join(os.getcwd(), "settings", "config.json")
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

# Открываем архив
config = load_config()
require_signature = bool(config.get("require_signature", False))
public_key_path = config.get("public_key_path", os.path.join("settings", "public.key"))

if os.path.exists("update.zip"):
    if require_signature:
        sig_path = "update.zip.asc"
        if not os.path.exists(sig_path):
            print("Подпись обновления не найдена. Установка остановлена.")
            raise SystemExit(1)
        if not verify_signature("update.zip", sig_path, public_key_path):
            print("Подпись обновления невалидна. Установка остановлена.")
            raise SystemExit(1)
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
script_path = os.path.join(os.getcwd(), "FireStorm.py")
python_path = sys.executable
subprocess.Popen([python_path, script_path], shell=False)
