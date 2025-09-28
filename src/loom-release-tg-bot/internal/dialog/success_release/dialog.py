from aiogram import F
from aiogram_dialog import Window, Dialog
from aiogram_dialog.widgets.text import Const, Format, Case, Multi
from aiogram_dialog.widgets.kbd import Button, Column, Row, Select, Group
from sulguk import SULGUK_PARSE_MODE

from internal import interface, model


class SuccessfulReleasesDialog(interface.ISuccessfulReleasesDialog):
    def __init__(
            self,
            tel: interface.ITelemetry,
            successful_releases_service: interface.ISuccessfulReleasesService,
            successful_releases_getter: interface.ISuccessfulReleasesGetter,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.successful_releases_service = successful_releases_service
        self.successful_releases_getter = successful_releases_getter

    def get_dialog(self) -> Dialog:
        return Dialog(
            self.get_view_successful_releases_window(),
            self.get_select_rollback_tag_window(),
            self.get_confirm_rollback_window(),
        )

    def get_view_successful_releases_window(self) -> Window:
        return Window(
            Multi(
                Const("✅ <b>Успешные релизы</b><br><br>"),
                Case(
                    {
                        True: Multi(
                            Format("📦 <b>{service_name}</b><br>"),
                            Case(
                                {
                                    False: Format("🏷️ <b>Tag:</b> <code>{current_tag}</code><br>"),
                                    True: Multi(
                                        Format("🏷️ <b>Текущий tag:</b> <code>{current_tag}</code><br>"),
                                        Format("🏷️ <b>Прошлый tag:</b> <code>{old_tag}</code><br>"),
                                    ),
                                },
                                selector="has_rollback"
                            ),
                            Format("🔄 <b>Статус:</b> {status_text}<br>"),
                            Format("👤 <b>Инициатор:</b> <code>{initiated_by}</code><br>"),
                            Format("📅 <b>Создан:</b> <code>{created_at_formatted}</code><br>"),
                            Format("🚀 <b>Задеплоен:</b> <code>{deployed_at_formatted}</code><br>"),
                            Format("🔗 <b>GitHub Action:</b> <a href='{github_action_link}'>Открыть</a><br>"),
                        ),
                        False: Multi(
                            Const("📭 <b>Нет успешных релизов</b><br><br>"),
                            Const("💡 <i>Успешные релизы появятся здесь после завершения деплоя</i>"),
                        ),
                    },
                    selector="has_releases"
                ),
                sep="",
            ),

            # Навигация по релизам
            Row(
                Button(
                    Const("⬅️ Пред"),
                    id="prev_release",
                    on_click=self.successful_releases_service.handle_navigate_release,
                    when="has_prev",
                ),
                Button(
                    Format("📊 {current_index}/{total_count}"),
                    id="counter",
                    on_click=lambda c, b, d: c.answer("📈 Навигация по релизам"),
                    when="has_releases",
                ),
                Button(
                    Const("➡️ След"),
                    id="next_release",
                    on_click=self.successful_releases_service.handle_navigate_release,
                    when="has_next",
                ),
                when="has_releases",
            ),

            Column(
                Button(
                    Const("⏪ Откатить"),
                    id="rollback_release",
                    on_click=self.successful_releases_service.handle_rollback_click,
                    when=~F["has_rollback"],
                ),
                Button(
                    Const("🔄 Обновить"),
                    id="refresh",
                    on_click=self.successful_releases_service.handle_refresh,
                    when="has_releases",
                ),
                Button(
                    Const("⬅️ Назад в меню"),
                    id="back_to_menu",
                    on_click=self.successful_releases_service.handle_back_to_menu,
                ),
            ),

            state=model.SuccessfulReleasesStates.view_releases,
            getter=self.successful_releases_getter.get_releases_data,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_select_rollback_tag_window(self) -> Window:
        return Window(
            Case(
                {
                    True: Multi(
                        Const("⏪ <b>Выбор tag для отката</b><br><br>"),
                        Format("📦 <b>Сервис:</b> <code>{service_name}</code><br>"),
                        Format("🏷️ <b>Текущий tag:</b> <code>{current_tag}</code><br><br>"),
                        Const("📋 <b>Выберите версию для отката:</b><br>"),
                        Const("<i>Показаны последние 3 успешных релиза</i>"),
                        sep="",
                    ),
                    False: Const("Нет релизов для отката")
                },
                selector="has_releases"
            ),

            Group(
                Select(
                    Format("🏷️ {item[release_tag]} ({item[deployed_at_formatted]})"),
                    id="rollback_releases_select",
                    items="available_releases",
                    item_id_getter=lambda item: str(item["id"]),
                    on_click=self.successful_releases_service.handle_tag_selected,
                ),
                width=1,
                when="has_releases"
            ),

            Button(
                Const("Назад"),
                id="cancel_rollback",
                on_click=lambda c, b, d: d.switch_to(model.SuccessfulReleasesStates.view_releases),
            ),

            state=model.SuccessfulReleasesStates.select_rollback_tag,
            getter=self.successful_releases_getter.get_rollback_tags_data,
            parse_mode=SULGUK_PARSE_MODE,
        )

    def get_confirm_rollback_window(self) -> Window:
        return Window(
            Case(
                {
                    "not_run": Multi(
                        Const("⚠️ <b>Подтверждение отката</b><br><br>"),
                        Const("❗ <b>ВНИМАНИЕ!</b> Вы собираетесь откатить релиз!<br><br>"),
                        Format("📦 <b>Сервис:</b> <code>{service_name}</code><br>"),
                        Format("🏷️ <b>Текущий tag:</b> <code>{current_tag}</code><br>"),
                        Format("⏪ <b>Откатить на tag:</b> <code>{target_tag}</code><br>"),
                        Format("📅 <b>Дата деплоя выбранной версии:</b> <code>{target_deployed_at}</code><br><br>"),
                        Const("⚠️ <i>Это действие приведет к откату сервиса на выбранную версию.</i><br>"),
                        Const("⚠️ <i>Убедитесь, что откат действительно необходим!</i>"),
                        sep="",
                    ),
                    "run": Const("Выполняю откат"),
                    "done":  Multi(
                        Format("📦 <b>Сервис:</b> <code>{service_name}</code><br>"),
                        Format("🏷️ <b>Прошлый tag:</b> <code>{old_tag}</code><br>"),
                        Format("⏪ <b>Новый tag:</b> <code>{new_tag}</code><br>"),
                    ),
                    "error": Const("Ошибка отката")
                },
                selector="rollback_status"
            ),

            Row(
                Button(
                    Const("✅ Да, откатить"),
                    id="confirm_rollback_yes",
                    on_click=self.successful_releases_service.handle_confirm_rollback,
                    when=~F["has_run_rollback"]
                ),
                Button(
                    Const("Назад"),
                    id="cancel_rollback_confirm",
                    on_click=lambda c, b, d: d.switch_to(model.SuccessfulReleasesStates.view_releases),
                    when=~F["has_run_rollback"]
                ),
            ),

            state=model.SuccessfulReleasesStates.confirm_rollback,
            getter=self.successful_releases_getter.get_rollback_confirm_data,
            parse_mode=SULGUK_PARSE_MODE,
        )
