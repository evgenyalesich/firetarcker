@echo off
REM Установка переменной среды
set DB_HOST=ip_адрес_postgres
set DB_PORT=port
set DB_USER=юзернейм_пользователя_бд
set DB_PASSWORD=пароль
set DB_USERS=бд_юзеров
set DB_DASHBOARD=бд_дешборда
set DB_MIN_POOL=минимальное_количество_соединений_в_пуле
set DB_MAX_POOL=максимальное_кол-во_соединений_в_пуле
set SERVER_ROOT=полный_путь_к_папке_в_которой_лежит_server.py
SET SECRET_KEY=секретный_ключ
SET DS_TOKEN=токен дискорд бота для рассылки инфы в каналы

start "C:\путь\к\nginx.exe"

REM Запуск сервера
C:\Users\killmenow\AppData\Local\Programs\Python\Python311\python.exe "C:\Users\killmenow\Desktop\poker\project\server\server.py" -d
pause

