from opentelemetry.trace import Status, StatusCode, SpanKind
from typing import Dict, Optional

from internal import interface
from pkg.client.client import AsyncHTTPClient


class GitHubClient(interface.IGitHubClient):
    def __init__(
            self,
            tel: interface.ITelemetry,
            token: str,
            host: str = "api.github.com",
            port: int = 443
    ):
        self.client = AsyncHTTPClient(
            host,
            port,
            prefix="",
            use_tracing=True,
            use_https=True,
        )
        self.tracer = tel.tracer()
        self.token = token
        self._default_headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def trigger_workflow(
            self,
            owner: str,
            repo: str,
            workflow_id: str,
            ref: str = "main",
            inputs: Optional[Dict[str, str]] = None
    ) -> None:
        with self.tracer.start_as_current_span(
                "GitHubClient.trigger_workflow",
                kind=SpanKind.CLIENT,
                attributes={
                    "owner": owner,
                    "repo": repo,
                    "workflow_id": workflow_id,
                    "ref": ref
                }
        ) as span:
            try:
                body = {
                    "ref": ref,
                    "inputs": inputs or {}
                }

                url = f"/repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches"
                await self.client.post(url, json=body, headers=self._default_headers)

                span.set_status(Status(StatusCode.OK))

            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise



