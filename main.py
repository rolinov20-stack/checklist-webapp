import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import MenuButtonDefault
from config import BOT_TOKEN, WEBAPP_URL
from bot.handlers import main_router
from bot.middlewares.db import DbSessionMiddleware

logging.basicConfig(level=logging.INFO)


async def main() -> None:
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.update.middleware(DbSessionMiddleware())
    dp.include_router(main_router)

    await bot.set_chat_menu_button(menu_button=MenuButtonDefault())
    logging.info("Menu button removed")

    logging.info("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
