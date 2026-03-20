from aiogram import Router
from bot.handlers.webapp import router as webapp_router
from bot.handlers.admin import router as admin_router

main_router = Router()
main_router.include_router(webapp_router)
main_router.include_router(admin_router)
