import os

from aiohttp import web
import aiohttp_jinja2
import jinja2
from aiohttp_session import setup
from aiohttp_session.cookie_storage import EncryptedCookieStorage

import modules.db_manager as db_manager
import modules.dashboard as dashboard
import modules.file_counter as file_counter
import modules.logger as logger
from modules.asyncdb_pool import AsyncDatabasePool

from server_app import config, state
from server_app.middleware.request_logging import print_request
from server_app.handlers import auth, files, layout, logs, misc, notice, updates, upload


def configure_services():
    db_manager.users_db_data = {
        "host": os.getenv("DB_HOST"),
        "port": os.getenv("DB_PORT"),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "database": os.getenv("DB_USERS"),
        "min_size": int(os.getenv("DB_MIN_POOL")),
        "max_size": int(os.getenv("DB_MAX_POOL")),
    }
    db_manager.pool = db_manager.AsyncDatabasePool(**db_manager.users_db_data)

    file_counter.USERS_DATABASE = "users.db"

    dashboard.dashboard_db_data = {
        "host": os.getenv("DB_HOST"),
        "port": os.getenv("DB_PORT"),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "database": os.getenv("DB_DASHBOARD"),
        "min_size": int(os.getenv("DB_MIN_POOL")),
        "max_size": int(os.getenv("DB_MAX_POOL")),
    }
    dashboard.users_db_data = db_manager.users_db_data
    dashboard.pool = dashboard.AsyncDatabasePool(**dashboard.dashboard_db_data)
    dashboard.FILES_DIR = config.FILES_DIR


configure_services()
pool = AsyncDatabasePool(**dashboard.dashboard_db_data)


def build_blacklist():
    state.BLACK_LIST = [
        dashboard.login.__name__,
        dashboard.do_login.__name__,
        dashboard.users.__name__,
        misc.handle_ping.__name__,
        files.get_files_list.__name__,
        logs.handle_log.__name__,
        auth.get_key.__name__,
        updates.check_update_v2.__name__,
        updates.get_update_v2.__name__,
        updates.get_update_v2_sig.__name__,
        upload.handle_upload.__name__,
        misc.get_files_count.__name__,
        logs.handle_logs.__name__,
        dashboard.add_user.__name__,
        dashboard.delete_user.__name__,
        dashboard.update_user.__name__,
        dashboard.filter_users.__name__,
    ]


def register_routes(app):
    app.router.add_get("/", dashboard.login)
    app.router.add_post("/", dashboard.do_login)
    app.router.add_get("/users", dashboard.users)
    app.router.add_get("/get_data", dashboard.get_data)
    app.router.add_post("/add_user", dashboard.add_user)
    app.router.add_get("/delete_user", dashboard.delete_user)
    app.router.add_post("/update_user", dashboard.update_user)
    app.router.add_get("/filter_users", dashboard.filter_users)
    app.router.add_get("/logout", dashboard.logout)

    app.router.add_static("/static/", path="dashboard_data/static", name="static")
    aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader("dashboard_data/templates"))
    key = b"Team_FireStorm_CreatedBy_Dragmor"
    setup(app, EncryptedCookieStorage(key))

    app.router.add_get("/get-files-count", dashboard.get_files_count)
    app.router.add_post("/update_send_date", misc.update_send_date)
    app.router.add_post("/files_on_server", misc.get_files_count)
    app.router.add_get("/logs", logs.handle_logs)

    app.router.add_post("/upload", upload.handle_upload)
    app.router.add_get("/ping", misc.handle_ping)
    app.router.add_post("/login", auth.handle_login)
    app.router.add_post("/get_files_list", files.get_files_list)
    app.router.add_post("/errorlog", logs.handle_errorlog)
    app.router.add_post("/check_notice", notice.check_notice)
    app.router.add_post("/delete_notice", notice.delete_notice)
    app.router.add_post("/get_server", auth.get_server)
    app.router.add_post("/log", logs.handle_log)
    app.router.add_post("/get_key", auth.get_key)
    app.router.add_post("/get_layout", layout.get_layout)
    app.router.add_post("/checkupdate_v2", updates.check_update_v2)
    app.router.add_post("/getupdate_v2", updates.get_update_v2)
    app.router.add_post("/getupdate_v2_sig", updates.get_update_v2_sig)


async def init_conn(app):
    await pool.create_pool()


def start_server(manager):
    state.MANAGER = manager
    state.AUTH_USERS = manager.AUTH_USERS

    app = web.Application(middlewares=[print_request], client_max_size=config.MAX_UPLOAD_SIZE)
    app["pool"] = pool
    app.on_startup.append(dashboard.init_db)
    app.on_startup.append(db_manager.main)
    app.on_startup.append(init_conn)

    register_routes(app)
    build_blacklist()

    web.run_app(
        app,
        host=config.HOST,
        port=config.PORT,
        print=logger.sync_info(
            f"Сервер запущен на [{config.HOST}:{config.PORT}] Путь для сохранения данных: {config.FILES_DIR}. Ключей передано: {len(state.AUTH_USERS)}"
        ),
    )
