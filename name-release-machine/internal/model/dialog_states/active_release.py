from aiogram.fsm.state import StatesGroup, State


class ActiveReleaseStates(StatesGroup):
    view_releases = State()
    confirm_dialog = State()
    reject_dialog = State()