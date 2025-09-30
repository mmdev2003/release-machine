from pydantic import BaseModel

from internal import model


class CreateReleaseBody(BaseModel):
    service_name: str
    release_tag: str
    status: model.ReleaseStatus
    initiated_by: str
    github_run_id: str
    github_action_link: str
    github_ref: str

class UpdateReleaseBody(BaseModel):
    release_id: int
    status: model.ReleaseStatus = None
    github_run_id: str = None
    github_action_link: str = None