import json
import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message, WebAppInfo, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove,
)
from sqlalchemy.ext.asyncio import AsyncSession
from config import REPORT_CHAT_ID, WEBAPP_URL
from bot.states.checklist import ShiftReport

router = Router()
log = logging.getLogger(__name__)

RATING_MAP = {"good": "😎 Отлично", "ok": "😐 Нормально", "bad": "😤 Тяжело"}
SHIFT_MAP = {"day": "Дневная 🌅", "night": "Ночная 🌙"}

DONE_KB = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="✅ Фото отправлены, завершить")]],
    resize_keyboard=True,
)


@router.message(Command("start", "checklist"))
async def cmd_start(message: Message, session: AsyncSession) -> None:
    if WEBAPP_URL:
        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="📋 Открыть чеклист смены", web_app=WebAppInfo(url=WEBAPP_URL))]],
            resize_keyboard=True,
        )
        await message.answer("Нажми кнопку ниже чтобы открыть чеклист смены:", reply_markup=kb)
    else:
        await message.answer("⚙️ WEBAPP_URL не настроен в .env")


@router.message(F.web_app_data)
async def handle_webapp_data(message: Message, session: AsyncSession, state: FSMContext) -> None:
    log.info("Received web_app_data from user %s", message.from_user.id)
    try:
        data = json.loads(message.web_app_data.data)
    except Exception:
        log.exception("Failed to parse webapp data")
        await message.answer("Ошибка при получении данных.")
        return

    report = _build_report(message, data)

    try:
        await message.bot.send_message(REPORT_CHAT_ID, report, parse_mode="HTML")
        log.info("Report sent to chat %s", REPORT_CHAT_ID)
    except Exception as e:
        log.exception("Failed to send report: %s", e)
        await message.answer(f"⚠️ Не удалось отправить отчёт в группу.\nОшибка: {e}")
        return

    photos_total = data.get("photos_total", 0)

    if photos_total > 0:
        await state.set_state(ShiftReport.waiting_for_photos)
        await state.update_data(photos_sent=0)
        await message.answer(
            f"✅ Отчёт отправлен!\n\n"
            f"📸 Теперь отправь {photos_total} фото сюда — я перешлю их в группу.\n"
            f"Когда закончишь — нажми кнопку ниже.",
            reply_markup=DONE_KB,
        )
    else:
        await message.answer("✅ Отчёт отправлен управляющему!", reply_markup=ReplyKeyboardRemove())


@router.message(ShiftReport.waiting_for_photos, F.photo)
async def receive_photo(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    photos_sent = data.get("photos_sent", 0) + 1
    await state.update_data(photos_sent=photos_sent)

    # Пересылаем фото в группу с подписью от сотрудника
    user = message.from_user
    username = f"@{user.username}" if user.username else user.full_name
    caption = f"📸 Фото к отчёту — {username}"
    if message.caption:
        caption += f"\n{message.caption}"

    try:
        await message.bot.send_photo(
            REPORT_CHAT_ID,
            photo=message.photo[-1].file_id,
            caption=caption,
        )
        await message.reply(f"📸 Фото {photos_sent} получено и отправлено в группу.")
    except Exception as e:
        log.exception("Failed to forward photo: %s", e)
        await message.reply(f"⚠️ Не удалось переслать фото: {e}")


@router.message(ShiftReport.waiting_for_photos, F.text == "✅ Фото отправлены, завершить")
async def finish_photos(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    photos_sent = data.get("photos_sent", 0)
    await state.clear()
    await message.answer(
        f"✅ Готово! Отправлено фото: {photos_sent}\nХорошей смены! 👋",
        reply_markup=ReplyKeyboardRemove(),
    )


def _build_report(message: Message, d: dict) -> str:
    shift = SHIFT_MAP.get(d.get("shift", ""), d.get("shift", "—"))
    dt = d.get("datetime", "—")
    cl = d.get("checklist", {})
    tasks = d.get("tasks", {})
    h = d.get("handover", {})
    unchecked = d.get("unchecked", {})
    photos_total = d.get("photos_total", 0)

    user = message.from_user
    username = f"@{user.username}" if user.username else user.full_name

    lines = [
        "📋 <b>ОТЧЁТ О СМЕНЕ — CYBER SPACE</b>",
        "",
        f"👤 Сотрудник: {username} ({user.full_name})",
        f"🕐 Время: {dt}",
        f"🌐 Смена: {shift}",
        "",
        f"<b>Обход:</b> {cl.get('done', 0)}/{cl.get('total', 0)} пунктов ✅",
    ]

    if unchecked:
        lines.append("")
        lines.append("⚠️ <b>Не отмечено:</b>")
        for section, items in unchecked.items():
            lines.append(f"  <b>{section}:</b>")
            for item in items:
                lines.append(f"    • {item}")

    lines += [
        "",
        f"<b>Задачи дня:</b> {tasks.get('done', 0)}/{tasks.get('total', 0)}",
    ]
    if tasks.get("incomplete"):
        lines.append("Не выполнено: " + ", ".join(tasks["incomplete"]))

    lines += [
        "",
        f"📸 Фото: {photos_total}",
        f"💵 Касса: {h.get('cash') or '—'} ₽",
        f"🤝 Принимает: {h.get('next') or '—'}",
        f"⭐ Оценка: {RATING_MAP.get(h.get('rating', ''), '—')}",
    ]

    if h.get("notes"):
        lines += ["", "📝 <b>Заметки:</b>", h["notes"]]

    return "\n".join(lines)
