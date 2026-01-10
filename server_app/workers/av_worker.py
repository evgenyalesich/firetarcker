import json
import os
import time

import modules.logger as logger
from server_app import config
from server_app.services.antivirus import scan_file
from server_app.services.antivirus import quarantine_file
from server_app.services.redis_queue import get_redis


def handle_infected(file_path, payload):
    action = config.QUARANTINE_ACTION
    filename = os.path.basename(file_path)
    username = payload.get("username")
    if action == "ignore":
        logger.sync_info(
            f'[AV] Файл "{filename}" от "{username}" заражен, но оставлен по политике'
        )
        return
    if action == "delete":
        try:
            os.remove(file_path)
        except OSError:
            pass
        logger.sync_info(
            f'[AV] Файл "{filename}" от "{username}" удалён как зараженный'
        )
        return
    quarantined = quarantine_file(
        file_path,
        payload.get("route"),
        payload.get("username"),
        payload.get("room"),
        payload.get("date"),
        payload.get("subdirs"),
    )
    logger.sync_info(
        f'[AV] Файл "{filename}" от "{username}" перемещён в карантин: {quarantined}'
    )


def main():
    if not (config.REDIS_ENABLED and config.CLAMAV_ENABLED):
        raise SystemExit("REDIS_ENABLED=0 or CLAMAV_ENABLED=0, worker is disabled")
    r = get_redis()
    if r is None:
        raise SystemExit("Redis is not available")

    while True:
        item = r.blpop("av:queue", timeout=5)
        if not item:
            continue
        _, payload = item
        try:
            data = json.loads(payload)
        except Exception:
            continue
        file_path = data.get("file_path")
        if not file_path or not os.path.exists(file_path):
            continue

        result = scan_file(file_path)
        if result == "infected":
            handle_infected(file_path, data)
        elif result == "error":
            logger.sync_error(f"[AV] Ошибка антивирусной проверки файла: {file_path}")
        time.sleep(0.01)


if __name__ == "__main__":
    main()
