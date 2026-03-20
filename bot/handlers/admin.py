from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.models import Checklist, ChecklistItem
from bot.states.checklist import CreateChecklist
from bot.middlewares.auth import AdminFilter
from bot.keyboards.inline import admin_menu_keyboard

router = Router()
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())


@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    await message.answer("Панель администратора:", reply_markup=admin_menu_keyboard())


@router.callback_query(F.data == "admin_create_checklist")
async def create_checklist_start(call: CallbackQuery, state: FSMContext) -> None:
    await call.message.answer("Введите название нового чеклиста:")
    await state.set_state(CreateChecklist.waiting_for_title)
    await call.answer()


@router.message(CreateChecklist.waiting_for_title)
async def create_checklist_title(message: Message, state: FSMContext) -> None:
    await state.update_data(title=message.text, items=[])
    await message.answer(
        "Название сохранено. Теперь введите пункты чеклиста по одному.\n"
        "Отправьте /done когда закончите."
    )
    await state.set_state(CreateChecklist.waiting_for_items)


@router.message(CreateChecklist.waiting_for_items, Command("done"))
async def create_checklist_done(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    data = await state.get_data()
    if not data.get("items"):
        await message.answer("Добавьте хотя бы один пункт.")
        return

    checklist = Checklist(title=data["title"])
    session.add(checklist)
    await session.flush()

    for order, text in enumerate(data["items"]):
        session.add(ChecklistItem(checklist_id=checklist.id, text=text, order=order))

    await session.commit()
    await state.clear()
    await message.answer(f"Чеклист «{data['title']}» создан с {len(data['items'])} пунктами.")


@router.message(CreateChecklist.waiting_for_items)
async def create_checklist_add_item(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    items: list[str] = data.get("items", [])
    items.append(message.text)
    await state.update_data(items=items)
    await message.answer(f"Пункт {len(items)} добавлен. Продолжайте или /done.")
