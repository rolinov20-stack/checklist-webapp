import json
import logging
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import REPORT_CHAT_ID, WEBAPP_URL

router = Router()
log = logging.getLogger(__name__)

RATING_MAP = {
    "good": "😎 Отлично",
    "ok": "😐 Нормально",
    "bad": "😤 Тяжело",
}
SHIFT_MAP = {"day": "Дневная 🌅", "night": "Ночная 🌙"}


@router.message(Command("start", "checklist"))
async def cmd_start(message: Message) -> None:
    if WEBAPP_URL:
        builder = InlineKeyboardBuilder()
        builder.button(text="📋 Открыть чеклист смены", web_app=WebAppInfo(url=WEBAPP_URL))
        await message.answer(
            "Нажми кнопку ниже чтобы открыть чеклист смены:",
            reply_markup=builder.as_markup(),
        )
    else:
        await message.answer(
            "⚙️ Бот запущен, но WEBAPP_URL ещё не настроен.\n"
            "Укажи публичный HTTPS адрес в .env и перезапусти бота."
        )


@router.message(lambda m: m.web_app_data is not None)
async def handle_webapp_data(message: Message) -> None:
    try:
        data = json.loads(message.web_app_data.data)
    except Exception:
        log.exception("Failed to parse webapp data")
        await message.answer("Ошибка при получении данных.")
        return

    report = _build_report(message, data)

    # Отправляем отчёт в чат управляющего
    await message.bot.send_message(REPORT_CHAT_ID, report, parse_mode="HTML")

    # Подтверждение администратору
    await message.answer("✅ Отчёт отправлен управляющему!")


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
        f"📋 <b>ОТЧЁТ О СМЕНЕ — CYBER SPACE</b>",
        f"",
        f"👤 Сотрудник: {username} ({user.full_name})",
        f"🕐 Время: {dt}",
        f"🌐 Смена: {shift}",
        f"",
        f"<b>Обход:</b> {cl.get('done',0)}/{cl.get('total',0)} пунктов ✅",
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
        f"<b>Задачи дня:</b> {tasks.get('done',0)}/{tasks.get('total',0)}",
    ]
    if tasks.get("incomplete"):
        lines.append("Не выполнено: " + ", ".join(tasks["incomplete"]))

    lines += [
        "",
        f"📸 Фото: {photos_total}",
        f"💵 Касса: {h.get('cash') or '—'} ₽",
        f"🤝 Принимает: {h.get('next') or '—'}",
        f"⭐ Оценка: {RATING_MAP.get(h.get('rating',''), '—')}",
    ]

    if h.get("notes"):
        lines += ["", f"📝 <b>Заметки:</b>", h["notes"]]

    return "\n".join(lines)
