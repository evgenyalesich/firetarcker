@echo off
REM Установка переменной среды
set DB_HOST=ip_адрес_postgres
set DB_PORT=port
set DB_USER=юзернейм_пользователя_бд
set DB_PASSWORD=пароль
set DB_NAME=название_бд
set ROOT_DIR=полный_путь_к_корневому_каталогу_сервера

REM Запуск скрипта
C:\Users\killmenow\AppData\Local\Programs\Python\Python311\python.exe "C:\Users\killmenow\Desktop\poker\project\server\apps\notice_sender.py" -d
pause

