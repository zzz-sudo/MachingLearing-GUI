from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Literal
from urllib.parse import quote, unquote

from fastapi import APIRouter, Header, Query, Request
from fastapi.responses import FileResponse

from app.datasets import DatasetService
from app.algorithm_catalog import get_algorithm_catalog
from app.documents import DocumentExportService
from app.importer import FileImporter
from app.models import (
    AssetRecord,
    AlgorithmCatalog,
    DatasetCreate,
    DatasetVersion,
    DocumentParseResult,
    ImportResult,
    JobCreate,
    JobRecord,
    JobUpdate,
    ProjectFileNode,
    ProjectCreate,
    ProjectRecord,
    ServiceHealth,
    TablePreview,
    TrainingCreate,
    TrainingResult,
)
from app.storage import WorkspaceStore
from app.training import TrainingService

router = APIRouter()


def get_store(request: Request) -> WorkspaceStore:
    return request.app.state.workspace_store


def get_training_service(request: Request) -> TrainingService:
    return request.app.state.training_service


@router.get("/health", response_model=ServiceHealth)
def get_health() -> ServiceHealth:
    return ServiceHealth()


@router.get("/algorithms", response_model=AlgorithmCatalog)
def get_algorithms() -> AlgorithmCatalog:
    return get_algorithm_catalog()


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


@router.get("/projects/{project_id}/tree", response_model=list[ProjectFileNode])
def get_project_tree(
    project_id: str,
    request: Request,
    include_hidden: bool = Query(default=True, alias="includeHidden"),
) -> list[ProjectFileNode]:
    return get_store(request).get_project_tree(project_id, include_hidden)


@router.get("/projects/{project_id}/files/content")
def get_project_file_content(
    project_id: str,
    request: Request,
    relative_path: str = Query(alias="path"),
) -> FileResponse:
    path = get_store(request).resolve_project_file(project_id, relative_path)
    media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return FileResponse(
        path,
        media_type=media_type,
        headers={"Content-Disposition": f"inline; filename*=UTF-8''{quote(path.name)}"},
    )


@router.get("/assets/{asset_id}/content")
def get_asset_content(asset_id: str, request: Request) -> FileResponse:
    asset, path = get_store(request).resolve_asset_path(asset_id)
    return FileResponse(
        path,
        media_type=asset.media_type,
        headers={"Content-Disposition": f"inline; filename*=UTF-8''{quote(asset.name)}"},
    )


@router.get("/assets/{asset_id}/preview", response_model=TablePreview)
def get_asset_preview(asset_id: str, request: Request) -> TablePreview:
    return get_store(request).get_preview(asset_id)


@router.get("/assets/{asset_id}/document", response_model=DocumentParseResult)
def get_document_result(asset_id: str, request: Request) -> DocumentParseResult:
    return get_store(request).get_document_result(asset_id)


@router.get("/assets/{asset_id}/document/export")
def export_document_result(
    asset_id: str,
    request: Request,
    output_format: Literal["docx", "xlsx", "md", "txt"] = Query(alias="format"),
) -> FileResponse:
    path, media_type = DocumentExportService(get_store(request)).export(asset_id, output_format)
    return FileResponse(path, media_type=media_type, filename=path.name)


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


@router.post("/projects/{project_id}/training", response_model=TrainingResult, status_code=202)
def create_training(project_id: str, payload: TrainingCreate, request: Request) -> TrainingResult:
    return get_training_service(request).start(project_id, payload)


@router.get("/jobs/{job_id}/training-result", response_model=TrainingResult)
def get_training_result(job_id: str, request: Request) -> TrainingResult:
    return get_training_service(request).get_result(job_id)
    AssetRecord,
    ImportResult,
