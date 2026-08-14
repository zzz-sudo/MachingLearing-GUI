from __future__ import annotations

from pathlib import Path
from urllib.parse import unquote

from fastapi import APIRouter, Header, Query, Request
from fastapi.responses import FileResponse

from app.datasets import DatasetService
from app.importer import FileImporter
from app.models import (
    AssetRecord,
    DatasetCreate,
    DatasetVersion,
    ImportResult,
    JobCreate,
    JobRecord,
    JobUpdate,
    ProjectCreate,
    ProjectRecord,
    ServiceHealth,
    TablePreview,
)
from app.storage import WorkspaceStore

router = APIRouter()


def get_store(request: Request) -> WorkspaceStore:
    return request.app.state.workspace_store


@router.get("/health", response_model=ServiceHealth)
def get_health() -> ServiceHealth:
    return ServiceHealth()


@router.get("/projects", response_model=list[ProjectRecord])
def list_projects(request: Request) -> list[ProjectRecord]:
    return get_store(request).list_projects()


@router.post("/projects", response_model=ProjectRecord, status_code=201)
def create_project(payload: ProjectCreate, request: Request) -> ProjectRecord:
    return get_store(request).create_project(payload)


@router.post("/projects/default", response_model=ProjectRecord)
def get_default_project(request: Request) -> ProjectRecord:
    return get_store(request).get_or_create_default_project()


@router.get("/projects/{project_id}", response_model=ProjectRecord)
def get_project(project_id: str, request: Request) -> ProjectRecord:
    return get_store(request).get_project(project_id)


@router.get("/projects/{project_id}/assets", response_model=list[AssetRecord])
def list_assets(project_id: str, request: Request) -> list[AssetRecord]:
    return get_store(request).list_assets(project_id)


@router.get("/assets/{asset_id}/preview", response_model=TablePreview)
def get_asset_preview(asset_id: str, request: Request) -> TablePreview:
    return get_store(request).get_preview(asset_id)


@router.get("/projects/{project_id}/datasets", response_model=list[DatasetVersion])
def list_datasets(project_id: str, request: Request) -> list[DatasetVersion]:
    return get_store(request).list_dataset_versions(project_id)


@router.post("/projects/{project_id}/datasets", response_model=DatasetVersion, status_code=201)
def create_dataset(project_id: str, payload: DatasetCreate, request: Request) -> DatasetVersion:
    return DatasetService(get_store(request)).create(project_id, payload)


@router.get("/datasets/{dataset_id}/parquet")
def download_parquet(dataset_id: str, request: Request) -> FileResponse:
    store = get_store(request)
    dataset = store.get_dataset_version(dataset_id)
    project = store.get_project(dataset.project_id)
    path = Path(project.path) / dataset.parquet_relative_path
    return FileResponse(path, media_type="application/vnd.apache.parquet", filename=path.name)


@router.post(
    "/projects/{project_id}/imports",
    response_model=ImportResult,
    status_code=201,
)
async def import_file(
    project_id: str,
    request: Request,
    x_filename: str = Header(alias="X-Filename"),
) -> ImportResult:
    content = await request.body()
    return FileImporter(get_store(request)).import_bytes(
        project_id=project_id,
        filename=unquote(x_filename),
        content=content,
    )


@router.get("/jobs", response_model=list[JobRecord])
def list_jobs(
    request: Request,
    project_id: str | None = Query(default=None, alias="projectId"),
) -> list[JobRecord]:
    return get_store(request).list_jobs(project_id)


@router.post("/jobs", response_model=JobRecord, status_code=201)
def create_job(payload: JobCreate, request: Request) -> JobRecord:
    return get_store(request).create_job(payload)


@router.patch("/jobs/{job_id}", response_model=JobRecord)
def update_job(job_id: str, payload: JobUpdate, request: Request) -> JobRecord:
    return get_store(request).update_job(job_id, payload)
    AssetRecord,
    ImportResult,
