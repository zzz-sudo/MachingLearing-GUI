from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from app.errors import file_access_error, job_not_found, project_not_found
from app.models import (
    AssetRecord,
    JobCreate,
    JobRecord,
    JobStatus,
    JobUpdate,
    ProjectCreate,
    ProjectRecord,
)

PROJECT_DIRECTORIES = (
    "source",
    "extracted",
    "datasets",
    "documents",
    "models",
    "predictions",
    "reports",
    "logs",
    "temp",
)


def utc_now() -> datetime:
    return datetime.now(UTC)


class WorkspaceStore:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.database_path = data_dir / "workspace.sqlite"

    def initialize(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    path TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL,
                    progress INTEGER NOT NULL,
                    message TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(project_id) REFERENCES projects(id)
                );

                CREATE INDEX IF NOT EXISTS idx_jobs_project_id
                ON jobs(project_id, updated_at DESC);

                CREATE TABLE IF NOT EXISTS assets (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    relative_path TEXT NOT NULL,
                    media_type TEXT NOT NULL,
                    size INTEGER NOT NULL,
                    sha256 TEXT NOT NULL,
                    parent_asset_id TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(project_id) REFERENCES projects(id),
                    FOREIGN KEY(parent_asset_id) REFERENCES assets(id)
                );

                CREATE INDEX IF NOT EXISTS idx_assets_project_id
                ON assets(project_id, created_at DESC);
                """
            )

    def create_project(self, payload: ProjectCreate) -> ProjectRecord:
        project_path = Path(payload.path).expanduser().resolve()
        project_id = f"project-{uuid4().hex}"
        timestamp = utc_now()

        try:
            project_path.mkdir(parents=True, exist_ok=False)
            for directory in PROJECT_DIRECTORIES:
                (project_path / directory).mkdir()

            project_document = {
                "id": project_id,
                "name": payload.name,
                "path": str(project_path),
                "createdAt": timestamp.isoformat(),
                "updatedAt": timestamp.isoformat(),
            }
            (project_path / "project.json").write_text(
                json.dumps(project_document, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as error:
            raise file_access_error(
                project_path,
                "project_create",
                str(error),
            ) from error

        record = ProjectRecord(
            id=project_id,
            name=payload.name,
            path=str(project_path),
            created_at=timestamp,
            updated_at=timestamp,
        )

        try:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO projects(id, name, path, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        record.id,
                        record.name,
                        record.path,
                        record.created_at.isoformat(),
                        record.updated_at.isoformat(),
                    ),
                )
        except sqlite3.Error as error:
            raise file_access_error(
                self.database_path,
                "project_create",
                str(error),
            ) from error

        return record

    def list_projects(self) -> list[ProjectRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, name, path, created_at, updated_at
                FROM projects
                ORDER BY updated_at DESC
                """
            ).fetchall()
        return [self._project_from_row(row) for row in rows]

    def get_or_create_default_project(self) -> ProjectRecord:
        projects = self.list_projects()
        if projects:
            return projects[0]

        projects_dir = self.data_dir / "projects"
        projects_dir.mkdir(parents=True, exist_ok=True)
        return self.create_project(
            ProjectCreate(name="本地数据工作区", path=str(projects_dir / "default"))
        )

    def get_project(self, project_id: str) -> ProjectRecord:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, name, path, created_at, updated_at
                FROM projects
                WHERE id = ?
                """,
                (project_id,),
            ).fetchone()

        if row is None:
            raise project_not_found(project_id)
        return self._project_from_row(row)

    def create_job(self, payload: JobCreate) -> JobRecord:
        self.get_project(payload.project_id)
        timestamp = utc_now()
        record = JobRecord(
            id=f"job-{uuid4().hex}",
            project_id=payload.project_id,
            title=payload.title,
            status=JobStatus.QUEUED,
            progress=0,
            message=payload.message,
            created_at=timestamp,
            updated_at=timestamp,
        )

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO jobs(
                    id, project_id, title, status, progress, message,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    record.project_id,
                    record.title,
                    record.status.value,
                    record.progress,
                    record.message,
                    record.created_at.isoformat(),
                    record.updated_at.isoformat(),
                ),
            )
        return record

    def list_jobs(self, project_id: str | None = None) -> list[JobRecord]:
        query = """
            SELECT id, project_id, title, status, progress, message,
                   created_at, updated_at
            FROM jobs
        """
        parameters: tuple[str, ...] = ()
        if project_id:
            query += " WHERE project_id = ?"
            parameters = (project_id,)
        query += " ORDER BY updated_at DESC"

        with self._connect() as connection:
            rows = connection.execute(query, parameters).fetchall()
        return [self._job_from_row(row) for row in rows]

    def update_job(self, job_id: str, payload: JobUpdate) -> JobRecord:
        timestamp = utc_now()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE jobs
                SET status = ?, progress = ?, message = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    payload.status.value,
                    payload.progress,
                    payload.message,
                    timestamp.isoformat(),
                    job_id,
                ),
            )
            if cursor.rowcount == 0:
                raise job_not_found(job_id)

            row = connection.execute(
                """
                SELECT id, project_id, title, status, progress, message,
                       created_at, updated_at
                FROM jobs
                WHERE id = ?
                """,
                (job_id,),
            ).fetchone()

        if row is None:
            raise job_not_found(job_id)
        return self._job_from_row(row)

    def create_asset(
        self,
        project_id: str,
        name: str,
        relative_path: str,
        media_type: str,
        size: int,
        sha256: str,
        parent_asset_id: str | None = None,
    ) -> AssetRecord:
        self.get_project(project_id)
        record = AssetRecord(
            id=f"asset-{uuid4().hex}",
            project_id=project_id,
            name=name,
            relative_path=relative_path,
            media_type=media_type,
            size=size,
            sha256=sha256,
            parent_asset_id=parent_asset_id,
            created_at=utc_now(),
        )
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO assets(
                    id, project_id, name, relative_path, media_type, size,
                    sha256, parent_asset_id, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    record.project_id,
                    record.name,
                    record.relative_path,
                    record.media_type,
                    record.size,
                    record.sha256,
                    record.parent_asset_id,
                    record.created_at.isoformat(),
                ),
            )
        return record

    def list_assets(self, project_id: str) -> list[AssetRecord]:
        self.get_project(project_id)
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, project_id, name, relative_path, media_type, size,
                       sha256, parent_asset_id, created_at
                FROM assets
                WHERE project_id = ?
                ORDER BY created_at DESC
                """,
                (project_id,),
            ).fetchall()
        return [self._asset_from_row(row) for row in rows]

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @staticmethod
    def _project_from_row(row: sqlite3.Row) -> ProjectRecord:
        return ProjectRecord(
            id=row["id"],
            name=row["name"],
            path=row["path"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    @staticmethod
    def _job_from_row(row: sqlite3.Row) -> JobRecord:
        return JobRecord(
            id=row["id"],
            project_id=row["project_id"],
            title=row["title"],
            status=JobStatus(row["status"]),
            progress=row["progress"],
            message=row["message"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    @staticmethod
    def _asset_from_row(row: sqlite3.Row) -> AssetRecord:
        return AssetRecord(
            id=row["id"],
            project_id=row["project_id"],
            name=row["name"],
            relative_path=row["relative_path"],
            media_type=row["media_type"],
            size=row["size"],
            sha256=row["sha256"],
            parent_asset_id=row["parent_asset_id"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )
