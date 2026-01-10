from aiohttp import web

import modules.logger as logger
from server_app import state
from server_app.security import get_real_ip, is_rate_limited


async def print_request(app, handler):
    async def middleware_handler(request):
        handler_name = handler.keywords["handler"].__name__

        if handler_name in state.BLACK_LIST:
            return await handler(request)

        if request.path.startswith("/static/"):
            return await handler(request)

        real_ip = get_real_ip(request)
        if is_rate_limited(real_ip, request.path):
            await logger.debug(f"Rate limit for {real_ip} on {request.path}")
            return web.Response(status=429)

        await logger.request(
            f"Request from {real_ip} with method {request.method} and path {request.path}"
        )

        return await handler(request)

    return middleware_handler
