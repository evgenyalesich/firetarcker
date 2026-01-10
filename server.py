import os
import time
import requests
from multiprocessing import Process, Manager

import modules.logger as logger

# переходим в указанный из окружения путь к корневому каталогу сервера
if (root_path := os.getenv("SERVER_ROOT")):
    os.chdir(root_path)

from server_app.app import start_server
from server_app import config


if __name__ == "__main__":
    with Manager() as manager:
        ns = manager.Namespace()
        ns.AUTH_USERS = {}

        server_process = Process(target=start_server, args=(ns,))
        server_process.start()

        while True:
            try:
                time.sleep(20)
                try:
                    response = requests.get(
                        f"http://localhost:{config.PORT}/ping", timeout=40
                    )
                    if response.status_code != 200:
                        logger.sync_debug("Сервер не ответил, перезапуск...")
                        logger.sync_debug(f"ключей в ОЗУ: {len(ns.AUTH_USERS)}")

                        if server_process.is_alive():
                            server_process.terminate()
                            server_process.join()
                        server_process = Process(target=start_server, args=(ns,))
                        server_process.start()

                except requests.exceptions.RequestException:
                    logger.sync_debug("Сервер не ответил, перезапуск...")
                    logger.sync_debug(f"ключей в ОЗУ: {len(ns.AUTH_USERS)}")

                    if server_process.is_alive():
                        server_process.terminate()
                        server_process.join()
                    server_process = Process(target=start_server, args=(ns,))
                    server_process.start()

            except Exception:
                if server_process.is_alive():
                    server_process.terminate()
                    server_process.join()
                server_process = Process(target=start_server, args=(ns,))
                server_process.start()
