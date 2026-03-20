from aiohttp import web
from pathlib import Path

WEBAPP_DIR = Path(__file__).parent


async def index(request: web.Request) -> web.FileResponse:
    return web.FileResponse(WEBAPP_DIR / "index.html")


def create_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/", index)
    app.router.add_static("/static", WEBAPP_DIR, show_index=False)
    return app
