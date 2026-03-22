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


def _fmt(val) -> str:
    try:
        return f"{int(val):,}".replace(",", " ")
    except Exception:
        return str(val or 0)


def _build_report(message: Message, d: dict) -> str:
    shift = SHIFT_MAP.get(d.get("shift", ""), d.get("shift", "—"))
    dt = d.get("datetime", "—")
    cl = d.get("checklist", {})
    tasks = d.get("tasks", {})
    h = d.get("handover", {})
    photos_total = d.get("photos_total", 0)
    employee = d.get("employee", "")
    fin = d.get("finance", {})

    user = message.from_user
    tg_name = f"@{user.username}" if user.username else user.full_name
    name_str = employee or tg_name

    lines = [
        "📋 <b>ОТЧЁТ О СМЕНЕ — CYBER SPACE</b>",
        "",
        f"👤 Сотрудник: <b>{name_str}</b>",
        f"🕐 Дата/время: {dt}",
        f"🌐 Смена: {shift}",
        "",
    ]

    # ── Финансовая таблица ──
    if fin:
        cats = [
            ("💻 Компы",      fin.get("pc",    {})),
            ("🎮 Приставки",  fin.get("ps",    {})),
            ("🍔 Бар",        fin.get("bar",   {})),
            ("📦 Прочее",     fin.get("other", {})),
            ("💨 Кальян",     fin.get("kal",   {})),
            ("⭐ Prime",      fin.get("prime", {})),
        ]
        lines.append("💰 <b>ФИНАНСОВЫЙ ОТЧЁТ</b>")
        lines.append("")

        # Таблица по категориям
        for cat_name, cat in cats:
            nal = int(cat.get("nal", 0))
            bn  = int(cat.get("bn",  0))
            tot = nal + bn
            if tot > 0:
                lines.append(f"  <b>{cat_name}</b>")
                lines.append(f"    Нал: {_fmt(nal)} ₽  |  Безнал: {_fmt(bn)} ₽  |  Итого: {_fmt(tot)} ₽")

        total_nal = int(fin.get("total_nal", 0))
        total_bn  = int(fin.get("total_bn",  0))
        total     = int(fin.get("total",     0))

        lines += [
            "",
            f"💵 Итого нал:    <b>{_fmt(total_nal)} ₽</b>",
            f"💳 Итого безнал: <b>{_fmt(total_bn)} ₽</b>",
            f"📊 Общая выручка: <b>{_fmt(total)} ₽</b>",
            "",
        ]

        cash_start   = int(fin.get("cash_start",   0))
        transfer_pre = int(fin.get("transfer_pre", 0))
        transfer_on  = int(fin.get("transfer_on",  0))
        card_total   = int(fin.get("card_total",   0))
        cash_end     = int(fin.get("cash_end",     0))

        if any([cash_start, transfer_pre, transfer_on, card_total, cash_end]):
            lines.append("🏦 <b>КАССА</b>")
            if cash_start:   lines.append(f"  Начало смены:     {_fmt(cash_start)} ₽")
            if transfer_pre: lines.append(f"  Переводы до:      {_fmt(transfer_pre)} ₽")
            if transfer_on:  lines.append(f"  Переводы на смене:{_fmt(transfer_on)} ₽")
            if card_total:   lines.append(f"  На карте итого:   {_fmt(card_total)} ₽")
            if cash_end:     lines.append(f"  Конец смены:      {_fmt(cash_end)} ₽")
            lines.append("")

    # ── Обход ──
    lines += [
        f"✅ <b>Принятие смены:</b> {cl.get('done', 0)}/{cl.get('total', 0)} пунктов",
        f"📋 <b>Задачи дня:</b> {tasks.get('done', 0)}/{tasks.get('total', 0)}",
    ]
    if tasks.get("incomplete"):
        lines.append("  Не выполнено: " + ", ".join(tasks["incomplete"]))

    lines += [
        "",
        f"📸 Фото зон: {photos_total}",
        f"🤝 Принимает: {h.get('next') or '—'}",
        f"⭐ Оценка: {RATING_MAP.get(h.get('rating', ''), '—')}",
    ]

    if h.get("notes"):
        lines += ["", "📝 <b>Заметки:</b>", h["notes"]]

    return "\n".join(lines)
