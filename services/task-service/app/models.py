from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

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


class AssetRecord(ApiModel):
    id: str
    project_id: str
    name: str
    relative_path: str
    media_type: str
    size: int
    sha256: str
    parent_asset_id: str | None = None
    created_at: datetime


class ProjectFileNode(ApiModel):
    name: str
    relative_path: str
    kind: Literal["directory", "file"]
    hidden: bool
    size: int | None = None
    asset_id: str | None = None
    children: list["ProjectFileNode"] = Field(default_factory=list)


class PreviewColumn(ApiModel):
    name: str
    inferred_type: str
    null_count: int


class TablePreview(ApiModel):
    asset_id: str
    source_name: str
    format: str
    encoding: str | None = None
    sheet_name: str | None = None
    row_count: int
    column_count: int
    columns: list[PreviewColumn]
    rows: list[dict[str, Any]]


class DocumentPage(ApiModel):
    page_number: int
    text: str
    needs_ocr: bool


class DocumentParseResult(ApiModel):
    asset_id: str
    pdf_type: str
    engine: str
    status: str
    page_count: int
    ocr_pages: list[int]
    pages_needing_ocr: list[int]
    markdown_relative_path: str | None = None
    json_relative_path: str
    markdown_preview: str
    pages: list[DocumentPage]


class ImportResult(ApiModel):
    imported_assets: list[AssetRecord]
    preview: TablePreview | None = None
    document: DocumentParseResult | None = None
    extracted_count: int = 0
    warnings: list[str] = Field(default_factory=list)


class DatasetColumnSpec(ApiModel):
    name: str
    data_type: str


class DatasetCreate(ApiModel):
    asset_id: str
    columns: list[DatasetColumnSpec]


class DatasetVersion(ApiModel):
    id: str
    project_id: str
    source_asset_id: str
    version: int
    parquet_relative_path: str
    row_count: int
    columns: list[DatasetColumnSpec]
    created_at: datetime


class AlgorithmParameter(ApiModel):
    id: str
    label: str
    value_type: Literal["integer", "number", "boolean", "select"]
    default: int | float | bool | str
    minimum: int | float | None = None
    maximum: int | float | None = None
    step: int | float | None = None
    options: list[str] = Field(default_factory=list)
    description: str


AlgorithmStatus = Literal["available", "planned", "experimental", "disabled"]


class AlgorithmDefinition(ApiModel):
    id: str
    name: str
    task_type: Literal[
        "classification",
        "regression",
        "clustering",
        "anova",
        "hypothesis_test",
        "exploration",
        "dimensionality_reduction",
        "sequence_regression",
        "sequence_classification",
    ]
    family: str
    description: str
    requires_target: bool = False
    requires_factors: bool = False
    requires_time: bool = False
    supports_gpu: bool = False
    status: AlgorithmStatus = "available"
    dependencies: list[str] = Field(default_factory=list)
    chart_templates: list[str] = Field(default_factory=list)
    parameters: list[AlgorithmParameter] = Field(default_factory=list)


class AlgorithmCatalog(ApiModel):
    version: int = 1
    algorithms: list[AlgorithmDefinition]


ChartType = Literal[
    "line",
    "bar",
    "scatter",
    "histogram",
    "boxplot",
    "heatmap",
    "confusion_matrix",
    "feature_importance",
    "residual",
    "cluster_scatter",
    "anova_effect",
]


ChartValue = str | int | float | bool | list[str]


class ChartSpecCreate(ApiModel):
    name: str = Field(min_length=1, max_length=160)
    chart_type: ChartType
    dataset_id: str
    model_run_id: str | None = None
    x_column: str | None = None
    y_columns: list[str] = Field(default_factory=list)
    group_column: str | None = None
    color_column: str | None = None
    filters: dict[str, ChartValue] = Field(default_factory=dict)
    options: dict[str, ChartValue] = Field(default_factory=dict)


class ChartSpecRecord(ApiModel):
    id: str
    project_id: str
    name: str
    chart_type: ChartType
    dataset_id: str
    model_run_id: str | None = None
    x_column: str | None = None
    y_columns: list[str] = Field(default_factory=list)
    group_column: str | None = None
    color_column: str | None = None
    filters: dict[str, ChartValue] = Field(default_factory=dict)
    options: dict[str, ChartValue] = Field(default_factory=dict)
    status: Literal["draft", "ready", "failed"] = "draft"
    artifact_ids: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class TrainingCreate(ApiModel):
    dataset_id: str
    method: Literal["classification", "regression", "anova", "clustering", "deep-learning"] | None = None
    task_type: str | None = None
    algorithm_id: str | None = None
    target_column: str | None = None
    feature_columns: list[str] = Field(default_factory=list)
    factor_columns: list[str] = Field(default_factory=list)
    time_column: str | None = None
    group_column: str | None = None
    validation_ratio: int = Field(default=20, ge=10, le=40)
    test_ratio: int = Field(default=20, ge=10, le=40)
    random_seed: int = Field(default=42, ge=0, le=2_147_483_647)
    compute_mode: Literal["auto", "cpu", "gpu"] = "auto"
    parameters: dict[str, bool | int | float | str] = Field(default_factory=dict)


class TrainingArtifact(ApiModel):
    kind: str
    relative_path: str
    media_type: str
    description: str


class TrainingResult(ApiModel):
    job_id: str
    method: str
    task_type: str | None = None
    algorithm_id: str | None = None
    status: JobStatus
    target_column: str | None = None
    feature_columns: list[str] = Field(default_factory=list)
    parameters: dict[str, bool | int | float | str] = Field(default_factory=dict)
    metrics: dict[str, float] = Field(default_factory=dict)
    tables: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
    artifacts: list[TrainingArtifact] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    environment: dict[str, str] = Field(default_factory=dict)
    artifact_relative_path: str | None = None
    error_type: str | None = None
    error_message: str | None = None
