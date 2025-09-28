from aiogram.fsm.state import StatesGroup, State


class FailedReleasesStates(StatesGroup):
    view_releases = State()
    select_rollback_tag = State()
    confirm_rollback = State()