import json
import os

from aiohttp import web

import modules.layout_processor as layouts
import modules.logger as logger
from server_app import state
from server_app.security import parse_structured_data


async def get_layout(request):
    try:
        data = await request.post()
        room = data.get("room")

        constructed = parse_structured_data(data.get("constructed"))
        if constructed is None:
            return web.Response(status=400)
        await logger.debug(
            f"Поступил запрос на сборку лейаута room: {room}\ndata: {constructed}"
        )

        if room not in state.PATH_LAYOUTS:
            if os.path.exists(f"layouts/{room}/paths.json"):
                with open(f"layouts/{room}/paths.json", "r") as file:
                    try:
                        state.PATH_LAYOUTS[room] = json.load(file)
                    except Exception as error:
                        await logger.error(
                            f"Не удалось прочитать файл путей лейаута. Ошибка: {error}"
                        )
                        return web.Response(status=405)
            else:
                await logger.debug(
                    "Невозможно собрать данный лейаут, т.к. нет нужных файлов!"
                )
                return web.Response(status=406)

        zip_layout = await layouts.pack_layout(
            room_name=room, data=constructed, paths=state.PATH_LAYOUTS[room]
        )

        if zip_layout:
            response = web.Response(status=200, body=zip_layout)
            response.content_type = "application/zip"
            response.headers["Content-Disposition"] = 'attachment; filename="archive.zip"'
            await logger.info(f"Успешно собран и отправлен лейаут для рума {room}")
            return response
        await logger.debug("Не удалось собрать zip-архив лейаута!")
        return web.Response(status=404, text="Can't pack layout!")
    except Exception as error:
        await logger.error(f"Ошибка в get_layout: {error}")
