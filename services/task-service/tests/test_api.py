from __future__ import annotations

import io
import json
import time
import zipfile
from pathlib import Path
from urllib.parse import quote

from fastapi.testclient import TestClient
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


def create_dataset_from_csv(
    client: TestClient,
    project_id: str,
    fixture: Path,
    columns: list[dict[str, str]],
) -> dict[str, object]:
    imported = import_file(client, project_id, fixture.name, fixture.read_bytes())
    assert imported.status_code == 201
    asset_id = imported.json()["preview"]["assetId"]
    response = client.post(
        f"/api/projects/{project_id}/datasets",
        json={"assetId": asset_id, "columns": columns},
    )
    assert response.status_code == 201
    return response.json()


def wait_for_training(
    client: TestClient,
    project_id: str,
    job_id: str,
    timeout_seconds: float = 120.0,
) -> dict[str, object]:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        jobs = client.get("/api/jobs", params={"projectId": project_id}).json()
        job = next(item for item in jobs if item["id"] == job_id)
        if job["status"] in {"succeeded", "failed", "cancelled"}:
            result = client.get(f"/api/jobs/{job_id}/training-result")
            assert result.status_code == 200
            return result.json()
        time.sleep(0.25)
    raise AssertionError(f"训练任务超时: {job_id}")


def wait_for_chart(client: TestClient, job_id: str, timeout_seconds: float = 60.0) -> dict[str, object]:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        jobs = client.get("/api/jobs").json()
        job = next(item for item in jobs if item["id"] == job_id)
        if job["status"] in {"succeeded", "failed", "cancelled"}:
            result = client.get(f"/api/jobs/{job_id}/chart-result")
            assert result.status_code == 200
            return result.json()
        time.sleep(0.25)
    raise AssertionError(f"图形任务超时: {job_id}")


def test_default_project_uses_repository_workspace(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("ML_GUI_DEFAULT_PROJECT_DIR", raising=False)
    monkeypatch.setenv("ML_GUI_DATA_DIR", str(tmp_path / "service-data"))
    expected = Path(__file__).resolve().parents[3] / "workspace" / "default"
    with TestClient(create_app()) as client:
        response = client.post("/api/projects/default")

    assert response.status_code == 200
    assert Path(response.json()["path"]).resolve() == expected.resolve()
    assert (expected / "source").is_dir()


def test_health_endpoint(tmp_path: Path) -> None:
    with create_test_client(tmp_path) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "service": "ml-gui-task-service",
        "version": "0.1.0",
    }


