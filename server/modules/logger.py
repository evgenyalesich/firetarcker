import os
import sys
import asyncio
from colorama import Fore, Style, init
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from collections import deque
import threading
import aioconsole

# Инициализация colorama
init(autoreset=True)

# получаем аргументы запуска
# если False - не перенаправляем стандартный вывод
if "-d" not in sys.argv:
    DEBUG = False
else:
    DEBUG = True

# Пути к файлам логов
LOG_FILES = {
    'DEBUG': 'logs/debug.log',
    'INFO': 'logs/info.log',
    'REQST': 'logs/request.log',
    'ERROR': 'logs/error.log',
}

# Максимальное количество строк в логах
MAX_LINES = 300

# Создание пула потоков для записи в файл (с одним рабочим потоком)
executor = ThreadPoolExecutor(max_workers=1)

if not DEBUG:
    # сохраняем текущие потоки вывода
    stdout = sys.stdout
    stderr = sys.stderr
    sys.stdout = open(os.devnull, 'w')
    sys.stderr = open(os.devnull, 'w')

# Подготовка файлов логов
if not os.path.exists("logs"):
    os.makedirs("logs")
for file_path in LOG_FILES.values():
    open(file_path, 'a', encoding='utf-8').close()

def change_output(visible=False):
    if DEBUG:
        return
    if visible:
        # Вывод в консоль
        sys.stdout = stdout
        sys.stderr = stderr
    else:
        sys.stdout = open(os.devnull, 'w')
        sys.stderr = open(os.devnull, 'w')

# Функция для асинхронной записи в файл с ограничением на максимальное количество строк
def write_to_log(file_path, text):
    with threading.Lock():
        # Считываем существующие строки в файл, сохранив только MAX_LINES последних
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                lines = deque(file, maxlen=MAX_LINES)
        except FileNotFoundError:
            lines = deque(maxlen=MAX_LINES)
        except Exception as error:
            print(error)
        # Добавляем новый текст
        lines.append(text + '\n')
        
        # Записываем строки обратно в файл
        with open(file_path, 'w', encoding='utf-8') as file:
            file.writelines(lines)



# Асинхронные функции логирования
async def debug(text):

    change_output(True)
    await aioconsole.aprint(
        Style.BRIGHT + datetime.now().strftime("%d-%m-%Y : %H:%M:%S"),
        ">",
        Fore.CYAN + "[DEBUG]",
        ">",
        Style.BRIGHT + Fore.CYAN + text
    )
    change_output(False)
    # Запись в файл
    executor.submit(write_to_log, LOG_FILES['DEBUG'], f'{datetime.now().strftime("%d-%m-%Y : %H:%M:%S")} > {text}')

async def info(text):

    change_output(True)
    await aioconsole.aprint(
        Style.BRIGHT + datetime.now().strftime("%d-%m-%Y : %H:%M:%S"),
        ">",
        Fore.GREEN + "[INFO ]",
        ">",
        Style.BRIGHT + Fore.GREEN + text
    )
    change_output(False)
    # Запись в файл
    executor.submit(write_to_log, LOG_FILES['INFO'], f'{datetime.now().strftime("%d-%m-%Y : %H:%M:%S")} > {text}')

async def request(text):

    change_output(True)
    await aioconsole.aprint(
        Style.BRIGHT + datetime.now().strftime("%d-%m-%Y : %H:%M:%S"),
        ">",
        Fore.YELLOW + "[REQST]",
        ">",
        Style.BRIGHT + Fore.YELLOW + text
    )
    change_output(False)
    # Запись в файл
    executor.submit(write_to_log, LOG_FILES['REQST'], f'{datetime.now().strftime("%d-%m-%Y : %H:%M:%S")} > {text}')

async def error(text):

    change_output(True)
    await aioconsole.aprint(
        Style.BRIGHT + datetime.now().strftime("%d-%m-%Y : %H:%M:%S"),
        ">",
        Fore.RED + "[ERROR]",
        ">",
        Style.BRIGHT + Fore.RED + text
    )
    change_output(False)
    # Запись в файл
    executor.submit(write_to_log, LOG_FILES['ERROR'], f'{datetime.now().strftime("%d-%m-%Y : %H:%M:%S")} > {text}')


# синхронные функции логирования

def sync_debug(text):

    change_output(True)
    print(
        Style.BRIGHT + datetime.now().strftime("%d-%m-%Y : %H:%M:%S"),
        ">",
        Fore.CYAN + "[DEBUG]",
        ">",
        Style.BRIGHT + Fore.CYAN + text
    )
    change_output(False)


def sync_info(text):
    change_output(True)
    print(
        Style.BRIGHT + datetime.now().strftime("%d-%m-%Y : %H:%M:%S"),
        ">",
        Fore.GREEN + "[INFO ]",
        ">",
        Style.BRIGHT + Fore.GREEN + text
    )
    change_output(False)


def sync_error(text):
    change_output(True)
    print(
        Style.BRIGHT + datetime.now().strftime("%d-%m-%Y : %H:%M:%S"),
        ">",
        Fore.RED + "[ERROR]",
        ">",
        Style.BRIGHT + Fore.RED + text
    )
    change_output(False)