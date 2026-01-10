import asyncio
from collections import defaultdict, deque

from server_app import config

AUTH_USERS = {}
USERS_FILES = {}
PATH_LAYOUTS = {}
MANAGER = None

SERVERS = config.SERVERS

RATE_LIMIT_STORE = defaultdict(deque)

semaphore = asyncio.Semaphore(256)

BLACK_LIST = []
