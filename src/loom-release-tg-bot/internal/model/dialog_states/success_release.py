from aiogram.fsm.state import StatesGroup, State


class SuccessfulReleasesStates(StatesGroup):
    view_releases = State()
    select_rollback_tag = State()
    confirm_rollback = State()