def test_training_api_dispatches_multiple_algorithm_runners(tmp_path: Path) -> None:
    project_path = tmp_path / "algorithm-api-project"
    classification_fixture = Path(__file__).parent / "fixtures" / "algorithms" / "classification_fixture.csv"
    clustering_fixture = Path(__file__).parent / "fixtures" / "algorithms" / "clustering_fixture.csv"
    anova_fixture = Path(__file__).parent / "fixtures" / "algorithms" / "anova_multi_factor.csv"
    sequence_fixture = Path(__file__).parent / "fixtures" / "algorithms" / "sequence_fixture.csv"
    classification_columns = [
        {"name": "feature_x", "dataType": "number"},
        {"name": "feature_y", "dataType": "number"},
        {"name": "feature_sum", "dataType": "number"},
        {"name": "channel", "dataType": "text"},
        {"name": "target_class", "dataType": "text"},
    ]
    clustering_columns = [
        {"name": "feature_x", "dataType": "number"},
        {"name": "feature_y", "dataType": "number"},
        {"name": "radius", "dataType": "number"},
        {"name": "expected_cluster", "dataType": "integer"},
    ]
    anova_columns = [
        {"name": "treatment", "dataType": "text"},
        {"name": "region", "dataType": "text"},
        {"name": "replicate", "dataType": "integer"},
        {"name": "score", "dataType": "number"},
    ]
    sequence_columns = [
        {"name": "timestamp", "dataType": "text"},
        {"name": "series_id", "dataType": "text"},
        {"name": "signal", "dataType": "number"},
        {"name": "temperature", "dataType": "number"},
        {"name": "target_value", "dataType": "number"},
        {"name": "target_class", "dataType": "text"},
    ]

    with create_test_client(tmp_path) as client:
        project = create_project(client, project_path)
        classification = create_dataset_from_csv(client, project["id"], classification_fixture, classification_columns)
        classification_task = client.post(
            f"/api/projects/{project['id']}/training",
            json={
                "datasetId": classification["id"],
                "algorithmId": "random_forest_classifier",
                "taskType": "classification",
                "targetColumn": "target_class",
                "featureColumns": ["feature_x", "feature_y", "feature_sum", "channel"],
                "computeMode": "cpu",
                "parameters": {"n_estimators": 20, "max_depth": 8},
            },
        )
        assert classification_task.status_code == 202
        classification_result = wait_for_training(client, project["id"], classification_task.json()["jobId"])
        diagnostic_response = client.post(f"/api/jobs/{classification_task.json()['jobId']}/diagnostic-charts")
        assert diagnostic_response.status_code == 201
        assert {item["chartType"] for item in diagnostic_response.json()} == {"confusion_matrix", "feature_importance"}

        xgboost_task = client.post(
            f"/api/projects/{project['id']}/training",
            json={
                "datasetId": classification["id"],
                "algorithmId": "xgboost_classifier",
                "taskType": "classification",
                "targetColumn": "target_class",
                "featureColumns": ["feature_x", "feature_y", "feature_sum"],
                "computeMode": "cpu",
                "parameters": {"n_estimators": 25, "max_depth": 4, "learning_rate": 0.1, "subsample": 0.9},
            },
        )
        assert xgboost_task.status_code == 202
        xgboost_result = wait_for_training(client, project["id"], xgboost_task.json()["jobId"])

        clustering = create_dataset_from_csv(client, project["id"], clustering_fixture, clustering_columns)
        clustering_task = client.post(
            f"/api/projects/{project['id']}/training",
            json={
                "datasetId": clustering["id"],
                "algorithmId": "kmeans",
                "taskType": "clustering",
                "featureColumns": ["feature_x", "feature_y"],
                "computeMode": "cpu",
                "parameters": {"n_clusters": 3},
            },
        )
        assert clustering_task.status_code == 202
        clustering_result = wait_for_training(client, project["id"], clustering_task.json()["jobId"])

        anova = create_dataset_from_csv(client, project["id"], anova_fixture, anova_columns)
        anova_task = client.post(
            f"/api/projects/{project['id']}/training",
            json={
                "datasetId": anova["id"],
                "algorithmId": "factorial_anova",
                "taskType": "anova",
                "targetColumn": "score",
                "factorColumns": ["treatment", "region"],
                "computeMode": "cpu",
                "parameters": {"sum_squares_type": "2", "include_interactions": True},
            },
        )
        assert anova_task.status_code == 202
        anova_result = wait_for_training(client, project["id"], anova_task.json()["jobId"])

        sequence = create_dataset_from_csv(client, project["id"], sequence_fixture, sequence_columns)
        sequence_task = client.post(
            f"/api/projects/{project['id']}/training",
            json={
                "datasetId": sequence["id"],
                "algorithmId": "lstm_regressor",
                "taskType": "sequence_regression",
                "targetColumn": "target_value",
                "featureColumns": ["signal", "temperature"],
                "timeColumn": "timestamp",
                "groupColumn": "series_id",
                "computeMode": "cpu",
                "parameters": {"window_size": 12, "horizon": 1, "hidden_size": 8, "num_layers": 1, "epochs": 2, "batch_size": 32, "learning_rate": 0.01},
            },
        )
        assert sequence_task.status_code == 202
        sequence_result = wait_for_training(client, project["id"], sequence_task.json()["jobId"])

    assert classification_result["status"] == "succeeded"
    assert classification_result["algorithmId"] == "random_forest_classifier"
    assert classification_result["datasetId"] == classification["id"]
    assert xgboost_result["status"] == "succeeded"
    assert xgboost_result["algorithmId"] == "xgboost_classifier"
    assert clustering_result["status"] == "succeeded"
    assert clustering_result["algorithmId"] == "kmeans"
    assert anova_result["status"] == "succeeded"
    assert anova_result["algorithmId"] == "factorial_anova"
    assert sequence_result["status"] == "succeeded"
    assert sequence_result["algorithmId"] == "lstm_regressor"


def test_algorithm_catalog_exposes_stable_capabilities(tmp_path: Path) -> None:
    with create_test_client(tmp_path) as client:
        response = client.get("/api/algorithms")

    assert response.status_code == 200
    catalog = response.json()
    algorithms = {item["id"]: item for item in catalog["algorithms"]}
    assert catalog["version"] == 1
    assert algorithms["random_forest_classifier"]["taskType"] == "classification"
    assert algorithms["xgboost_regressor"]["supportsGpu"] is True
    assert algorithms["factorial_anova"]["requiresFactors"] is True
    assert algorithms["lstm_regressor"]["requiresTime"] is True
    assert all("status" in item and "chartTemplates" in item for item in catalog["algorithms"])
    assert any(item["status"] == "planned" for item in catalog["algorithms"])
    parameter_ids = {item["id"] for item in algorithms["lstm_regressor"]["parameters"]}
    assert {"window_size", "hidden_size", "epochs"} <= parameter_ids


def test_chart_specs_persist_dataset_source_and_restore(tmp_path: Path) -> None:
    fixture = Path(__file__).parent / "fixtures" / "algorithms" / "regression_fixture.csv"
    project_path = tmp_path / "chart-project"

    with create_test_client(tmp_path) as client:
        project = create_project(client, project_path)
        dataset = create_dataset_from_csv(
            client,
            project["id"],
            fixture,
            [
                {"name": "feature_x", "dataType": "number"},
                {"name": "feature_y", "dataType": "number"},
                {"name": "region", "dataType": "text"},
                {"name": "target_value", "dataType": "number"},
            ],
        )
        created = client.post(
            f"/api/projects/{project['id']}/charts",
            json={
                "name": "目标预测散点图",
                "chartType": "scatter",
                "datasetId": dataset["id"],
                "xColumn": "target_value",
                "yColumns": ["feature_x"],
                "filters": {"region": ["east", "west"]},
                "options": {"theme": "light", "showLegend": True},
            },
        )
        invalid = client.post(
            f"/api/projects/{project['id']}/charts",
            json={
                "name": "错误字段",
                "chartType": "scatter",
                "datasetId": dataset["id"],
                "xColumn": "missing_column",
                "yColumns": ["feature_x"],
            },
        )
        listed = client.get(f"/api/projects/{project['id']}/charts")
        restored = client.get(f"/api/charts/{created.json()['id']}")

    assert created.status_code == 201
    assert invalid.status_code == 400
    assert invalid.json()["errorType"] == "ChartSpecError"
    assert listed.status_code == 200
    assert restored.status_code == 200
    assert restored.json()["datasetId"] == dataset["id"]
    assert restored.json()["filters"]["region"] == ["east", "west"]


def test_chart_generation_creates_reproducible_artifacts(tmp_path: Path) -> None:
    fixture = Path(__file__).parent / "fixtures" / "algorithms" / "regression_fixture.csv"
    project_path = tmp_path / "chart-generation-project"

    with create_test_client(tmp_path) as client:
        project = create_project(client, project_path)
        dataset = create_dataset_from_csv(
            client,
            project["id"],
            fixture,
            [
                {"name": "feature_x", "dataType": "number"},
                {"name": "feature_y", "dataType": "number"},
                {"name": "region", "dataType": "text"},
                {"name": "target_value", "dataType": "number"},
            ],
        )
        chart = client.post(
            f"/api/projects/{project['id']}/charts",
            json={"name": "回归散点图", "chartType": "scatter", "datasetId": dataset["id"], "xColumn": "feature_x", "yColumns": ["target_value"]},
        )
        generated = client.post(f"/api/projects/{project['id']}/charts/{chart.json()['id']}/generate")
        result = wait_for_chart(client, generated.json()["jobId"])
        html = client.get(f"/api/jobs/{generated.json()['jobId']}/chart-artifacts/chart.html")
        png = client.get(f"/api/jobs/{generated.json()['jobId']}/chart-artifacts/chart.png")

    assert generated.status_code == 202
    assert result["status"] == "succeeded", result
    assert {artifact["format"] for artifact in result["artifacts"]} == {"json", "html", "png", "svg"}
    assert html.status_code == 200
    assert b"echarts" in html.content
    assert png.status_code == 200
    assert png.content.startswith(b"\x89PNG")


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


