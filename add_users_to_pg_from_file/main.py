"""
скрипт открывает файл users.txt, в котором записаны данные юзеров в виде

никнейм  пароль  направление
никнейм направление

если пароль не указан - будет сгенерирован 6-ти значный пароль (первые 6 символов хеша никнейма)
создаёт для них пароли, и записывает в БД в таблицу users (если
такого юзера в БД ещё нет).
Также дописывает в файл added.txt данные, которые попали в БД при работе скрипта 
"""

import os
import hashlib
import psycopg2

users_file = 'users.txt'
added_file = 'added.csv'

def add_user_data(username: str, route: str, password: str, cur):
    """
    Добавляет данные пользователя в базу данных, игнорируя добавление, если username уже существует.
    Если пользователь успешно добавлен, возвращает True, иначе - False.
    """
    try:
        cur.execute(
            """
            INSERT INTO users (username, route, password)
            VALUES (%s, %s, %s)
            ON CONFLICT (username) DO NOTHING
            RETURNING id;
            """,
            (username, route, password)
        )
        if cur.fetchone():
            return True
        else:
            return False
    except Exception as e:
        print(f"Ошибка при добавлении данных: {e}")
        return False

        

def hash_string(input_string):
    hashed_string = hashlib.sha256(input_string.encode()).hexdigest()
    return hashed_string[:6]


with open(users_file, 'r') as file:
    users = file.read().splitlines()

users = list(map(lambda line: line.strip(), users))

unique_users = [] # чтобы не было дубликатов

for user in users:
    data = user.split()
    username = data[0]
    if username in list(map(lambda name: name['username'], unique_users)):
        print(f"юзер {username} уже был найден прежде!")
        continue
    if len(data) > 2: # если есть пароль
        password = data[1]
        route = data[2]
    else: # если же пароль не был указан
        route = data[1]
        password = hash_string(username)
    unique_users.append({"username":username, "route":route, "password":password})
    # print(username, route, password)

conn = psycopg2.connect(dbname='dashboard', user='postgres',
                        password='Mvh54g2y', host='127.0.0.1')
cur = conn.cursor()

# если таблицы нет, сначала создаём её
cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    route TEXT NOT NULL,
    password TEXT NOT NULL
    );
    """)
# записывем уникальных юзеров в БД и в файл
with open(added_file, 'a') as added_file:
    for user in unique_users:
        if add_user_data(user['username'], user['route'], user['password'], cur):
            added_file.write(f"{user['username']},{user['password']},{user['route']}\n")

conn.commit()
cur.close()
conn.close()
