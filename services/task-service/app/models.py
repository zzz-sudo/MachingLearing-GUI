from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


def to_camel(value: str) -> str:
    parts = value.split("_")
    return parts[0] + "".join(part.capitalize() for part in parts[1:])


class ApiModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    WAITING_CONFIRMATION = "waiting_confirmation"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ServiceHealth(ApiModel):
    status: str = "ready"
    service: str = "ml-gui-task-service"
    version: str = "0.1.0"


class ProjectCreate(ApiModel):
    name: str = Field(min_length=1, max_length=120)
    path: str = Field(min_length=1)


class ProjectRecord(ApiModel):
    id: str
    name: str
    path: str
    created_at: datetime
    updated_at: datetime


class JobCreate(ApiModel):
    project_id: str
    title: str = Field(min_length=1, max_length=200)
    message: str | None = None


class JobUpdate(ApiModel):
    status: JobStatus
    progress: int = Field(ge=0, le=100)
    message: str | None = None


class JobRecord(ApiModel):
    id: str
    project_id: str
    title: str
    status: JobStatus
    progress: int
    message: str | None
    created_at: datetime
    updated_at: datetime