def test_missing_document_result_returns_structured_error(tmp_path: Path) -> None:
    with create_test_client(tmp_path) as client:
        response = client.get("/api/assets/asset-missing/document")

    assert response.status_code == 404
    assert response.json()["errorType"] == "DocumentResultNotFoundError"
    assert response.json()["operation"] == "document_get"


def test_project_tree_includes_nested_and_hidden_entries(tmp_path: Path) -> None:
    project_path = tmp_path / "tree-project"
    with create_test_client(tmp_path) as client:
        project = create_project(client, project_path)
        hidden_directory = project_path / ".workspace-cache"
        hidden_directory.mkdir()
        (hidden_directory / "state.json").write_text("{}", encoding="utf-8")
        nested_directory = project_path / "source" / "季度报表"
        nested_directory.mkdir()
        (nested_directory / "说明.txt").write_text("项目说明", encoding="utf-8")

        complete_tree = client.get(
            f"/api/projects/{project['id']}/tree",
            params={"includeHidden": "true"},
        )
        visible_tree = client.get(
            f"/api/projects/{project['id']}/tree",
            params={"includeHidden": "false"},
        )

    assert complete_tree.status_code == 200
    assert complete_tree.json()[0]["name"] == ".workspace-cache"
    assert complete_tree.json()[0]["hidden"] is True
    source = next(node for node in complete_tree.json() if node["name"] == "source")
    nested = next(node for node in source["children"] if node["name"] == "季度报表")
    assert nested["children"][0]["relativePath"] == "source/季度报表/说明.txt"
    assert all(node["name"] != ".workspace-cache" for node in visible_tree.json())


def test_project_file_content_is_inline_and_restricted_to_project(tmp_path: Path) -> None:
    project_path = tmp_path / "file-preview-project"
    outside_file = tmp_path / "outside.txt"
    outside_file.write_text("private", encoding="utf-8")
    with create_test_client(tmp_path) as client:
        project = create_project(client, project_path)
        note_path = project_path / "documents" / "说明.txt"
        note_path.write_text("项目内预览", encoding="utf-8")
        content = client.get(
            f"/api/projects/{project['id']}/files/content",
            params={"path": "documents/说明.txt"},
        )
        escaped = client.get(
            f"/api/projects/{project['id']}/files/content",
            params={"path": "../outside.txt"},
        )

    assert content.status_code == 200
    assert content.content.decode("utf-8") == "项目内预览"
    assert content.headers["content-disposition"].startswith("inline;")
    assert escaped.status_code == 400
    assert escaped.json()["errorType"] == "FileAccessError"


def test_import_markdown_records_a_text_asset(tmp_path: Path) -> None:
    project_path = tmp_path / "markdown-project"
    with create_test_client(tmp_path) as client:
        project = create_project(client, project_path)
        imported = import_file(client, str(project["id"]), "研究说明.md", "# 真实文本\n数据来源说明".encode("utf-8"))

    assert imported.status_code == 201
    assert imported.json()["preview"] is None
    assert imported.json()["document"] is None
    assert imported.json()["importedAssets"][0]["name"] == "研究说明.md"


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
    fixture = Path(__file__).parent / "fixtures" / "chinese_sales.xlsx"
    project_path = tmp_path / "xlsx-project"

    with create_test_client(tmp_path) as client:
        project = create_project(client, project_path)
        response = import_file(
            client,
            str(project["id"]),
            fixture.name,
            fixture.read_bytes(),
        )

    assert response.status_code == 201
    preview = response.json()["preview"]
    assert preview["sheetName"] == "销售数据"
    assert preview["rowCount"] == 2
    assert preview["columns"][1]["inferredType"] == "integer"
    assert preview["rows"][1]["销量"] == 48


