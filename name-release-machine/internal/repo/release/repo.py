import json

from opentelemetry.trace import SpanKind, Status, StatusCode

from internal.repo.release.query import *
from internal import model
from internal import interface


class ReleaseRepo(interface.IReleaseRepo):
    def __init__(self, tel: interface.ITelemetry, db: interface.IDB):
        self.db = db
        self.tracer = tel.tracer()

    async def create_release(
            self,
            service_name: str,
            release_tag: str,
            status: model.ReleaseStatus,
            initiated_by: str,
            github_run_id: str,
            github_action_link: str,
            github_ref: str
    ) -> int:
        with self.tracer.start_as_current_span(
                "ReleaseRepo.create_release",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                args = {
                    "service_name": service_name,
                    "release_tag": release_tag,
                    "status": status.value,
                    "initiated_by": initiated_by,
                    "github_run_id": github_run_id,
                    "github_action_link": github_action_link,
                    "github_ref": github_ref,
                }
                release_id = await self.db.insert(create_release, args)

                span.set_status(StatusCode.OK)
                return release_id

            except Exception as err:
                span.record_exception(err)
                span.set_status(StatusCode.ERROR, str(err))
                raise err

    async def update_release(
            self,
            release_id: int,
            status: model.ReleaseStatus = None,
            github_run_id: str = None,
            github_action_link: str = None,
            rollback_to_tag: str = None,
            approved_list: list[str] = None,
    ) -> None:
        with self.tracer.start_as_current_span(
                "ReleaseRepo.update_release",
                kind=SpanKind.INTERNAL,
                attributes={
                    "release_id": release_id,
                }
        ) as span:
            try:
                update_fields = []
                args: dict = {'release_id': release_id}

                if status is not None:
                    update_fields.append("status = :status")
                    args['status'] = status.value

                if github_run_id is not None:
                    update_fields.append("github_run_id = :github_run_id")
                    args['github_run_id'] = github_run_id

                if github_action_link is not None:
                    update_fields.append("github_action_link = :github_action_link")
                    args['github_action_link'] = github_action_link

                if rollback_to_tag is not None:
                    update_fields.append("rollback_to_tag = :rollback_to_tag")
                    args['rollback_to_tag'] = rollback_to_tag

                if approved_list is not None:
                    update_fields.append("approved_list = :approved_list")
                    args['approved_list'] = json.dumps(approved_list, ensure_ascii=False)

                if not update_fields:
                    span.set_status(Status(StatusCode.OK))
                    return

                query = f"""
                UPDATE releases 
                SET {', '.join(update_fields)}
                WHERE id = :release_id;
                """

                await self.db.update(query, args)
                span.set_status(StatusCode.OK)

            except Exception as err:
                span.record_exception(err)
                span.set_status(StatusCode.ERROR, str(err))
                raise

    async def get_active_release(self) -> list[model.Release]:
        with self.tracer.start_as_current_span(
                "ReleaseRepo.get_active_release",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                rows = await self.db.select(get_active_releases, {})
                if rows:
                    rows = model.Release.serialize(rows)
                span.set_status(StatusCode.OK)
                return rows

            except Exception as err:
                span.record_exception(err)
                span.set_status(StatusCode.ERROR, str(err))
                raise

    async def get_release_by_id(self, release_id: int) -> list[model.Release]:
        with self.tracer.start_as_current_span(
                "ReleaseRepo.get_release_by_id",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                args = {'release_id': release_id}
                rows = await self.db.select(get_active_releases, args)
                if rows:
                    rows = model.Release.serialize(rows)
                span.set_status(StatusCode.OK)
                return rows

            except Exception as err:
                span.record_exception(err)
                span.set_status(StatusCode.ERROR, str(err))
                raise

    async def get_successful_releases(self) -> list[model.Release]:
        with self.tracer.start_as_current_span(
                "ReleaseRepo.get_successful_releases",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                rows = await self.db.select(get_successful_releases, {})
                if rows:
                    rows = model.Release.serialize(rows)
                span.set_status(StatusCode.OK)
                return rows

            except Exception as err:
                span.record_exception(err)
                span.set_status(StatusCode.ERROR, str(err))
                raise

    async def get_failed_releases(self) -> list[model.Release]:
        with self.tracer.start_as_current_span(
                "ReleaseRepo.get_failed_releases",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                rows = await self.db.select(get_failed_releases, {})
                if rows:
                    rows = model.Release.serialize(rows)
                span.set_status(StatusCode.OK)
                return rows

            except Exception as err:
                span.record_exception(err)
                span.set_status(StatusCode.ERROR, str(err))
                raise