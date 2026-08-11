from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class WorkspaceServiceError(Exception):
    error_type: str
    message: str
    operation: str
    status_code: int = 400
    recoverable: bool = True
    details: dict[str, Any] = field(default_factory=dict)

    def as_response(self) -> dict[str, Any]:
        return {
            "errorType": self.error_type,
            "message": self.message,
            "operation": self.operation,
            "recoverable": self.recoverable,
            "details": self.details,
        }


def file_access_error(path: Path, operation: str, reason: str) -> WorkspaceServiceError:
    return WorkspaceServiceError(
        error_type="FileAccessError",
        message=f"无法访问项目路径: {path}",
        operation=operation,
        status_code=400,
        details={"path": str(path), "reason": reason},
    )


def project_not_found(project_id: str) -> WorkspaceServiceError:
    return WorkspaceServiceError(
        error_type="ProjectNotFoundError",
        message=f"未找到项目: {project_id}",
        operation="project_get",
        status_code=404,
        details={"projectId": project_id},
    )


def job_not_found(job_id: str) -> WorkspaceServiceError:
    return WorkspaceServiceError(
        error_type="JobNotFoundError",
        message=f"未找到任务: {job_id}",
        operation="job_update",
        status_code=404,
        details={"jobId": job_id},
    )

