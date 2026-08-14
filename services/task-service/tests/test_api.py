from __future__ import annotations

import json
import io
import zipfile
from pathlib import Path
from urllib.parse import quote

from fastapi.testclient import TestClient
from openpyxl import Workbook
import pyarrow.parquet as parquet

from app.main import create_app


def create_test_client(tmp_path: Path) -> TestClient:
    return TestClient(create_app(tmp_path / "service-data"))


def create_project(client: TestClient, path: Path) -> dict[str, object]:
    response = client.post(
        "/api/projects",
        json={"name": "导入测试项目", "path": str(path)},
    )
    assert response.status_code == 201
    return response.json()


def import_file(
    client: TestClient,
    project_id: str,
    filename: str,
    content: bytes,
):
    return client.post(
        f"/api/projects/{project_id}/imports",
        headers={"X-Filename": quote(filename, safe="")},
        content=content,
    )


def test_health_endpoint(tmp_path: Path) -> None:
    with create_test_client(tmp_path) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "service": "ml-gui-task-service",
        "version": "0.1.0",
    }


def test_create_project_keeps_chinese_metadata(tmp_path: Path) -> None:
    project_path = tmp_path / "销售预测项目"

    with create_test_client(tmp_path) as client:
        response = client.post(
            "/api/projects",
            json={"name": "销售预测项目", "path": str(project_path)},
        )
        project_list = client.get("/api/projects")

    assert response.status_code == 201
    assert response.json()["name"] == "销售预测项目"
    assert project_list.json()[0]["name"] == "销售预测项目"
    assert (project_path / "source").is_dir()
    assert (project_path / "models").is_dir()

    project_document = json.loads(
        (project_path / "project.json").read_text(encoding="utf-8")
    )
    assert project_document["name"] == "销售预测项目"


def test_create_and_update_job(tmp_path: Path) -> None:
    project_path = tmp_path / "job-project"

    with create_test_client(tmp_path) as client:
        project = client.post(
            "/api/projects",
            json={"name": "任务测试项目", "path": str(project_path)},
        ).json()
        created_job = client.post(
            "/api/jobs",
            json={
                "projectId": project["id"],
                "title": "训练回归模型",
                "message": "等待本地 Worker",
            },
        )
        job_id = created_job.json()["id"]
        updated_job = client.patch(
            f"/api/jobs/{job_id}",
            json={
                "status": "running",
                "progress": 36,
                "message": "正在训练模型",
            },
        )
        job_list = client.get("/api/jobs", params={"projectId": project["id"]})

    assert created_job.status_code == 201
    assert created_job.json()["status"] == "queued"
    assert updated_job.status_code == 200
    assert updated_job.json()["progress"] == 36
    assert job_list.json()[0]["message"] == "正在训练模型"


def test_missing_project_returns_structured_error(tmp_path: Path) -> None:
    with create_test_client(tmp_path) as client:
        response = client.get("/api/projects/project-missing")

    assert response.status_code == 404
    assert response.json()["errorType"] == "ProjectNotFoundError"
    assert response.json()["operation"] == "project_get"


def test_import_gb18030_csv_preserves_chinese_and_profiles_columns(
    tmp_path: Path,
) -> None:
    content = "城市,销量,备注\n上海,18,正常\n杭州,25,\n".encode("gb18030")
    project_path = tmp_path / "中文导入项目"

    with create_test_client(tmp_path) as client:
        project = create_project(client, project_path)
        response = import_file(client, str(project["id"]), "销售明细.csv", content)
        assets = client.get(f"/api/projects/{project['id']}/assets")

    assert response.status_code == 201
    result = response.json()
    assert result["preview"]["encoding"] == "gb18030"
    assert result["preview"]["rows"][0] == {
        "城市": "上海",
        "销量": "18",
        "备注": "正常",
    }
    assert result["preview"]["columns"][2]["nullCount"] == 1
    assert result["preview"]["columns"][1]["inferredType"] == "integer"
    assert assets.json()[0]["name"] == "销售明细.csv"
    assert (project_path / "source" / "销售明细.csv").read_bytes() == content


def test_import_xlsx_returns_first_sheet_preview(tmp_path: Path) -> None:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "销售数据"
    worksheet.append(["日期", "销量", "是否促销"])
    worksheet.append(["2026-08-01", 32, True])
    worksheet.append(["2026-08-02", 48, False])
    content = io.BytesIO()
    workbook.save(content)
    project_path = tmp_path / "xlsx-project"

    with create_test_client(tmp_path) as client:
        project = create_project(client, project_path)
        response = import_file(
            client,
            str(project["id"]),
            "销售预测.xlsx",
            content.getvalue(),
        )

    assert response.status_code == 201
    preview = response.json()["preview"]
    assert preview["sheetName"] == "销售数据"
    assert preview["rowCount"] == 2
    assert preview["columns"][1]["inferredType"] == "integer"
    assert preview["rows"][1]["销量"] == 48


def test_import_zip_extracts_csv_and_records_asset_relationship(tmp_path: Path) -> None:
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as output:
        output.writestr("数据/区域销售.csv", "区域,金额\n华东,120.5\n".encode("utf-8"))
    project_path = tmp_path / "zip-project"

    with create_test_client(tmp_path) as client:
        project = create_project(client, project_path)
        response = import_file(
            client,
            str(project["id"]),
            "补充数据.zip",
            archive.getvalue(),
        )

    assert response.status_code == 201
    result = response.json()
    assert result["extractedCount"] == 1
    assert len(result["importedAssets"]) == 2
    assert result["importedAssets"][1]["parentAssetId"] == result["importedAssets"][0]["id"]
    assert result["preview"]["rows"][0]["区域"] == "华东"
    assert list((project_path / "extracted").rglob("区域销售.csv"))


def test_import_zip_rejects_path_traversal(tmp_path: Path) -> None:
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("../outside.csv", "name\ninvalid\n")
    project_path = tmp_path / "unsafe-zip-project"

    with create_test_client(tmp_path) as client:
        project = create_project(client, project_path)
        response = import_file(
            client,
            str(project["id"]),
            "unsafe.zip",
            archive.getvalue(),
        )

    assert response.status_code == 400
    assert response.json()["errorType"] == "ArchiveExtractionError"
    assert response.json()["operation"] == "archive_extract"
    assert not (project_path / "outside.csv").exists()


def test_confirm_fields_persists_preview_and_exports_versioned_parquet(tmp_path: Path) -> None:
    fixture = Path(__file__).parent / "fixtures" / "chinese_sales_utf8.csv"
    project_path = tmp_path / "dataset-project"

    with create_test_client(tmp_path) as client:
        project = create_project(client, project_path)
        imported = import_file(client, str(project["id"]), fixture.name, fixture.read_bytes())
        preview = imported.json()["preview"]
        restored = client.get(f"/api/assets/{preview['assetId']}/preview")
        payload = {
            "assetId": preview["assetId"],
            "columns": [
                {"name": "城市", "dataType": "text"},
                {"name": "销量", "dataType": "integer"},
                {"name": "销售额", "dataType": "number"},
                {"name": "是否促销", "dataType": "boolean"},
            ],
        }
        version_one = client.post(f"/api/projects/{project['id']}/datasets", json=payload)
        version_two = client.post(f"/api/projects/{project['id']}/datasets", json=payload)
        downloaded = client.get(f"/api/datasets/{version_one.json()['id']}/parquet")

    assert restored.status_code == 200
    assert restored.json()["rows"][0]["城市"] == "上海"
    assert version_one.status_code == 201
    assert version_one.json()["version"] == 1
    assert version_two.json()["version"] == 2
    assert downloaded.content[:4] == b"PAR1"
    table = parquet.read_table(project_path / version_one.json()["parquetRelativePath"])
    assert table.num_rows == 3
    assert table.column("销量").to_pylist() == [18, 25, 31]
    assert table.column("是否促销").to_pylist() == [True, False, True]
