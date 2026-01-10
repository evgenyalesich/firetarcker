import asyncpg
import asyncio
import inspect

# класс для реализации пула соединений
class AsyncDatabasePool:
    def __init__(self, **params):
        self._pool = None
        self._params = params

    async def create_pool(self):
        # # Раскомментить этот код для отслеживания инфы о пулах и event loop
        # frame = inspect.currentframe()
        # caller_frame = frame.f_back
        # info = inspect.getframeinfo(caller_frame)
        # loop = asyncio.get_running_loop()
        # print(f"Создание пула в event loop id_{id(loop)}, self.id_{id(self)}, вызвано из {info.function} в {info.filename}:{info.lineno}")

        if self._pool is None:
            self._pool = await asyncpg.create_pool(**self._params)
        return self._pool

    async def close_pool(self):
        if self._pool:
            await self._pool.close()
            self._pool = None

    async def acquire(self):
        # Убедитесь, что пул был создан
        if self._pool is None:
            raise Exception("Connection pool has not been created")
        
        # # Расширенная информация о текущем event loop и вызове acquire
        # loop = asyncio.get_running_loop()
        # frame = inspect.currentframe()
        # caller_frame = frame.f_back
        # info = inspect.getframeinfo(caller_frame)
        # print(f"Получение соединения из пула в event loop id_{id(loop)}, self.id_{id(self)}, вызвано из {info.function} в {info.filename}:{info.lineno}")

        return self._pool.acquire()