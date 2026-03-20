from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.models import Checklist, ChecklistSession, ChecklistItem, SessionCheck
from bot.keyboards.inline import checklists_keyboard, checklist_items_keyboard
from datetime import datetime

router = Router()


@router.callback_query(F.data == "checklists")
async def show_checklists(call: CallbackQuery, session: AsyncSession) -> None:
    result = await session.execute(
        select(Checklist).where(Checklist.is_active == True).order_by(Checklist.id)
    )
    checklists = result.scalars().all()
    if not checklists:
        await call.message.edit_text("Нет доступных чеклистов.")
        return
    await call.message.edit_text(
        "Выберите чеклист:", reply_markup=checklists_keyboard(checklists)
    )


@router.callback_query(F.data.startswith("start_checklist:"))
async def start_checklist(call: CallbackQuery, session: AsyncSession) -> None:
    checklist_id = int(call.data.split(":")[1])
    checklist = await session.get(Checklist, checklist_id)
    if not checklist:
        await call.answer("Чеклист не найден.", show_alert=True)
        return

    checklist_session = ChecklistSession(
        checklist_id=checklist_id,
        user_id=call.from_user.id,
        username=call.from_user.username,
    )
    session.add(checklist_session)
    await session.flush()

    result = await session.execute(
        select(ChecklistItem)
        .where(ChecklistItem.checklist_id == checklist_id)
        .order_by(ChecklistItem.order)
    )
    items = result.scalars().all()
    for item in items:
        session.add(SessionCheck(session_id=checklist_session.id, item_id=item.id))

    await session.commit()
    await call.message.edit_text(
        f"*{checklist.title}*\n\nОтмечайте выполненные пункты:",
        reply_markup=checklist_items_keyboard(checklist_session.id, items, []),
        parse_mode="Markdown",
    )


@router.callback_query(F.data.startswith("toggle:"))
async def toggle_item(call: CallbackQuery, session: AsyncSession) -> None:
    _, session_id, item_id = call.data.split(":")
    session_id, item_id = int(session_id), int(item_id)

    check_result = await session.execute(
        select(SessionCheck).where(
            SessionCheck.session_id == session_id,
            SessionCheck.item_id == item_id,
        )
    )
    check = check_result.scalar_one_or_none()
    if check:
        check.is_checked = not check.is_checked
        await session.commit()

    checklist_session = await session.get(ChecklistSession, session_id)
    items_result = await session.execute(
        select(ChecklistItem)
        .where(ChecklistItem.checklist_id == checklist_session.checklist_id)
        .order_by(ChecklistItem.order)
    )
    items = items_result.scalars().all()

    checks_result = await session.execute(
        select(SessionCheck).where(SessionCheck.session_id == session_id)
    )
    checked_ids = {c.item_id for c in checks_result.scalars().all() if c.is_checked}

    await call.message.edit_reply_markup(
        reply_markup=checklist_items_keyboard(session_id, items, checked_ids)
    )
    await call.answer()


@router.callback_query(F.data.startswith("complete:"))
async def complete_checklist(call: CallbackQuery, session: AsyncSession) -> None:
    session_id = int(call.data.split(":")[1])
    checklist_session = await session.get(ChecklistSession, session_id)
    if checklist_session:
        checklist_session.is_completed = True
        checklist_session.completed_at = datetime.now()
        await session.commit()
    await call.message.edit_text("Чеклист завершён! Хорошая работа.")
