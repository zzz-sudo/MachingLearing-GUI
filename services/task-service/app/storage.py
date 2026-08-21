from __future__ import annotations

import json
import os
import sqlite3
import stat
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from app.errors import chart_error, document_result_not_found, file_access_error, job_not_found, project_not_found
from app.models import (
    AssetRecord,
    DatasetColumnSpec,
    DatasetVersion,
    DocumentParseResult,
    JobCreate,
    JobRecord,
    JobStatus,
    JobUpdate,
    ProjectCreate,
    ProjectFileNode,
    ProjectRecord,
    ChartSpecCreate,
    ChartSpecRecord,
    TablePreview,
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
    def __init__(self, data_dir: Path, default_project_dir: Path | None = None) -> None:
        self.data_dir = data_dir
        self.database_path = data_dir / "workspace.sqlite"
        self.default_project_dir = default_project_dir

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

                CREATE TABLE IF NOT EXISTS table_previews (
                    asset_id TEXT PRIMARY KEY,
                    preview_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(asset_id) REFERENCES assets(id)
                );

                CREATE TABLE IF NOT EXISTS dataset_versions (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    source_asset_id TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    parquet_relative_path TEXT NOT NULL,
                    row_count INTEGER NOT NULL,
                    columns_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(source_asset_id, version),
                    FOREIGN KEY(project_id) REFERENCES projects(id),
                    FOREIGN KEY(source_asset_id) REFERENCES assets(id)
                );

                CREATE TABLE IF NOT EXISTS document_results (
                    asset_id TEXT PRIMARY KEY,
                    result_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(asset_id) REFERENCES assets(id)
                );

                CREATE TABLE IF NOT EXISTS chart_specs (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    chart_type TEXT NOT NULL,
                    dataset_id TEXT NOT NULL,
                    model_run_id TEXT,
                    x_column TEXT,
                    y_columns_json TEXT NOT NULL,
                    group_column TEXT,
                    color_column TEXT,
                    filters_json TEXT NOT NULL,
                    options_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    artifact_ids_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(project_id) REFERENCES projects(id),
                    FOREIGN KEY(dataset_id) REFERENCES dataset_versions(id)
                );

                CREATE INDEX IF NOT EXISTS idx_chart_specs_project_id
                ON chart_specs(project_id, updated_at DESC);
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

        configured = os.environ.get("ML_GUI_DEFAULT_PROJECT_DIR")
        projects_dir = Path(configured).expanduser().resolve() if configured else (
            self.default_project_dir if self.default_project_dir is not None else self.data_dir / "projects" / "default"
        )
        projects_dir.parent.mkdir(parents=True, exist_ok=True)
        if projects_dir.exists() and (projects_dir / "project.json").is_file():
            document = json.loads((projects_dir / "project.json").read_text(encoding="utf-8"))
            existing = ProjectRecord.model_validate(document)
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO projects(id, name, path, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (existing.id, existing.name, str(projects_dir), existing.created_at.isoformat(), existing.updated_at.isoformat()),
                )
            return self.get_project(existing.id)
        return self.create_project(ProjectCreate(name="本地数据工作区", path=str(projects_dir)))

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

    def get_job(self, job_id: str) -> JobRecord:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, project_id, title, status, progress, message,
                       created_at, updated_at
                FROM jobs WHERE id = ?
                """,
                (job_id,),
            ).fetchone()
        if row is None:
            raise job_not_found(job_id)
        return self._job_from_row(row)

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

    def get_project_tree(self, project_id: str, include_hidden: bool) -> list[ProjectFileNode]:
        project = self.get_project(project_id)
        project_root = Path(project.path).resolve()
        assets = {asset.relative_path: asset.id for asset in self.list_assets(project_id)}

        def build_nodes(directory: Path) -> list[ProjectFileNode]:
            try:
                entries = sorted(
                    os.scandir(directory),
                    key=lambda entry: (not entry.is_dir(follow_symlinks=False), entry.name.casefold()),
                )
            except OSError as error:
                raise file_access_error(directory, "project_tree", str(error)) from error

            nodes: list[ProjectFileNode] = []
            for entry in entries:
                path = Path(entry.path)
                hidden = self._is_hidden(path)
                if hidden and not include_hidden:
                    continue
                relative_path = path.relative_to(project_root).as_posix()
                is_directory = entry.is_dir(follow_symlinks=False)
                nodes.append(
                    ProjectFileNode(
                        name=entry.name,
                        relative_path=relative_path,
                        kind="directory" if is_directory else "file",
                        hidden=hidden,
                        size=None if is_directory else entry.stat(follow_symlinks=False).st_size,
                        asset_id=assets.get(relative_path),
                        children=build_nodes(path) if is_directory else [],
                    )
                )
            return nodes

        return build_nodes(project_root)

    def resolve_asset_path(self, asset_id: str) -> tuple[AssetRecord, Path]:
        asset = self.get_asset(asset_id)
        project = self.get_project(asset.project_id)
        project_root = Path(project.path).resolve()
        path = (project_root / asset.relative_path).resolve()
        if not path.is_relative_to(project_root) or not path.is_file():
            raise file_access_error(path, "asset_content", "资产文件不存在或已经离开项目目录")
        return asset, path

    def resolve_project_file(self, project_id: str, relative_path: str) -> Path:
        project = self.get_project(project_id)
        project_root = Path(project.path).resolve()
        path = (project_root / relative_path).resolve()
        if not path.is_relative_to(project_root) or not path.is_file():
            raise file_access_error(
                path,
                "project_file_content",
                "文件不存在、不是普通文件，或已经离开项目目录",
            )
        return path

    def get_asset(self, asset_id: str) -> AssetRecord:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, project_id, name, relative_path, media_type, size,
                       sha256, parent_asset_id, created_at
                FROM assets WHERE id = ?
                """,
                (asset_id,),
            ).fetchone()
        if row is None:
            raise project_not_found(asset_id)
        return self._asset_from_row(row)

    def save_preview(self, preview: TablePreview) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO table_previews(asset_id, preview_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(asset_id) DO UPDATE SET
                    preview_json = excluded.preview_json,
                    updated_at = excluded.updated_at
                """,
                (preview.asset_id, preview.model_dump_json(by_alias=True), utc_now().isoformat()),
            )

    def get_preview(self, asset_id: str) -> TablePreview:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT preview_json FROM table_previews WHERE asset_id = ?",
                (asset_id,),
            ).fetchone()
        if row is None:
            raise job_not_found(asset_id)
        return TablePreview.model_validate_json(row["preview_json"])

    def save_document_result(self, result: DocumentParseResult) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO document_results(asset_id, result_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(asset_id) DO UPDATE SET
                    result_json = excluded.result_json,
                    updated_at = excluded.updated_at
                """,
                (result.asset_id, result.model_dump_json(by_alias=True), utc_now().isoformat()),
            )

    def get_document_result(self, asset_id: str) -> DocumentParseResult:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT result_json FROM document_results WHERE asset_id = ?", (asset_id,),
            ).fetchone()
        if row is None:
            raise document_result_not_found(asset_id)
        return DocumentParseResult.model_validate_json(row["result_json"])

    def create_dataset_version(
        self, project_id: str, source_asset_id: str, parquet_relative_path: str,
        row_count: int, columns: list[DatasetColumnSpec],
    ) -> DatasetVersion:
        timestamp = utc_now()
        with self._connect() as connection:
            current = connection.execute(
                "SELECT COALESCE(MAX(version), 0) AS version FROM dataset_versions WHERE source_asset_id = ?",
                (source_asset_id,),
            ).fetchone()
            version = int(current["version"]) + 1
            record = DatasetVersion(
                id=f"dataset-{uuid4().hex}", project_id=project_id,
                source_asset_id=source_asset_id, version=version,
                parquet_relative_path=parquet_relative_path, row_count=row_count,
                columns=columns, created_at=timestamp,
            )
            connection.execute(
                """
                INSERT INTO dataset_versions(
                    id, project_id, source_asset_id, version,
                    parquet_relative_path, row_count, columns_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.id, record.project_id, record.source_asset_id, record.version,
                    record.parquet_relative_path, record.row_count,
                    json.dumps([column.model_dump(by_alias=True) for column in columns], ensure_ascii=False),
                    record.created_at.isoformat(),
                ),
            )
        return record

    def list_dataset_versions(self, project_id: str) -> list[DatasetVersion]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, project_id, source_asset_id, version,
                       parquet_relative_path, row_count, columns_json, created_at
                FROM dataset_versions WHERE project_id = ? ORDER BY created_at DESC
                """,
                (project_id,),
            ).fetchall()
        return [self._dataset_from_row(row) for row in rows]

    def get_dataset_version(self, dataset_id: str) -> DatasetVersion:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, project_id, source_asset_id, version, parquet_relative_path,
                       row_count, columns_json, created_at
                FROM dataset_versions WHERE id = ?
                """,
                (dataset_id,),
            ).fetchone()
        if row is None:
            raise project_not_found(dataset_id)
        return self._dataset_from_row(row)

    def create_chart_spec(self, project_id: str, payload: ChartSpecCreate) -> ChartSpecRecord:
        project = self.get_project(project_id)
        dataset = self.get_dataset_version(payload.dataset_id)
        if dataset.project_id != project.id:
            raise project_not_found(payload.dataset_id)
        available_columns = {column.name for column in dataset.columns}
        requested_columns = [payload.x_column, *payload.y_columns, payload.group_column, payload.color_column]
        invalid_columns = sorted({column for column in requested_columns if column and column not in available_columns})
        if invalid_columns:
            raise chart_error("图形字段不存在于数据集版本", datasetId=payload.dataset_id, columns=invalid_columns)
        if not payload.y_columns:
            raise chart_error("图形至少需要选择一个 Y 轴字段", datasetId=payload.dataset_id)
        timestamp = utc_now()
        record = ChartSpecRecord(
            id=f"chart-{uuid4().hex}",
            project_id=project.id,
            name=payload.name,
            chart_type=payload.chart_type,
            dataset_id=payload.dataset_id,
            model_run_id=payload.model_run_id,
            x_column=payload.x_column,
            y_columns=payload.y_columns,
            group_column=payload.group_column,
            color_column=payload.color_column,
            filters=payload.filters,
            options=payload.options,
            status="draft",
            created_at=timestamp,
            updated_at=timestamp,
        )
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO chart_specs(
                    id, project_id, name, chart_type, dataset_id, model_run_id,
                    x_column, y_columns_json, group_column, color_column,
                    filters_json, options_json, status, artifact_ids_json,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.id, record.project_id, record.name, record.chart_type, record.dataset_id,
                    record.model_run_id, record.x_column, json.dumps(record.y_columns, ensure_ascii=False),
                    record.group_column, record.color_column, json.dumps(record.filters, ensure_ascii=False),
                    json.dumps(record.options, ensure_ascii=False), record.status,
                    json.dumps(record.artifact_ids, ensure_ascii=False), record.created_at.isoformat(),
                    record.updated_at.isoformat(),
                ),
            )
        return record

    def list_chart_specs(self, project_id: str) -> list[ChartSpecRecord]:
        self.get_project(project_id)
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, project_id, name, chart_type, dataset_id, model_run_id,
                       x_column, y_columns_json, group_column, color_column,
                       filters_json, options_json, status, artifact_ids_json,
                       created_at, updated_at
                FROM chart_specs WHERE project_id = ? ORDER BY updated_at DESC
                """,
                (project_id,),
            ).fetchall()
        return [self._chart_from_row(row) for row in rows]

    def get_chart_spec(self, chart_id: str) -> ChartSpecRecord:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, project_id, name, chart_type, dataset_id, model_run_id,
                       x_column, y_columns_json, group_column, color_column,
                       filters_json, options_json, status, artifact_ids_json,
                       created_at, updated_at
                FROM chart_specs WHERE id = ?
                """,
                (chart_id,),
            ).fetchone()
        if row is None:
            raise project_not_found(chart_id)
        return self._chart_from_row(row)

    def update_chart_spec(
        self,
        chart_id: str,
        *,
        status: str,
        artifact_ids: list[str] | None = None,
    ) -> ChartSpecRecord:
        self.get_chart_spec(chart_id)
        timestamp = utc_now().isoformat()
        with self._connect() as connection:
            if artifact_ids is None:
                connection.execute(
                    "UPDATE chart_specs SET status = ?, updated_at = ? WHERE id = ?",
                    (status, timestamp, chart_id),
                )
            else:
                connection.execute(
                    """
                    UPDATE chart_specs
                    SET status = ?, artifact_ids_json = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (status, json.dumps(artifact_ids, ensure_ascii=False), timestamp, chart_id),
                )
        return self.get_chart_spec(chart_id)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @staticmethod
    def _is_hidden(path: Path) -> bool:
        if path.name.startswith("."):
            return True
        if os.name == "nt":
            return bool(path.stat().st_file_attributes & stat.FILE_ATTRIBUTE_HIDDEN)
        return False

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

    @staticmethod
    def _dataset_from_row(row: sqlite3.Row) -> DatasetVersion:
        return DatasetVersion(
            id=row["id"], project_id=row["project_id"],
            source_asset_id=row["source_asset_id"], version=row["version"],
            parquet_relative_path=row["parquet_relative_path"], row_count=row["row_count"],
            columns=[DatasetColumnSpec.model_validate(item) for item in json.loads(row["columns_json"])],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    @staticmethod
    def _chart_from_row(row: sqlite3.Row) -> ChartSpecRecord:
        return ChartSpecRecord(
            id=row["id"],
            project_id=row["project_id"],
            name=row["name"],
            chart_type=row["chart_type"],
            dataset_id=row["dataset_id"],
            model_run_id=row["model_run_id"],
            x_column=row["x_column"],
            y_columns=json.loads(row["y_columns_json"]),
            group_column=row["group_column"],
            color_column=row["color_column"],
            filters=json.loads(row["filters_json"]),
            options=json.loads(row["options_json"]),
            status=row["status"],
            artifact_ids=json.loads(row["artifact_ids_json"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
