import asyncio
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN, WEBAPP_PORT
from bot.handlers import main_router
from bot.middlewares.db import DbSessionMiddleware
from webapp.server import create_app

logging.basicConfig(level=logging.INFO)


async def main() -> None:
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.update.middleware(DbSessionMiddleware())
    dp.include_router(main_router)

    webapp = create_app()
    runner = web.AppRunner(webapp)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", WEBAPP_PORT)
    await site.start()
    logging.info(f"WebApp running on http://0.0.0.0:{WEBAPP_PORT}")

    logging.info("Bot started")
    try:
        await dp.start_polling(bot)
    finally:
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
