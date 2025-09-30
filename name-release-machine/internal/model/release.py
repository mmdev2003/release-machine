import json
from datetime import datetime
from dataclasses import dataclass
from enum import Enum


class ReleaseStatus(Enum):
    INITIATED = "initiated"

    STAGE_BUILDING = "stage_building"
    STAGE_BUILDING_FAILED = "stage_building_failed"
    STAGE_TEST_ROLLBACK = "stage_test_rollback"
    STAGE_ROLLBACK_TEST_FAILED = "stage_test_rollback_failed"

    MANUAL_TESTING = "manual_testing"
    MANUAL_TEST_PASSED = "manual_test_passed"
    MANUAL_TEST_FAILED = "manual_test_failed"

    DEPLOYING = "deploying"
    DEPLOYED = "deployed"
    PRODUCTION_FAILED = "production_failed"

    ROLLBACK = "production_rollback"
    ROLLBACK_FAILED = "rollback_failed"
    ROLLBACK_DONE = "rollback_done"


@dataclass
class Release:
    id: int
    service_name: str
    release_tag: str
    rollback_to_tag: str
    status: ReleaseStatus

    initiated_by: str
    github_run_id: str
    github_action_link: str
    github_ref: str
    approved_list: list[str]

    created_at: datetime
    started_at: datetime
    completed_at: datetime

    @classmethod
    def serialize(cls, rows) -> list:
        return [
            cls(
                id=row.id,
                service_name=row.service_name,
                release_tag=row.release_tag,
                rollback_to_tag=row.rollback_to_tag,
                status=ReleaseStatus(row.status),
                initiated_by=row.initiated_by,
                github_run_id=row.github_run_id,
                github_action_link=row.github_action_link,
                github_ref=row.github_ref,
                approved_list=json.loads(row.approved_list),
                created_at=row.created_at,
                started_at=row.started_at,
                completed_at=row.completed_at,
            )
            for row in rows
        ]

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'service_name': self.service_name,
            'release_tag': self.release_tag,
            'rollback_to_tag': self.rollback_to_tag,
            'status': self.status.value,  # assuming ReleaseStatus is an enum
            'initiated_by': self.initiated_by,
            'github_run_id': self.github_run_id,
            'github_action_link': self.github_action_link,
            'github_ref': self.github_ref,
            'approved_list': self.approved_list,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
        }