from aiogram.fsm.state import State, StatesGroup


class CreateChecklist(StatesGroup):
    waiting_for_title = State()
    waiting_for_items = State()
