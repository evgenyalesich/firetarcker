import ast
import json
import os
import time

from server_app import config, state


def is_safe_component(value):
    if not value:
        return False
    if value in {".", ".."}:
        return False
    for sep in (os.sep, os.altsep):
        if sep and sep in value:
            return False
    return True


def normalize_relpath(value):
    if not value:
        return ""
    norm = os.path.normpath(value)
    if os.path.isabs(norm) or norm.startswith("..") or norm == "..":
        return None
    return "" if norm == "." else norm


def get_real_ip(request):
    real_ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
    if not real_ip:
        real_ip = request.headers.get("X-Real-IP", "").strip()
    return real_ip or request.remote or "unknown"


def is_rate_limited(ip, path):
    limit = config.RATE_LIMITS.get(path, config.RATE_LIMITS["default"])
    now = time.monotonic()
    dq = state.RATE_LIMIT_STORE[(ip, path)]
    window_sec = limit["window_sec"]
    while dq and (now - dq[0]) > window_sec:
        dq.popleft()
    if len(dq) >= limit["max_requests"]:
        return True
    dq.append(now)
    return False


def parse_structured_data(value):
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except Exception:
        pass
    try:
        return ast.literal_eval(value)
    except Exception:
        return None