def test_import_zip_extracts_csv_and_records_asset_relationship(tmp_path: Path) -> None:
    fixture = Path(__file__).parent / "fixtures" / "chinese_archive.zip"
    project_path = tmp_path / "zip-project"

    with create_test_client(tmp_path) as client:
        project = create_project(client, project_path)
        response = import_file(
            client,
            str(project["id"]),
            fixture.name,
            fixture.read_bytes(),
        )

    assert response.status_code == 201
    result = response.json()
    assert result["extractedCount"] == 1
    assert len(result["importedAssets"]) == 2
    assert result["importedAssets"][1]["parentAssetId"] == result["importedAssets"][0]["id"]
    assert result["preview"]["encoding"] == "gb18030"
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


def test_import_digital_pdf_extracts_markdown_and_persists_result(tmp_path: Path) -> None:
    fixture = Path(__file__).parent / "fixtures" / "digital_chinese_report.pdf"
    project_path = tmp_path / "digital-pdf-project"
    with create_test_client(tmp_path) as client:
        project = create_project(client, project_path)
        imported = import_file(client, str(project["id"]), fixture.name, fixture.read_bytes())
        result = imported.json()["document"]
        restored = client.get(f"/api/assets/{result['assetId']}/document")

    assert imported.status_code == 201
    assert result["pdfType"] == "text_based"
    assert result["status"] == "parsed"
    assert "上海区域销量" in result["markdownPreview"]
    assert restored.json()["engine"] == "pymupdf"
    assert (project_path / result["markdownRelativePath"]).is_file()
    assert (project_path / result["jsonRelativePath"]).is_file()


def test_pdf_content_and_parsed_document_exports(tmp_path: Path) -> None:
    fixture = Path(__file__).parent / "fixtures" / "digital_chinese_report.pdf"
    project_path = tmp_path / "document-export-project"
    with create_test_client(tmp_path) as client:
        project = create_project(client, project_path)
        imported = import_file(client, str(project["id"]), fixture.name, fixture.read_bytes())
        asset_id = imported.json()["document"]["assetId"]
        content = client.get(f"/api/assets/{asset_id}/content")
        exports = {
            output_format: client.get(
                f"/api/assets/{asset_id}/document/export",
                params={"format": output_format},
            )
            for output_format in ("docx", "xlsx", "md", "txt")
        }

    assert content.status_code == 200
    assert content.content.startswith(b"%PDF")
    assert exports["docx"].status_code == 200
    assert exports["docx"].content.startswith(b"PK")
    assert exports["xlsx"].content.startswith(b"PK")
    assert "上海区域销量" in exports["md"].content.decode("utf-8")
    assert "第 1 页" in exports["txt"].content.decode("utf-8")


def test_import_scanned_pdf_routes_page_to_ocr(tmp_path: Path) -> None:
    fixture = Path(__file__).parent / "fixtures" / "scanned_chinese_report.pdf"
    project_path = tmp_path / "scanned-pdf-project"
    with create_test_client(tmp_path) as client:
        project = create_project(client, project_path)
        imported = import_file(client, str(project["id"]), fixture.name, fixture.read_bytes())

    result = imported.json()["document"]
    assert result["pdfType"] == "scanned"
    assert result["status"] == "parsed"
    assert result["engine"] == "pymupdf+rapidocr"
    assert result["ocrPages"] == [1]
    assert result["pagesNeedingOcr"] == []
    assert "扫描 PDF 测试报告" in result["markdownPreview"]
    assert (project_path / result["markdownRelativePath"]).is_file()


def test_import_mixed_pdf_only_runs_ocr_for_image_page(tmp_path: Path) -> None:
    fixture = Path(__file__).parent / "fixtures" / "mixed_chinese_report.pdf"
    project_path = tmp_path / "mixed-pdf-project"
    with create_test_client(tmp_path) as client:
        project = create_project(client, project_path)
        imported = import_file(client, str(project["id"]), fixture.name, fixture.read_bytes())

    result = imported.json()["document"]
    assert result["pdfType"] == "mixed"
    assert result["status"] == "parsed"
    assert result["ocrPages"] == [2]
    assert result["pagesNeedingOcr"] == []
    assert "混合 PDF 第一页" in result["pages"][0]["text"]
    assert "扫描 PDF 测试报告" in result["pages"][1]["text"]
