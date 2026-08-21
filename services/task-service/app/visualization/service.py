from __future__ import annotations

import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from app.errors import chart_error
from app.models import ChartGenerationResult, ChartSpecRecord, JobCreate, JobStatus, JobUpdate
from app.storage import WorkspaceStore


class VisualizationService:
    """Coordinate isolated chart rendering processes and persist their outcomes."""

    def __init__(self, store: WorkspaceStore) -> None:
        self.store = store
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ml-gui-chart")

    def start(self, project_id: str, chart_id: str) -> ChartGenerationResult:
        chart = self.store.get_chart_spec(chart_id)
        if chart.project_id != project_id:
            raise chart_error("图形规格不属于当前项目", chartId=chart_id)
        if chart.status == "running":
            raise chart_error("图形已经在生成中", chartId=chart_id)
        project = self.store.get_project(project_id)
        job = self.store.create_job(JobCreate(project_id=project_id, title=f"生成图形 {chart.name}", message="等待图形 Worker"))
        run_directory = Path(project.path) / "charts" / job.id
        run_directory.mkdir(parents=True, exist_ok=True)
        config_path = run_directory / "run.json"
        result_path = run_directory / "result.json"
        config_path.write_text(
            json.dumps(
                {
                    "jobId": job.id,
                    "chartId": chart.id,
                    "name": chart.name,
                    "chartType": chart.chart_type,
                    "datasetPath": str(Path(project.path) / self.store.get_dataset_version(chart.dataset_id).parquet_relative_path),
                    "xColumn": chart.x_column,
                    "yColumns": chart.y_columns,
                    "groupColumn": chart.group_column,
                    "options": chart.options,
                    "filters": chart.filters,
                    "artifactDirectory": str(run_directory),
                    "resultPath": str(result_path),
                },
                ensure_ascii=False,
                indent=2,
            ) + "\n",
            encoding="utf-8",
        )
        self.store.update_chart_spec(chart.id, status="queued")
        self.executor.submit(self._run, job.id, chart.id, config_path, result_path)
        return ChartGenerationResult(job_id=job.id, chart_id=chart.id, status=JobStatus.QUEUED, chart_type=chart.chart_type)

    def get_result(self, job_id: str) -> ChartGenerationResult:
        job = self.store.get_job(job_id)
        project = self.store.get_project(job.project_id)
        result_path = Path(project.path) / "charts" / job.id / "result.json"
        config_path = Path(project.path) / "charts" / job.id / "run.json"
        if not result_path.is_file():
            chart_type = json.loads(config_path.read_text(encoding="utf-8")).get("chartType", "line") if config_path.is_file() else "line"
            return ChartGenerationResult(job_id=job.id, chart_id="unknown", status=job.status, chart_type=chart_type)
        try:
            result = json.loads(result_path.read_text(encoding="utf-8"))
            config = json.loads(config_path.read_text(encoding="utf-8"))
            return ChartGenerationResult(job_id=job.id, chart_id=config["chartId"], **result)
        except (OSError, ValueError, KeyError, TypeError) as error:
            raise chart_error("无法读取图形生成结果", jobId=job.id, reason=str(error)) from error

    def _run(self, job_id: str, chart_id: str, config_path: Path, result_path: Path) -> None:
        self.store.update_job(job_id, JobUpdate(status=JobStatus.RUNNING, progress=5, message="正在启动图形 Worker"))
        self.store.update_chart_spec(chart_id, status="running")
        python_executable = self._resolve_python()
        worker_path = Path(getattr(sys, "_MEIPASS", Path(__file__).parent.parent)) / "app" / "visualization" / "worker.py"
        if not worker_path.is_file():
            worker_path = Path(__file__).with_name("worker.py")
        try:
            process = subprocess.run(
                [str(python_executable), str(worker_path), str(config_path)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=3600,
                check=False,
            )
            if process.returncode != 0:
                raise RuntimeError(process.stderr.strip() or process.stdout.strip() or "图形 Worker 返回失败状态")
            result = json.loads(result_path.read_text(encoding="utf-8"))
            artifacts = result.get("artifacts", [])
            artifact_ids = [f"{job_id}:{item['relativePath']}" for item in artifacts]
            self.store.update_chart_spec(chart_id, status="succeeded", artifact_ids=artifact_ids)
            self.store.update_job(job_id, JobUpdate(status=JobStatus.SUCCEEDED, progress=100, message="图形生成完成，产物已保存"))
        except (OSError, RuntimeError, subprocess.TimeoutExpired, ValueError, KeyError) as error:
            result = {"status": "failed", "chartType": "line", "artifacts": [], "warnings": [], "environment": {}, "errorType": type(error).__name__, "errorMessage": str(error)}
            result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            self.store.update_chart_spec(chart_id, status="failed")
            self.store.update_job(job_id, JobUpdate(status=JobStatus.FAILED, progress=100, message=str(error)))

    @staticmethod
    def _resolve_python() -> Path:
        configured = os.environ.get("ML_GUI_TRAINING_PYTHON")
        candidate = Path(configured) if configured else Path(r"D:\Python\python11\python.exe")
        if candidate.is_file():
            return candidate
        if getattr(sys, "frozen", False):
            raise RuntimeError("VisualizationRuntimeError: packaged application requires ML_GUI_TRAINING_PYTHON")
        return Path(sys.executable)
