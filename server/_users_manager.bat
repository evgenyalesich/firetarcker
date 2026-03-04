@echo off
REM Установка переменной среды
set DB_HOST=127.0.0.1
set DB_PORT=5432
set DB_USER=postgres
set DB_PASSWORD=Mvh54g2y
set DB_NAME=firetracker

REM Запуск скрипта
C:\Users\ITadmin\Desktop\server\env\Scripts\python.exe "C:\Users\ITadmin\Desktop\server\apps\UserManager.py" -d
pause

