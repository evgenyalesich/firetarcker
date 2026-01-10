import hashlib
import os

from server_app import config
import modules.logger as logger


def collect_file_info(username, room, route):
    path = os.path.join(config.FILES_DIR, route, username, room)
    logger.sync_debug(f"Поступил запрос от {username} на получение списка файлов рума: {room}")

    file_info = []
    if not os.path.exists(path):
        os.makedirs(path)
    subfolders = [f.path for f in os.scandir(path) if f.is_dir()]
    for subfolder in subfolders:
        if os.path.exists(subfolder):
            for root, dirs, files in os.walk(subfolder):
                for file in files:
                    relative_path = os.path.relpath(os.path.join(root, file), subfolder)
                    file_path = os.path.normpath(os.path.join(root, file))

                    if file.lower().endswith("db"):
                        with open(file_path, mode="rb") as f:
                            md5_hash = hashlib.md5()
                            while chunk := f.read(4096):
                                md5_hash.update(chunk)
                            checksum = md5_hash.hexdigest()
                    else:
                        checksum = None

                    file_info.append([relative_path, checksum])

    return file_info
