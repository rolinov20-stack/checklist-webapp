from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from db.models import Checklist, ChecklistItem


def main_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Чеклисты", callback_data="checklists")
    builder.adjust(1)
    return builder.as_markup()


def admin_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Создать чеклист", callback_data="admin_create_checklist")
    builder.button(text="Список чеклистов", callback_data="admin_list_checklists")
    builder.adjust(1)
    return builder.as_markup()


def checklists_keyboard(checklists: list[Checklist]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for cl in checklists:
        builder.button(text=cl.title, callback_data=f"start_checklist:{cl.id}")
    builder.adjust(1)
    return builder.as_markup()


def checklist_items_keyboard(
    session_id: int,
    items: list[ChecklistItem],
    checked_ids: set[int],
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for item in items:
        mark = "✅" if item.id in checked_ids else "⬜"
        builder.button(
            text=f"{mark} {item.text}",
            callback_data=f"toggle:{session_id}:{item.id}",
        )
    builder.button(text="Завершить чеклист", callback_data=f"complete:{session_id}")
    builder.adjust(1)
    return builder.as_markup()
