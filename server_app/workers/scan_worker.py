import json
import time

from server_app import config
from server_app.services.file_scan import collect_file_info
from server_app.services.redis_queue import get_redis, set_scan_result


def main():
    if not config.REDIS_ENABLED:
        raise SystemExit("REDIS_ENABLED=0, worker is disabled")
    r = get_redis()
    if r is None:
        raise SystemExit("Redis is not available")

    while True:
        item = r.blpop("scan:queue", timeout=5)
        if not item:
            continue
        _, payload = item
        try:
            data = json.loads(payload)
        except Exception:
            continue
        username = data.get("username")
        room = data.get("room")
        route = data.get("route")
        if not username or not room or not route:
            continue
        file_info = collect_file_info(username, room, route)
        set_scan_result(username, file_info)
        time.sleep(0.01)


if __name__ == "__main__":
    main()
