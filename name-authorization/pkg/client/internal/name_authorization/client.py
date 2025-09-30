from opentelemetry.trace import Status, StatusCode, SpanKind

from internal import model
from internal import interface
from pkg.client.client import AsyncHTTPClient


class NameAuthorizationClient(interface.INameAuthorizationClient):
    def __init__(
            self,
            tel: interface.ITelemetry,
            host: str,
            port: int
    ):
        logger = tel.logger()
        self.client = AsyncHTTPClient(
            host,
            port,
            prefix="/api/authorization",
            use_tracing=True,
            logger=logger,
        )
        self.tracer = tel.tracer()

    async def authorization(self, account_id: int) -> model.JWTTokens:
        with self.tracer.start_as_current_span(
                "NameAuthorizationClient.authorization",
                kind=SpanKind.CLIENT,
                attributes={
                    "account_id": account_id
                }
        ) as span:
            try:
                body = {
                    "account_id": account_id
                }
                response = await self.client.post("/", json=body)
                json_response = response.json()

                span.set_status(Status(StatusCode.OK))
                return model.JWTTokens(**json_response)
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    async def check_authorization(self, access_token: str) -> model.AuthorizationData:
        with self.tracer.start_as_current_span(
                "NameAuthorizationClient.check_authorization",
                kind=SpanKind.CLIENT,
        ) as span:
            try:
                cookies = {"Access-Token": access_token}
                response = await self.client.get("/check", cookies=cookies)
                json_response = response.json()

                span.set_status(Status(StatusCode.OK))
                return model.AuthorizationData(**json_response)
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise