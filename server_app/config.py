import os
import json
import shutil

SECRET_KEY = os.getenv("SECRET_KEY")

FILES_DIR = os.getenv("FILES_DIR", "/var/lib/fstracker")

HOST = "0.0.0.0"
PORT = 8080

MAX_UPLOAD_SIZE = int(os.getenv("MAX_UPLOAD_SIZE_MB", "200")) * 1024 * 1024

RATE_LIMITS = {
    "default": {"window_sec": 60, "max_requests": int(os.getenv("RATE_LIMIT_DEFAULT", "180"))},
    "/login": {"window_sec": 60, "max_requests": int(os.getenv("RATE_LIMIT_LOGIN", "30"))},
    "/upload": {"window_sec": 60, "max_requests": int(os.getenv("RATE_LIMIT_UPLOAD", "600"))},
    "/get_files_list": {"window_sec": 60, "max_requests": int(os.getenv("RATE_LIMIT_FILELIST", "120"))},
}

CLAMAV_ENABLED = os.getenv("CLAMAV_ENABLED", "0") == "1"
CLAMAV_TIMEOUT_SEC = int(os.getenv("CLAMAV_TIMEOUT_SEC", "30"))
CLAMAV_CMD = os.getenv("CLAMAV_CMD", "")
if not CLAMAV_CMD:
    CLAMAV_CMD = "clamdscan" if shutil.which("clamdscan") else "clamscan" if shutil.which("clamscan") else ""

QUARANTINE_DIR = os.getenv("QUARANTINE_DIR", "quarantine")
QUARANTINE_ACTION = os.getenv("QUARANTINE_ACTION", "quarantine")

REDIS_ENABLED = os.getenv("REDIS_ENABLED", "0") == "1"
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
REDIS_TTL_SEC = int(os.getenv("REDIS_TTL_SEC", "600"))

with open("servers.json", "r") as file:
    SERVERS = json.load(file)
