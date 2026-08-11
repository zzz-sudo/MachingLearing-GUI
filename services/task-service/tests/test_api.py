from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app


def create_test_client(tmp_path: Path) -> TestClient:
    return TestClient(create_app(tmp_path / "service-data"))


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

