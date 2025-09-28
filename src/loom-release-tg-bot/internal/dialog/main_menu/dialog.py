from aiogram_dialog import Window, Dialog
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.kbd import Button, Column
from sulguk import SULGUK_PARSE_MODE

from internal import interface, model


class MainMenuDialog(interface.IMainMenuDialog):
    def __init__(
            self,
            tel: interface.ITelemetry,
            main_menu_service: interface.IMainMenuService,
            main_menu_getter: interface.IMainMenuGetter,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.main_menu_service = main_menu_service
        self.main_menu_getter = main_menu_getter

    def get_dialog(self) -> Dialog:
        return Dialog(
            self.get_main_menu_window(),
        )

    def get_main_menu_window(self) -> Window:
        return Window(
            Format("🤖 <b>Release Bot</b><br><br>"),
            Format("👋 Привет, {name}!<br><br>"),
            Const("Я помогу тебе отслеживать и управлять релизами.<br>"),
            Const("Здесь ты можешь просматривать активные релизы и управлять ими.<br><br>"),
            Const("Выбери действие:"),
            Column(
                Button(
                    Const("🚀 Активные релизы"),
                    id="active_releases",
                    on_click=self.main_menu_service.handle_go_to_active_releases,
                ),
                Button(
                    Const("✅ Успешные релизы"),
                    id="successful_releases",
                    on_click=self.main_menu_service.handle_go_to_successful_releases,
                ),
                Button(
                    Const("❌ Провальные релизы"),
                    id="failed_releases",
                    on_click=self.main_menu_service.handle_go_to_failed_releases,
                ),
            ),
            state=model.MainMenuStates.main_menu,
            getter=self.main_menu_getter.get_main_menu_data,
            parse_mode=SULGUK_PARSE_MODE,
        )