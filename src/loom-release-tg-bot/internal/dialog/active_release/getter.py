from datetime import datetime, timezone
from aiogram_dialog import DialogManager
from opentelemetry.trace import SpanKind, Status, StatusCode

from internal import interface, model


class ActiveReleaseGetter(interface.IActiveReleaseGetter):
    def __init__(
            self,
            tel: interface.ITelemetry,
            release_repo: interface.IReleaseRepo
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.release_repo = release_repo

    async def get_releases_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        with self.tracer.start_as_current_span(
                "ActiveReleaseGetter.get_releases_data",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                # Получаем активные релизы
                releases = await self.release_repo.get_active_release()

                if not releases:
                    return {
                        "has_releases": False,
                        "total_count": 0,
                        "period_text": "",
                    }

                # Сохраняем список для навигации
                releases_list = []
                for release in releases:
                    releases_list.append(release.to_dict())

                dialog_manager.dialog_data["releases_list"] = releases_list

                # Устанавливаем текущий индекс (0 если не был установлен)
                if "current_index" not in dialog_manager.dialog_data:
                    dialog_manager.dialog_data["current_index"] = 0

                current_index = dialog_manager.dialog_data["current_index"]

                # Корректируем индекс если он выходит за границы
                if current_index >= len(releases):
                    current_index = len(releases) - 1
                    dialog_manager.dialog_data["current_index"] = current_index

                current_release = releases[current_index]

                # Рассчитываем время ожидания
                waiting_time = self._calculate_waiting_time(current_release.created_at)

                # Определяем период
                period_text = self._get_period_text(releases)

                # Форматируем данные релиза
                release_data = {
                    "service_name": current_release.service_name,
                    "current_tag": current_release.release_tag,
                    "old_tag": current_release.rollback_to_tag,
                    "status_text": self._format_status(current_release.status),
                    "initiated_by": current_release.initiated_by,
                    "created_at_formatted": self._format_datetime(current_release.created_at),
                    "has_github_link": bool(current_release.github_action_link),
                    "github_action_link": current_release.github_action_link,
                    "waiting_time": waiting_time,
                    "has_waiting_time": bool(waiting_time),
                }

                data = {
                    "has_releases": True,
                    "total_count": len(releases),
                    "period_text": period_text,
                    "current_index": current_index + 1,
                    "has_prev": current_index > 0,
                    "has_next": current_index < len(releases) - 1,
                    "has_rollback": bool(current_release.rollback_to_tag),
                    "show_manual_testing_buttons": current_release.status == model.ReleaseStatus.MANUAL_TESTING,
                    **release_data,
                }

                # Сохраняем данные текущего релиза для диалогов подтверждения/отклонения
                dialog_manager.dialog_data["current_release"] = current_release.to_dict()

                self.logger.info("Список активных релизов загружен")

                span.set_status(Status(StatusCode.OK))
                return data

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise err

    async def get_confirm_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        with self.tracer.start_as_current_span(
                "ActiveReleaseGetter.get_confirm_data",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                current_release = dialog_manager.dialog_data.get("current_release", {})

                data = {
                    "service_name": current_release.get("service_name", "Неизвестно"),
                    "release_tag": current_release.get("release_tag", "Неизвестно"),
                    "initiated_by": current_release.get("initiated_by", "Неизвестно"),
                }

                span.set_status(Status(StatusCode.OK))
                return data

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise err

    async def get_reject_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        with self.tracer.start_as_current_span(
                "ActiveReleaseGetter.get_reject_data",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                current_release = dialog_manager.dialog_data.get("current_release", {})

                data = {
                    "service_name": current_release.get("service_name", "Неизвестно"),
                    "release_tag": current_release.get("release_tag", "Неизвестно"),
                    "initiated_by": current_release.get("initiated_by", "Неизвестно"),
                }

                span.set_status(Status(StatusCode.OK))
                return data

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise err

    def _format_status(self, status: model.ReleaseStatus) -> str:
        """Форматирует статус релиза с эмодзи"""
        status_map = {
            model.ReleaseStatus.INITIATED: "🔵 Инициирован",
            model.ReleaseStatus.BUILDING: "🔨 Сборка",
            model.ReleaseStatus.STAGING_FAILED: "❌ Ошибка на stage",
            model.ReleaseStatus.MANUAL_TESTING: "🧪 Ручное тестирование",
            model.ReleaseStatus.MANUAL_TEST_PASSED: "✅ Тест пройден",
            model.ReleaseStatus.MANUAL_TEST_FAILED: "❌ Отклонен",
            model.ReleaseStatus.DEPLOYING: "🚀 Деплой",
            model.ReleaseStatus.DEPLOYED: "✅ Задеплоен",
            model.ReleaseStatus.PRODUCTION_FAILED: "❌ Ошибка на prod",
        }
        return status_map.get(status, status.value if hasattr(status, 'value') else str(status))

    def _format_datetime(self, dt: datetime) -> str:
        """Форматирует дату и время"""
        if not dt:
            return "—"

        try:
            if isinstance(dt, str):
                dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))

            return dt.strftime("%d.%m.%Y %H:%M")
        except Exception:
            return str(dt)

    def _calculate_waiting_time(self, created_at: datetime) -> str:
        """Вычисляет время ожидания релиза"""
        if not created_at:
            return ""

        try:
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))

            now = datetime.now(timezone.utc)

            # Убеждаемся что datetime имеет timezone info
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)

            delta = now - created_at
            total_seconds = delta.total_seconds()

            if total_seconds < 60:
                return "только что"

            minutes = int(total_seconds / 60)
            if minutes < 60:
                return f"{minutes} мин"

            hours = int(total_seconds / 3600)
            if hours < 24:
                if hours == 1:
                    return "1 час"
                elif hours < 5:
                    return f"{hours} часа"
                else:
                    return f"{hours} часов"

            days = int(total_seconds / (3600 * 24))
            if days == 1:
                return "1 день"
            elif days < 5:
                return f"{days} дня"
            else:
                return f"{days} дней"

        except Exception:
            return ""

    def _get_period_text(self, releases: list) -> str:
        """Определяет период активных релизов"""
        if not releases:
            return "Нет данных"

        # Находим самый старый релиз
        oldest_date = None
        for release in releases:
            if hasattr(release, 'created_at') and release.created_at:
                if oldest_date is None or release.created_at < oldest_date:
                    oldest_date = release.created_at

        if not oldest_date:
            return "Сегодня"

        try:
            if isinstance(oldest_date, str):
                oldest_date = datetime.fromisoformat(oldest_date.replace('Z', '+00:00'))

            now = datetime.now(timezone.utc)
            if oldest_date.tzinfo is None:
                oldest_date = oldest_date.replace(tzinfo=timezone.utc)

            delta = now - oldest_date
            hours = delta.total_seconds() / 3600

            if hours < 24:
                return "За сегодня"
            elif hours < 48:
                return "За последние 2 дня"
            elif hours < 168:  # неделя
                return "За неделю"
            else:
                return "За месяц"

        except Exception:
            return "За последнее время"

    def _calculate_waiting_hours(self, created_at: datetime) -> int:
        """Вычисляет количество часов ожидания"""
        if not created_at:
            return 0

        try:
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))

            now = datetime.now(timezone.utc)
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)

            delta = now - created_at
            return int(delta.total_seconds() / 3600)
        except Exception:
            return 0