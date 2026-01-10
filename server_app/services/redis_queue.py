import json

from server_app import config


def get_redis():
    if not config.REDIS_ENABLED:
        return None
    try:
        import redis
    except Exception:
        return None
    try:
        return redis.Redis.from_url(config.REDIS_URL, decode_responses=True)
    except Exception:
        return None


def enqueue_scan(username, room, route):
    r = get_redis()
    if r is None:
        return False
    inflight_key = f"scan:inflight:{username.lower()}"
    if not r.set(inflight_key, "1", nx=True, ex=config.REDIS_TTL_SEC):
        return False
    payload = {"username": username, "room": room, "route": route}
    r.rpush("scan:queue", json.dumps(payload))
    return True


def enqueue_antivirus(payload):
    r = get_redis()
    if r is None:
        return False
    r.rpush("av:queue", json.dumps(payload))
    return True


def set_scan_result(username, result):
    r = get_redis()
    if r is None:
        return False
    key = f"scan:result:{username.lower()}"
    r.setex(key, config.REDIS_TTL_SEC, json.dumps(result))
    inflight_key = f"scan:inflight:{username.lower()}"
    r.delete(inflight_key)
    return True


def get_scan_result(username):
    r = get_redis()
    if r is None:
        return None
    key = f"scan:result:{username.lower()}"
    value = r.get(key)
    if value is None:
        return None
    r.delete(key)
    try:
        return json.loads(value)
    except Exception:
        return None
