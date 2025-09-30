from typing import Any

from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, ShowMode
from opentelemetry.trace import SpanKind, Status, StatusCode

from internal import interface, model


class ActiveReleaseService(interface.IActiveReleaseService):
    def __init__(
            self,
            tel: interface.ITelemetry,
            release_service: interface.IReleaseService,
            github_client: interface.IGitHubClient,
            required_approve_list: list[str]
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.release_service = release_service
        self.github_client = github_client
        self.required_approve_list = required_approve_list

    async def handle_navigate_release(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        """Обработка навигации между релизами"""
        with self.tracer.start_as_current_span(
                "ActiveReleaseService.handle_navigate_release",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                current_index = dialog_manager.dialog_data.get("current_index", 0)
                releases_list = dialog_manager.dialog_data.get("releases_list", [])

                # Определяем направление навигации
                if button.widget_id == "prev_release":
                    new_index = max(0, current_index - 1)
                else:  # next_release
                    new_index = min(len(releases_list) - 1, current_index + 1)

                if new_index == current_index:
                    await callback.answer()
                    return

                # Обновляем индекс
                dialog_manager.dialog_data["current_index"] = new_index

                self.logger.info("Навигация по релизам")

                await callback.answer()
                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await callback.answer("❌ Ошибка навигации", show_alert=True)
                raise err

    async def handle_refresh(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        """Обработка обновления списка релизов"""
        with self.tracer.start_as_current_span(
                "ActiveReleaseService.handle_refresh",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                dialog_manager.show_mode = ShowMode.EDIT

                # Сбрасываем индекс к первому релизу
                dialog_manager.dialog_data["current_index"] = 0

                # Очищаем кешированные данные
                dialog_manager.dialog_data.pop("releases_list", None)
                dialog_manager.dialog_data.pop("current_release", None)

                await callback.answer("✅ Данные обновлены")

                self.logger.info("Обновление списка релизов")
                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await callback.answer("❌ Ошибка при обновлении", show_alert=True)
                raise err

    async def handle_back_to_menu(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        """Обработка возврата в главное меню"""
        with self.tracer.start_as_current_span(
                "ActiveReleaseService.handle_back_to_menu",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                dialog_manager.show_mode = ShowMode.EDIT

                # Очищаем данные диалога
                dialog_manager.dialog_data.clear()

                await dialog_manager.start(model.MainMenuStates.main_menu)

                self.logger.info("Возврат в главное меню")
                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await callback.answer("❌ Ошибка", show_alert=True)
                raise err

    async def handle_confirm_yes(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        """Обработка подтверждения релиза"""
        with self.tracer.start_as_current_span(
                "ActiveReleaseService.handle_confirm_yes",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                dialog_manager.show_mode = ShowMode.EDIT

                current_release = dialog_manager.dialog_data.get("current_release", {})
                release_id = current_release.get("id")
                approver_username = callback.from_user.username

                if not release_id:
                    raise ValueError("Release ID not found in dialog data")

                # Получаем текущий список подтверждений
                current_approved_list = current_release.get("approved_list", [])

                if approver_username not in self.required_approve_list:
                    await callback.answer("У вас нет прав на подтверждение", show_alert=True)
                    return

                if approver_username in current_approved_list:
                    await callback.answer("Вы уже подтвердили", show_alert=True)
                    return


                if len(current_approved_list) == len(self.required_approve_list) - 1:
                    # Все подтверждения собраны - переводим в статус "тест пройден" и запускаем деплой
                    current_approved_list.append(approver_username)

                    await self.release_service.update_release(
                        release_id=release_id,
                        status=model.ReleaseStatus.MANUAL_TEST_PASSED,
                        approved_list=current_approved_list,
                    )

                    # Запускаем GitHub workflow для деплоя на продакшн
                    await self.github_client.trigger_workflow(
                        owner="Name",
                        repo=current_release["service_name"],
                        workflow_id="on-approve-manual-testing.yaml.yml",
                        inputs={
                            "release_id": str(release_id),
                            "release_tag": current_release["release_tag"],
                        },
                    )

                    await callback.answer(
                        "✅ Релиз подтвержден!\n"
                        "🚀 Все подтверждения собраны - запускается деплой на продакшн!",
                        show_alert=True
                    )

                    await self._remove_current_release_from_list(dialog_manager)

                    self.logger.info(
                        f"Релиз {release_id} полностью подтвержден пользователем {approver_username}. "
                        f"Запущен деплой на продакшн"
                    )
                else:
                    current_approved_list.append(approver_username)

                    await self.release_service.update_release(
                        release_id=release_id,
                        approved_list=current_approved_list,
                    )

                    await callback.answer(f"✅ Ваше подтверждение учтено!", show_alert=True)

                    self.logger.info(f"Релиз {release_id} подтвержден пользователем {approver_username}.")

                # Обновляем данные текущего релиза в dialog_data
                current_release["approved_list"] = current_approved_list
                dialog_manager.dialog_data["current_release"] = current_release

                await dialog_manager.switch_to(model.ActiveReleaseStates.view_releases)

                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await callback.answer("❌ Ошибка при подтверждении релиза", show_alert=True)
                raise err

    async def handle_reject_yes(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        """Обработка отклонения релиза"""
        with self.tracer.start_as_current_span(
                "ActiveReleaseService.handle_reject_yes",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                dialog_manager.show_mode = ShowMode.EDIT

                current_release = dialog_manager.dialog_data.get("current_release", {})
                release_id = current_release.get("id")
                rejector_username = callback.from_user.username

                if not release_id:
                    raise ValueError("Release ID not found in dialog data")

                if rejector_username not in self.required_approve_list:
                    await callback.answer("У вас нет прав на подтверждение", show_alert=True)
                    return

                # Обновляем статус релиза на отклонен
                await self.release_service.update_release(
                    release_id=release_id,
                    status=model.ReleaseStatus.MANUAL_TEST_FAILED
                )

                await callback.answer("❌ Релиз отклонен", show_alert=True)

                self.logger.info(f"Релиз {release_id} отклонен пользователем {rejector_username}")

                # Удаляем текущий релиз из списка и переходим к следующему
                await self._remove_current_release_from_list(dialog_manager)

                await dialog_manager.switch_to(model.ActiveReleaseStates.view_releases)

                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await callback.answer("❌ Ошибка при отклонении релиза", show_alert=True)
                raise err

    async def _remove_current_release_from_list(self, dialog_manager: DialogManager) -> None:
        """Удаляет текущий релиз из списка и корректирует индекс"""
        releases_list = dialog_manager.dialog_data.get("releases_list", [])
        current_index = dialog_manager.dialog_data.get("current_index", 0)

        if releases_list and current_index < len(releases_list):
            releases_list.pop(current_index)

            # Корректируем индекс если нужно
            if current_index >= len(releases_list) and releases_list:
                dialog_manager.dialog_data["current_index"] = len(releases_list) - 1
            elif not releases_list:
                dialog_manager.dialog_data["current_index"] = 0

            # Очищаем данные текущего релиза
            dialog_manager.dialog_data.pop("current_release", None)