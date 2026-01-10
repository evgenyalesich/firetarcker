import aiohttp
import asyncio
import json
import os
#
from datetime import datetime, timedelta
#
import modules.logger as logger
from modules.asyncdb_pool import AsyncDatabasePool

path_to_conf = "modules/ds_mailer/config.json"
path_to_ini = "modules/ds_mailer/last_send.ini"

def check_date(user_data):
    str_date = user_data["last_send"]
    username = user_data["username"]
    if str_date and str_date != "0":
        try:
            date = datetime.strptime(str_date, "%Y.%m.%d").date()
        except Exception as error:
            logger.sync_debug(f"[DiscordBot] Не удалось установить дату для юзера {username}, ошибка: {error}")
            return None

        current_date = datetime.now().date()
        days_passed = current_date - date
        if days_passed > timedelta(days=3):
            return {"last_send":str_date, "username":username, "days_passed":days_passed.days}
        else:
            return None



class DiscordNotifier():

    def __init__(self):
        self.token = os.getenv("DS_TOKEN")
        # self.token = "MTE5MjUyMjI4MTAwODc2MzA0MQ.G_9ZU0.MThrkXn9kZlAwdQT4p-ece7JufO1-IR5uXVrdA" # мой бот
        # считываем направлений и id их каналов
        with open(path_to_conf, "r") as conf:
            self.config = json.load(conf)

        # считываем дату последней отправки
        if not os.path.exists(path_to_ini):
            with open(path_to_ini, "w") as file:
                self.last_send = None
        else:
            with open(path_to_ini, "r") as last_date:
                self.last_send = last_date.read()

        self.db_data = {
            "host": os.getenv("DB_HOST"),
            "port": os.getenv("DB_PORT"),
            "user": os.getenv("DB_USER"),
            "password": os.getenv("DB_PASSWORD"),
            "database": os.getenv("DB_DASHBOARD"),
            'min_size': int(os.getenv("DB_MIN_POOL")),
            'max_size': int(os.getenv("DB_MAX_POOL"))
        }
        self.pool = AsyncDatabasePool(**self.db_data)

    async def send_discord_message(self, channel_id, message):
        # Url АПИ
        url = f"https://discord.com/api/v9/channels/{channel_id}/messages"

        payload = {"content": message}

        headers = {
            "Authorization": f"Bot {self.token}",
            "Content-Type": "application/json"
        }

        # для отправки сообщения
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    await logger.debug(f"[DiscordBot] Уведомление в {channel_id} отправлено!")
                else:
                    await logger.debug(f"[DiscordBot] Не удалось отправить сообщение в канал: {channel_id}. Ошибка: {response.status}")
                    # print(response.text)

    async def start_sending(self):
        # делаем выборку данных из БД
        for route in self.config["routes"]:
            # channel_id зависит от направления
            channel_id = self.config["routes"].get(route, None)
            if not channel_id:
                await logger.debug(f"[DiscordBot] Не найден id канала {route}")
                return
            

            # делаем выборку из БД юзеров по данному направлению
            async with await self.pool.acquire() as conn:
                users = await conn.fetch("SELECT username, last_send FROM gamers WHERE LOWER(route) = ($1)", route)
            if not users:
                await logger.debug(f"[DiscordBot] Не найдено записей в БД по направлению: {route}")
                continue

            filtered_users = [f"{'имя пользователя'.upper()[:25].ljust(25)}|{'сколько дней не отправлял'.upper()[:25].ljust(25)}",
                                f"{('-'*25)[:25].ljust(25)}|{('-'*25)[:25].ljust(25)}"
                                ]
            users = list(filter(lambda usr: usr, list(map(lambda user: check_date(user), users))))
            users.sort(key=lambda x: x["days_passed"])

            # если юзеров для рассылки нет - пропускаем
            if not users:
                continue

            for _ in users:
                filtered_users.append(f"{_['username'][:25].ljust(25)}|{str(_['days_passed'])[:25].ljust(25)}")

            if len(filtered_users) > 25:
                for i in range(0, len(filtered_users), 25):
                    output_str = '\n'.join(filtered_users[i:i+25])
                    if i == 0:
                        message = f"!task Эти пользователи давно не отправляли файлы`\n```{output_str}``"
                    else:
                        message = f"```{output_str}```"
                    await self.send_discord_message(channel_id, message)
                    await asyncio.sleep(1)
            else:
                output_str = '\n'.join(filtered_users)
                # Сообщение, которое нужно отправить
                message = f"!task Эти пользователи давно не отправляли файлы`\n```{output_str}``"

                # Отправка сообщения
                await self.send_discord_message(channel_id, message)
                await asyncio.sleep(3)

    async def time_to_send(self):
        if self.last_send:
            try:
                date = datetime.strptime(self.last_send, "%Y.%m.%d").date()
            except Exception as error:
                await logger.error(f"[DiscordBot] Не получилось считать дату последней отправки {self.last_send}, ошибка: {error}")
                return True
            current_date = datetime.now().date()
            days_passed = current_date - date
            if days_passed > timedelta(days=2):
                return True
        else:
            return True
        return False

    async def write_new_date(self):
        current_date = datetime.now().date()
        last_send = current_date.strftime("%Y.%m.%d")
        with open(path_to_ini, "w") as file:
            file.write(last_send)
        self.last_send = last_send
        await logger.debug(f"[DiscordBot] Дата последней рассылки успешно обновлена: {self.last_send}")

    async def calculate_date(self):
        date = datetime.strptime(self.last_send, "%Y.%m.%d").date()
        current_date = datetime.now().date()
        days_passed = current_date - date
        await logger.debug(f"[DiscordBot] До отправки уведомлений осталось дней: {3-days_passed.days}")

    async def main(self):
        # в вечном цикле
        await self.pool.create_pool()
        await logger.info(f"[DiscordBot] Discord-рассыльщик успешно запущен")
        while True:
            try:
                # тут проверка, подошло ли время для запуска рассылки
                if await self.time_to_send():
                    await self.start_sending()
                    await self.write_new_date()
                else:
                    await self.calculate_date()
            except Exception as error:
                await logger.error(f"[DiscordBot] Произошла ошибка: {error}")
            finally:
                # ждём час перед следующей проверкой
                await asyncio.sleep(3600)

def start():
    # Запускаем асинхронный event loop
    bot = DiscordNotifier()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(bot.main())
    
if __name__ == "__main__":
    start()


