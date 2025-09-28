from fastapi.responses import JSONResponse
from opentelemetry.trace import SpanKind, Status, StatusCode

from internal import interface
from internal.controller.http.handler.release.model import CreateReleaseBody, UpdateReleaseBody


class ReleaseController(interface.IReleaseController):
    def __init__(
            self,
            tel: interface.ITelemetry,
            release_service: interface.IReleaseService
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.release_service = release_service

    async def create_release(self, body: CreateReleaseBody) -> JSONResponse:
        with self.tracer.start_as_current_span(
                "ReleaseController.create_release",
                kind=SpanKind.INTERNAL,
                attributes={
                    "service_name": body.service_name,
                    "release_tag": body.release_tag,
                    "initiated_by": body.initiated_by,
                    "github_run_id": body.github_run_id,
                }
        ) as span:
            try:
                self.logger.info(f"Получен запрос на создание релиза для сервиса {body.service_name}")

                release_id = await self.release_service.create_release(
                    service_name=body.service_name,
                    release_tag=body.release_tag,
                    initiated_by=body.initiated_by,
                    github_run_id=body.github_run_id,
                    github_action_link=body.github_action_link,
                    github_ref=body.github_ref
                )

                self.logger.info(f"Релиз успешно создан с ID {release_id}")

                span.set_status(Status(StatusCode.OK))
                return JSONResponse(
                    status_code=201,
                    content={"release_id": release_id}
                )

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))

                raise err

    async def update_release(self, body: UpdateReleaseBody) -> JSONResponse:
        with self.tracer.start_as_current_span(
                "ReleaseController.update_release",
                kind=SpanKind.INTERNAL,
                attributes={
                    "release_id": body.release_id,
                    "new_status": body.status.value,
                }
        ) as span:
            try:
                self.logger.info(f"Получен запрос на обновление релиза {body.release_id}")

                await self.release_service.update_release(
                    release_id=body.release_id,
                    status=body.status,
                    github_run_id=body.github_run_id,
                    github_action_link=body.github_action_link,
                )

                self.logger.info(f"Статус релиза {body.release_id} успешно обновлен на {body.status.value}")

                span.set_status(Status(StatusCode.OK))
                return JSONResponse(
                    status_code=200,
                    content={"status": "success"},
                )

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise